"""
Dynamic NPC Generator (SPR-NPC06)

This module generates dynamic NPCs based on player archetype, story theme, and context.
Provides the generate_story_npcs function used by scene integration.
"""

import uuid
from typing import List, Dict, Any
from .models import NPC


async def generate_story_npcs(
    player_id: str,
    player_name: str,
    player_archetype: str,
    story_theme: str,
    num_npcs: int = 3
) -> List[NPC]:
    """
    Generate dynamic NPCs for a story.
    
    Args:
        player_id: Player identifier
        player_name: Player's name
        player_archetype: Player's archetype
        story_theme: Story theme
        num_npcs: Number of NPCs to generate
        
    Returns:
        List of generated NPCs
    """
    npcs = []
    
    # Default NPC templates based on common story roles
    npc_templates = [
        {
            "name": "Lyra",
            "role": "Companion",
            "archetype": "Archer",
            "personality_traits": ["loyal", "observant", "cautious"],
            "narrative_hooks": ["forest", "nature", "survival"],
            "motivation": "To protect and guide the player",
            "relationship_to_player": "trusted ally"
        },
        {
            "name": "Orin",
            "role": "Mentor",
            "archetype": "Sage",
            "personality_traits": ["wise", "patient", "mysterious"],
            "narrative_hooks": ["knowledge", "ancient", "secrets"],
            "motivation": "To share wisdom and guide the player's growth",
            "relationship_to_player": "teacher and guide"
        },
        {
            "name": "Thorne",
            "role": "Rival",
            "archetype": "Warrior",
            "personality_traits": ["proud", "competitive", "honorable"],
            "narrative_hooks": ["challenge", "strength", "honor"],
            "motivation": "To prove their worth and test the player",
            "relationship_to_player": "worthy opponent"
        },
        {
            "name": "Mira",
            "role": "Ally",
            "archetype": "Healer",
            "personality_traits": ["compassionate", "gentle", "determined"],
            "narrative_hooks": ["healing", "compassion", "hope"],
            "motivation": "To help others and bring healing",
            "relationship_to_player": "supportive friend"
        },
        {
            "name": "Kael",
            "role": "Antagonist",
            "archetype": "Dark Mage",
            "personality_traits": ["ambitious", "ruthless", "charismatic"],
            "narrative_hooks": ["power", "corruption", "darkness"],
            "motivation": "To gain power at any cost",
            "relationship_to_player": "nemesis"
        }
    ]
    
    # Generate NPCs based on templates
    for i in range(min(num_npcs, len(npc_templates))):
        template = npc_templates[i]
        
        # Generate consistent UUID for this NPC
        npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:{template['name'].lower()}")
        
        # Create NPC instance
        npc = NPC(
            id=npc_uuid,
            full_name=template["name"],
            baseline_trust=0.3,  # Start with moderate trust
            trust=0.3,
            role=template["role"],
            archetype=template["archetype"],
            personality_traits=template["personality_traits"],
            narrative_hooks=template["narrative_hooks"],
            motivation=template["motivation"],
            relationship_to_player=template["relationship_to_player"]
        )
        
        npcs.append(npc)
    
    return npcs


def generate_npc_by_role(role: str, player_id: str) -> NPC:
    """
    Generate a specific NPC by role.
    
    Args:
        role: NPC role (Mentor, Companion, Rival, etc.)
        player_id: Player identifier
        
    Returns:
        Generated NPC
    """
    # Role-specific templates
    role_templates = {
        "Mentor": {
            "name": "Elder",
            "archetype": "Sage",
            "personality_traits": ["wise", "patient", "mysterious"],
            "narrative_hooks": ["knowledge", "ancient", "secrets"],
            "motivation": "To share wisdom and guide growth",
            "relationship_to_player": "teacher and guide"
        },
        "Companion": {
            "name": "Companion",
            "archetype": "Adventurer",
            "personality_traits": ["loyal", "brave", "supportive"],
            "narrative_hooks": ["adventure", "friendship", "loyalty"],
            "motivation": "To support and accompany the player",
            "relationship_to_player": "trusted friend"
        },
        "Rival": {
            "name": "Rival",
            "archetype": "Competitor",
            "personality_traits": ["proud", "competitive", "honorable"],
            "narrative_hooks": ["challenge", "competition", "honor"],
            "motivation": "To prove their worth",
            "relationship_to_player": "worthy opponent"
        }
    }
    
    template = role_templates.get(role, role_templates["Companion"])
    
    # Generate consistent UUID
    npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:{role.lower()}")
    
    return NPC(
        id=npc_uuid,
        full_name=template["name"],
        baseline_trust=0.3,
        trust=0.3,
        role=role,
        archetype=template["archetype"],
        personality_traits=template["personality_traits"],
        narrative_hooks=template["narrative_hooks"],
        motivation=template["motivation"],
        relationship_to_player=template["relationship_to_player"]
    ) 