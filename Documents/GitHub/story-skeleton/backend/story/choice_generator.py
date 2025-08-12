# backend/story/choice_generator.py

import os
import json
import re
import logging
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

try:
    import openai
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    LLM_AVAILABLE = True
except Exception:
    client = None
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)

# Feature flags
ENABLE_FREE_TEXT = os.getenv("ENABLE_FREE_TEXT", "true").lower() in ["true", "1", "yes"]
MIN_SCENE_FOR_FREE_TEXT = int(os.getenv("MIN_SCENE_FOR_FREE_TEXT", "7"))

# Constants for feature flags
ENABLE_FREE_TEXT_FLAG = "ENABLE_FREE_TEXT"
MIN_SCENE_FOR_FREE_TEXT_FLAG = "MIN_SCENE_FOR_FREE_TEXT"

class Choice:
    """Represents a generated choice with validation and safety metadata."""
    
    def __init__(self, text: str, effects: Dict[str, Any] = None, tags: List[str] = None, safety: Dict[str, Any] = None):
        self.text = text
        self.effects = effects or {}
        self.tags = tags or []
        self.safety = safety or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "effects": self.effects,
            "tags": self.tags,
            "safety": self.safety
        }

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two choice texts using fuzzy matching."""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def is_duplicate_choice(new_choice: str, existing_choices: List[str], threshold: float = 0.85) -> bool:
    """Check if a new choice is too similar to existing choices."""
    for existing in existing_choices:
        if calculate_similarity(new_choice, existing) >= threshold:
            return True
    return False

def generate_template_choice(beat_id: str, beat_tags: List[str], world_hooks: List[str], npcs_present: List[str]) -> Choice:
    """Generate a template-based choice when LLM is not available."""
    
    # Template choices based on beat type
    templates = {
        "recruitment_offer": [
            "Ask for time to consider",
            "Request more information about their skills",
            "Discuss the terms of joining",
            "Seek advice from other party members"
        ],
        "mentor_guidance": [
            "Ask for specific training",
            "Request guidance on a particular challenge",
            "Seek wisdom about the path ahead",
            "Ask about their own journey"
        ],
        "bond_by_fire": [
            "Share a personal story in return",
            "Ask about their past experiences",
            "Propose a joint training session",
            "Suggest a shared ritual or tradition"
        ],
        "action": [
            "Formulate a detailed plan",
            "Assess the risks involved",
            "Coordinate with allies",
            "Prepare for potential complications"
        ],
        "conflict": [
            "Attempt to de-escalate the situation",
            "Seek a diplomatic solution",
            "Prepare for the worst while hoping for the best",
            "Gather more information before acting"
        ],
        "reveal": [
            "Ask for clarification",
            "Request more context",
            "Seek additional details",
            "Process the information carefully"
        ]
    }
    
    # Find appropriate template based on beat_id or tags
    choice_text = None
    
    # First try beat_id specific templates
    if beat_id in templates:
        import random
        choice_text = random.choice(templates[beat_id])
    
    # Fallback to tag-based templates
    if not choice_text:
        for tag in beat_tags:
            if tag in templates:
                import random
                choice_text = random.choice(templates[tag])
                break
    
    # Ultimate fallback
    if not choice_text:
        fallback_choices = [
            "Consider the situation carefully",
            "Seek additional information",
            "Consult with your companions",
            "Take a moment to reflect",
            "Assess your options",
            "Plan your next move"
        ]
        import random
        choice_text = random.choice(fallback_choices)
    
    # Add world hook context if available
    if world_hooks and len(world_hooks) > 0:
        import random
        hook = random.choice(world_hooks[:3])  # Use first 3 hooks
        choice_text = f"{choice_text} regarding the {hook}"
    
    return Choice(
        text=choice_text,
        effects={"trust_delta": 0.0, "emotion_delta": [0.1, 0, 0, 0, 0.1, 0, 0, 0]},
        tags=beat_tags[:2] if beat_tags else ["contextual"],
        safety={"moderated": True, "appropriate": True}
    )

async def make_contextual_choice(
    state: Dict[str, Any], 
    beat: Dict[str, Any], 
    npcs_present: List[str], 
    existing_choices: List[str]
) -> Choice:
    """
    Generate a robust 3rd choice that's non-duplicate, on-beat, and state-aware.
    
    Args:
        state: Current story state
        beat: Selected beat data
        npcs_present: List of NPC IDs present in the scene
        existing_choices: List of existing choice texts to avoid duplicates
    
    Returns:
        Choice object with text, effects, tags, and safety metadata
    """
    
    beat_id = beat.get("id", "unknown")
    beat_tags = beat.get("tags", [])
    world_hooks = state.get("flags", {}).get("world_hooks", [])
    scene_index = state.get("scene_index", 0)
    phase = state.get("phase", "early")
    
    # Get NPC details for context
    npc_details = []
    for nid in npcs_present:
        npc_data = state.get("npcs", {}).get(nid, {})
        npc_details.append({
            "id": nid,
            "name": npc_data.get("full_name", "Unknown"),
            "role": npc_data.get("role", "Companion"),
            "trust": npc_data.get("trust", 0.3)
        })
    
    # Try LLM generation first if available
    if LLM_AVAILABLE and client:
        try:
            choice = await _generate_llm_choice(
                beat_id, beat_tags, world_hooks, npc_details, 
                existing_choices, scene_index, phase
            )
            if choice and not is_duplicate_choice(choice.text, existing_choices):
                return choice
        except Exception as e:
            logger.warning(f"LLM choice generation failed: {e}")
    
    # Fallback to template-based generation
    choice = generate_template_choice(beat_id, beat_tags, world_hooks, npcs_present)
    
    # Ensure no duplicates even with template
    attempts = 0
    while is_duplicate_choice(choice.text, existing_choices) and attempts < 5:
        choice = generate_template_choice(beat_id, beat_tags, world_hooks, npcs_present)
        attempts += 1
    
    return choice

async def _generate_llm_choice(
    beat_id: str,
    beat_tags: List[str],
    world_hooks: List[str],
    npc_details: List[Dict[str, Any]],
    existing_choices: List[str],
    scene_index: int,
    phase: str
) -> Optional[Choice]:
    """Generate choice using LLM with safety constraints."""
    
    npc_context = ""
    if npc_details:
        npc_names = [npc["name"] for npc in npc_details[:2]]
        npc_context = f" NPCs present: {', '.join(npc_names)}."
    
    world_context = ""
    if world_hooks:
        world_context = f" World elements: {', '.join(world_hooks[:3])}."
    
    prompt = f"""
Generate a single, contextual choice for a story scene. The choice should be:

CONTEXT:
- Beat ID: {beat_id}
- Beat tags: {', '.join(beat_tags)}
- Scene index: {scene_index} (phase: {phase})
- Existing choices to avoid: {', '.join(existing_choices[:2])}
-{npc_context}
-{world_context}

REQUIREMENTS:
1. Must be different from existing choices (avoid similar phrasing)
2. Should align with beat tags and world context
3. Must be safe and appropriate for all audiences
4. Should feel natural and contextual to the scene
5. Keep it concise (1-2 sentences max)

SPECIAL RULES:
- If beat_id is "recruitment_offer": create an orthogonal choice like "Ask for time to consider"
- If "mentor" in tags: focus on seeking guidance or wisdom
- If "action" in tags: focus on planning or preparation
- If "conflict" in tags: focus on de-escalation or diplomacy

Respond with ONLY the choice text, no explanations or formatting.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        
        choice_text = response.choices[0].message.content.strip()
        
        # Basic safety check
        if not choice_text or len(choice_text) > 200:
            return None
        
        # Check for inappropriate content
        inappropriate_words = ["kill", "murder", "hate", "destroy", "attack", "fight"]
        if any(word in choice_text.lower() for word in inappropriate_words):
            return None
        
        return Choice(
            text=choice_text,
            effects={"trust_delta": 0.0, "emotion_delta": [0.1, 0, 0, 0, 0.1, 0, 0, 0]},
            tags=beat_tags[:2] if beat_tags else ["contextual"],
            safety={"moderated": True, "appropriate": True, "llm_generated": True}
        )
        
    except Exception as e:
        logger.error(f"LLM choice generation error: {e}")
        return None

def should_enable_free_text(scene_index: int) -> bool:
    """Check if free-text should be enabled for the given scene."""
    return ENABLE_FREE_TEXT and scene_index >= MIN_SCENE_FOR_FREE_TEXT
