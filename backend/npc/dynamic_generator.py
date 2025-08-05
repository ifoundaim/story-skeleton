"""
Dynamic NPC Seed Generator & Profile Factory (SPR-NPC06)

This module generates unique, story-specific NPC profiles dynamically at story initialization.
NPCs are generated in alignment with the player's intent and archetype to deepen narrative 
personalization and replayability.
"""

import os
import json
import uuid
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import openai

from .models import NPC
from .service import ensure_npc_profile
from db import SessionLocal
from soulmap.service import get_soulmap_dict


class DynamicNPCGenerator:
    """Generates NPC profiles using LLM prompts based on player data."""
    
    def __init__(self):
        self.client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.client = openai.AsyncOpenAI(api_key=api_key)
            except Exception as e:
                print(f"⚠️ Failed to initialize OpenAI client: {e}")
    
    def _build_npc_generation_prompt(
        self, 
        player_name: str, 
        player_archetype: str, 
        soul_map: Dict[str, float],
        story_theme: str,
        num_npcs: int = 3
    ) -> str:
        """Build LLM prompt for NPC generation based on player data."""
        
        # Extract key traits from soul map for NPC generation
        dominant_traits = self._get_dominant_traits(soul_map, top_k=5)
        
        prompt = f"""
You are a master character designer for an interactive story game. Generate {num_npcs} unique NPC profiles that will interact with the player.

PLAYER CONTEXT:
- Name: {player_name}
- Archetype: {player_archetype}
- Story Theme: {story_theme}
- Dominant Soul Traits: {', '.join(dominant_traits)}

NPC GENERATION RULES:
1. Create NPCs that complement or challenge the player's archetype
2. Each NPC must have a clear role in the story
3. Trust baselines should reflect the NPC's initial disposition toward the player
4. Include narrative hooks that can drive story progression
5. Ensure NPCs align with the story theme

REQUIRED OUTPUT FORMAT (JSON):
{{
  "npcs": [
    {{
      "id": "unique_npc_id",
      "full_name": "NPC Full Name",
      "role": "NPC's role in the story (e.g., 'Mentor', 'Rival', 'Companion')",
      "archetype": "NPC's personality archetype (e.g., 'Sage', 'Warrior', 'Trickster')",
      "baseline_trust": 0.0-1.0,
      "personality_traits": ["trait1", "trait2", "trait3"],
      "narrative_hooks": ["hook1", "hook2"],
      "relationship_to_player": "How this NPC relates to the player",
      "motivation": "What drives this NPC",
      "secrets": ["secret1", "secret2"]
    }}
  ]
}}

GUIDELINES:
- baseline_trust: 0.0 (hostile) to 1.0 (trusting)
- Generate 3-5 personality traits per NPC
- Include 2-3 narrative hooks that can drive story choices
- Add 1-2 secrets that can be revealed through player interaction
- Ensure NPCs have distinct personalities and motivations
- Consider how NPCs might react to the player's soul traits

Respond ONLY with valid JSON matching the exact format above.
"""
        return prompt
    
    def _get_dominant_traits(self, soul_map: Dict[str, float], top_k: int = 5) -> List[str]:
        """Extract the most dominant traits from the soul map."""
        # Sort traits by absolute value (both positive and negative extremes matter)
        sorted_traits = sorted(soul_map.items(), key=lambda x: abs(x[1]), reverse=True)
        return [trait for trait, value in sorted_traits[:top_k]]
    
    async def generate_npc_profiles(
        self,
        player_id: str,
        player_name: str,
        player_archetype: str,
        story_theme: str,
        num_npcs: int = 3,
        db: Session = None
    ) -> List[NPC]:
        """
        Generate NPC profiles using LLM and store them in the database.
        
        Args:
            player_id: Unique identifier for the player
            player_name: Player's display name
            player_archetype: Player's chosen archetype
            story_theme: Theme of the current story
            num_npcs: Number of NPCs to generate
            db: Database session (optional)
            
        Returns:
            List of generated NPC objects
        """
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get player's soul map
            soul_map = get_soulmap_dict(db, player_id)
            
            # Generate NPC profiles using LLM
            npc_data = await self._generate_npc_data(
                player_name, player_archetype, soul_map, story_theme, num_npcs
            )
            
            # Store NPCs in database
            generated_npcs = []
            for npc_info in npc_data:
                npc = self._create_npc_from_data(npc_info, db)
                generated_npcs.append(npc)
            
            return generated_npcs
            
        finally:
            if should_close:
                db.close()
    
    async def _generate_npc_data(
        self,
        player_name: str,
        player_archetype: str,
        soul_map: Dict[str, float],
        story_theme: str,
        num_npcs: int
    ) -> List[Dict[str, Any]]:
        """Generate NPC data using LLM."""
        
        if not self.client:
            # Fallback to predefined NPCs if OpenAI is not available
            print("⚠️ OpenAI client not available, using fallback NPCs")
            return self._generate_fallback_npcs(player_archetype, story_theme, num_npcs)
        
        try:
            prompt = self._build_npc_generation_prompt(
                player_name, player_archetype, soul_map, story_theme, num_npcs
            )
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            
            # Clean and parse JSON response
            cleaned_content = self._strip_code_fences(content)
            npc_data = json.loads(cleaned_content)
            
            return npc_data.get("npcs", [])
            
        except Exception as e:
            print(f"⚠️ Failed to generate NPCs with LLM: {e}")
            return self._generate_fallback_npcs(player_archetype, story_theme, num_npcs)
    
    def _generate_fallback_npcs(
        self, 
        player_archetype: str, 
        story_theme: str, 
        num_npcs: int
    ) -> List[Dict[str, Any]]:
        """Generate fallback NPCs when LLM is not available."""
        
        # Archetype-based NPC templates
        archetype_npcs = {
            "Hero": [
                {
                    "id": "mentor_sage",
                    "full_name": "Elder Thorne",
                    "role": "Mentor",
                    "archetype": "Sage",
                    "baseline_trust": 0.7,
                    "personality_traits": ["Wise", "Patient", "Mysterious"],
                    "narrative_hooks": ["Knows ancient secrets", "Tests the player's worthiness"],
                    "relationship_to_player": "Guiding mentor figure",
                    "motivation": "To prepare the next generation of heroes",
                    "secrets": ["Was once a great warrior", "Knows the player's destiny"]
                },
                {
                    "id": "rival_warrior",
                    "full_name": "Captain Valen",
                    "role": "Rival",
                    "archetype": "Warrior",
                    "baseline_trust": 0.3,
                    "personality_traits": ["Proud", "Competitive", "Honorable"],
                    "narrative_hooks": ["Seeks to prove superiority", "Respects strength"],
                    "relationship_to_player": "Respected rival",
                    "motivation": "To be recognized as the greatest warrior",
                    "secrets": ["Fears failure", "Has a hidden injury"]
                }
            ],
            "Sage": [
                {
                    "id": "apprentice_curious",
                    "full_name": "Luna Bright",
                    "role": "Apprentice",
                    "archetype": "Explorer",
                    "baseline_trust": 0.8,
                    "personality_traits": ["Curious", "Energetic", "Loyal"],
                    "narrative_hooks": ["Seeks knowledge", "Wants to prove worth"],
                    "relationship_to_player": "Eager student",
                    "motivation": "To learn and discover new things",
                    "secrets": ["Has hidden magical talent", "Is secretly noble"]
                }
            ],
            "Explorer": [
                {
                    "id": "fellow_adventurer",
                    "full_name": "Raven Swift",
                    "role": "Companion",
                    "archetype": "Explorer",
                    "baseline_trust": 0.6,
                    "personality_traits": ["Free-spirited", "Optimistic", "Resourceful"],
                    "narrative_hooks": ["Knows hidden paths", "Has seen strange things"],
                    "relationship_to_player": "Fellow adventurer",
                    "motivation": "To explore the unknown",
                    "secrets": ["Has a map to treasure", "Is running from something"]
                }
            ]
        }
        
        # Get NPCs for the player's archetype, or use default if not found
        available_npcs = archetype_npcs.get(player_archetype, archetype_npcs["Hero"])
        
        # Return requested number of NPCs (or all available if fewer)
        return available_npcs[:num_npcs]
    
    def _create_npc_from_data(self, npc_info: Dict[str, Any], db: Session) -> NPC:
        """Create an NPC database record from generated data."""
        
        # Generate a consistent UUID for the NPC
        npc_id = npc_info.get("id", str(uuid.uuid4()))
        npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, npc_id)
        
        # Check if NPC already exists
        existing_npc = db.query(NPC).filter_by(id=npc_uuid).first()
        if existing_npc:
            return existing_npc
        
        # Create new NPC with extended metadata
        npc = NPC(
            id=npc_uuid,
            full_name=npc_info.get("full_name", "Unknown"),
            baseline_trust=float(npc_info.get("baseline_trust", 0.5)),
            trust=float(npc_info.get("baseline_trust", 0.5)),
            role=npc_info.get("role", ""),
            archetype=npc_info.get("archetype", ""),
            personality_traits=npc_info.get("personality_traits", []),
            narrative_hooks=npc_info.get("narrative_hooks", []),
            relationship_to_player=npc_info.get("relationship_to_player", ""),
            motivation=npc_info.get("motivation", ""),
            secrets=npc_info.get("secrets", []),
            generated="true"
        )
        
        db.add(npc)
        db.commit()
        db.refresh(npc)
        
        return npc
    
    def _strip_code_fences(self, text: str) -> str:
        """Remove code fence markers from LLM response."""
        # Remove leading ``` or ```json (with optional whitespace/newline)
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if len(lines) > 1:
                # Remove first line (```json) and last line (```)
                text = "\n".join(lines[1:-1])
            else:
                # Just remove the ``` markers
                text = text.replace("```", "")
        
        return text.strip()


# Global instance for easy access
npc_generator = DynamicNPCGenerator()


async def generate_story_npcs(
    player_id: str,
    player_name: str,
    player_archetype: str,
    story_theme: str,
    num_npcs: int = 3
) -> List[NPC]:
    """
    Convenience function to generate NPCs for a story.
    
    This function should be called during story initialization to create
    dynamic NPCs that align with the player's archetype and story theme.
    """
    return await npc_generator.generate_npc_profiles(
        player_id, player_name, player_archetype, story_theme, num_npcs
    ) 