"""
Soulmap Delta Inference Task (SPR-SM03)

Analyzes choice text and scene context to automatically generate soulmap trait deltas.
"""

import json
import os
from typing import Dict, List, Optional, Any
import openai
import sys
import os

# Add the backend directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from soulmap.mapping import SoulTrait, clip_vector, dict_to_vec

SYSTEM_PROMPT = """You are a narrative analyst specializing in psychological trait analysis.

Your task is to analyze a player's choice in a story context and determine how it reflects changes in their psychological traits.

Given the choice text, scene context, player's current emotional state, trust levels, and memory recap, you must identify up to 5 SoulTraits that would be most affected by this choice.

Available SoulTraits (64 total):
- Core Virtues: COURAGE, COMPASSION, WISDOM, CREATIVITY, JUSTICE, TEMPERANCE, RESILIENCE, EMPATHY
- Shadow Traits: FEAR, PRIDE, APATHY, SHADOW_BLEND_1-5
- Motivations: SELFACTUALIZATION, EXTERNALVALIDATION, COLLECTIVE, MOTIVATION_BLEND_1-5
- Archetypes: HERO, REBEL, SAGE, CAREGIVER, MAGICIAN, LOVER, SOVEREIGN, EXPLORER
- Archetype Blends: ARCHETYPE_BLEND_1-8
- Cognitive Functions: INTROVERTEDTHINKING, EXTRAVERTEDTHINKING, INTROVERTEDFEELING, EXTRAVERTEDFEELING, INTROVERTEDSENSING, EXTRAVERTEDSENSING, INTROVERTEDINTUITING, EXTRAVERTEDINTUITING
- Attachment Styles: SECUREATTACHMENT, ANXIOUSATTACHMENT, AVOIDANTATTACHMENT, DISORGANIZEDATTACHMENT
- Psychological Needs: AUTONOMY, COMPETENCE, RELATEDNESS, SELFCONTROL, MINDFULNESS, GRIT, CURIOSITY, PLAYFULNESS
- Social Traits: OPTIMISM, VIGILANCE, SOCIALDOMINANCE, HUMILITY

Return a JSON object with up to 5 trait keys and float values between -1.0 and 1.0, where:
- Positive values (0.1 to 1.0) indicate strengthening of that trait
- Negative values (-0.1 to -1.0) indicate weakening of that trait
- Values close to 0 (0.0 to 0.1 or -0.1 to 0.0) indicate minor changes

Example response:
{
  "COURAGE": 0.3,
  "COMPASSION": -0.2,
  "WISDOM": 0.1
}

Focus on the traits that are most directly impacted by the choice, considering the player's current emotional state and the narrative context."""

USER_PROMPT_TEMPLATE = """Analyze this player choice and determine soulmap trait changes:

Choice Text: {choice_text}

Scene Context: {scene_text}

Player's Current Emotion: {emotion_state}

NPC Trust Levels: {trust_levels}

Memory Recap: {memory_recap}

Return a JSON object with up to 5 trait changes:"""


class SoulmapInferenceTask:
    """Task for inferring soulmap deltas from choice context"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None
    
    async def infer_soulmap_delta(
        self,
        choice_text: str,
        scene_text: str,
        emotion_state: Dict[str, float],
        trust_levels: Dict[str, float],
        memory_recap: str,
        player_id: str
    ) -> Dict[str, float]:
        """
        Infer soulmap delta from choice context.
        
        Args:
            choice_text: The player's choice text
            scene_text: The scene description/context
            emotion_state: Current 8D emotion vector
            trust_levels: NPC trust levels
            memory_recap: Player's memory recap
            
        Returns:
            Dictionary of trait changes with values in [-1, 1]
        """
        
        # Check if we should use CPU stubs or if OpenAI client is not available
        if os.getenv("USE_CPU_STUBS", "false").lower() == "true" or self.client is None:
            return self._get_stub_delta(choice_text)
        
        try:
            # Prepare the user prompt
            user_prompt = USER_PROMPT_TEMPLATE.format(
                choice_text=choice_text,
                scene_text=scene_text,
                emotion_state=json.dumps(emotion_state),
                trust_levels=json.dumps(trust_levels),
                memory_recap=memory_recap
            )
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse the response
            result_text = response.choices[0].message.content
            delta_dict = json.loads(result_text)
            
            # Validate and clean the result
            validated_delta = self._validate_delta(delta_dict)
            
            print(f"🧠 [soulmap_infer] Generated delta for {player_id}: {validated_delta}")
            return validated_delta
            
        except Exception as e:
            print(f"❌ [soulmap_infer] Error inferring delta: {e}")
            # Return a safe fallback
            return self._get_stub_delta(choice_text)
    
    def _validate_delta(self, delta_dict: Dict[str, Any]) -> Dict[str, float]:
        """Validate and clean the inferred delta"""
        validated = {}
        
        if not delta_dict:
            return validated
        
        for trait_name, value in delta_dict.items():
            # Check if trait name is valid
            try:
                SoulTrait[trait_name]
            except KeyError:
                print(f"⚠️ [soulmap_infer] Invalid trait name: {trait_name}")
                continue
            
            # Convert to float and clip to [-1, 1]
            try:
                float_value = float(value)
                validated[trait_name] = max(-1.0, min(1.0, float_value))
            except (ValueError, TypeError):
                print(f"⚠️ [soulmap_infer] Invalid value for {trait_name}: {value}")
                continue
        
        return validated
    
    def _get_stub_delta(self, choice_text: str) -> Dict[str, float]:
        """Return a hard-coded example delta for testing"""
        # Handle None or empty choice text
        if not choice_text:
            return {"CURIOSITY": 0.1, "WISDOM": 0.1}
        
        # Simple heuristic based on choice text keywords
        choice_lower = choice_text.lower()
        
        if any(word in choice_lower for word in ["fight", "attack", "confront", "brave"]):
            return {"COURAGE": 0.3, "FEAR": -0.2}
        elif any(word in choice_lower for word in ["help", "save", "protect", "care"]):
            return {"COMPASSION": 0.4, "CAREGIVER": 0.2}
        elif any(word in choice_lower for word in ["think", "analyze", "study", "learn"]):
            return {"WISDOM": 0.3, "INTROVERTEDTHINKING": 0.2}
        elif any(word in choice_lower for word in ["run", "hide", "avoid", "escape"]):
            return {"FEAR": 0.3, "COURAGE": -0.2}
        elif any(word in choice_lower for word in ["lead", "command", "take charge"]):
            return {"SOVEREIGN": 0.3, "SOCIALDOMINANCE": 0.2}
        else:
            return {"CURIOSITY": 0.1, "WISDOM": 0.1}


# Global instance
soulmap_infer = SoulmapInferenceTask() 