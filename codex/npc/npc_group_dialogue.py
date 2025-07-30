"""
Multi-NPC Group Dialogue Generator (SPR-NPC03)

Generates dynamic group dialogue when multiple NPCs appear in a scene.
Handles:
- Individual NPC trust scores and personalities
- Group dynamics and combined reactions
- Trust conflicts between NPCs
- Alternating dialogue patterns
"""

import json
import os
import random
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Import individual NPC dialogue utilities
from .npc_dialogue import (
    DIALOGUE_TEMPLATES, 
    EMOTION_DIMENSIONS,
    load_emotion_state,
    load_memory_recap,
    get_dominant_emotion,
    get_trust_category,
    select_dialogue_template
)

# Group dialogue templates for different trust combinations
GROUP_DIALOGUE_TEMPLATES = {
    # Both NPCs high trust
    "both_high_trust": {
        "supportive": [
            ("We both believe in you completely.", "Your courage inspires us both."),
            ("Together we stand with you.", "We'll face this challenge as one."),
            ("You have our unwavering support.", "We trust your judgment entirely.")
        ],
        "collaborative": [
            ("What do you think, friend?", "I agree - you've proven yourself."),
            ("We're here for you.", "Absolutely, you can count on us."),
            ("This calls for wisdom.", "And you've shown great wisdom before.")
        ]
    },
    
    # Mixed trust levels (high/low)
    "mixed_trust": {
        "conflicted": [
            ("I trust you completely.", "I'm not so sure about this..."),
            ("You've earned my faith.", "Actions speak louder than words."),
            ("I believe in your choice.", "Prove me wrong, then.")
        ],
        "tension": [
            ("They've shown their worth.", "Have they? I need more convincing."),
            ("Give them a chance.", "Chances must be earned."),
            ("I see potential here.", "I see risk.")
        ]
    },
    
    # Both NPCs low trust
    "both_low_trust": {
        "skeptical": [
            ("We're both watching you closely.", "Your next choice matters greatly."),
            ("Earn our trust together.", "Show us we're wrong about you."),
            ("Prove yourself to both of us.", "We need to see real change.")
        ],
        "cautious": [
            ("Tread carefully here.", "Very carefully indeed."),
            ("This is your chance.", "Don't waste it."),
            ("We're giving you an opportunity.", "Use it wisely.")
        ]
    },
    
    # Dynamic emotional responses
    "emotional_reactions": {
        "joy": [
            ("This fills my heart with joy!", "Mine too - what a wonderful moment!"),
            ("I can't help but smile.", "Your happiness is contagious."),
            ("This is what we hoped for.", "Beyond what we dreamed!")
        ],
        "fear": [
            ("I sense danger ahead.", "My instincts agree - be careful."),
            ("Something feels wrong.", "Trust that feeling."),
            ("We should proceed with caution.", "Together, we're stronger.")
        ],
        "grief": [
            ("My heart aches for you.", "We share your sorrow."),
            ("This loss weighs heavily.", "On all of us."),
            ("Grief is a burden shared.", "Let us help carry it.")
        ]
    },
    
    # Fallback group responses
    "fallback": [
        ("We're here with you.", "Whatever comes next."),
        ("The path ahead is uncertain.", "But we'll face it together."),
        ("Your choice will guide us.", "We'll follow where you lead.")
    ]
}

class NPCPersonality:
    """Defines NPC personality traits that influence group dialogue"""
    
    def __init__(self, npc_id: str, name: str, personality_type: str = "balanced"):
        self.npc_id = npc_id
        self.name = name
        self.personality_type = personality_type
        
        # Personality affects response patterns
        self.traits = {
            "supportive": {"tendency": "encouraging", "conflict_style": "diplomatic"},
            "skeptical": {"tendency": "questioning", "conflict_style": "direct"},
            "wise": {"tendency": "advisory", "conflict_style": "philosophical"},
            "protective": {"tendency": "cautious", "conflict_style": "defensive"},
            "balanced": {"tendency": "adaptive", "conflict_style": "moderate"}
        }.get(personality_type, {"tendency": "adaptive", "conflict_style": "moderate"})

def load_npc_states(player_id: str) -> Dict[str, float]:
    """Load trust values for all NPCs associated with a player"""
    try:
        # Import database dependencies
        from backend.db import SessionLocal
        from backend.npc.service import get_trust_scores
        
        db = SessionLocal()
        try:
            trust_scores = get_trust_scores(player_id, db)
            return trust_scores
        finally:
            db.close()
    except Exception as e:
        print(f"Error loading NPC states: {e}")
        # Fallback to default NPCs for development
        import uuid
        lyra_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:lyra"))
        orin_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:orin"))
        return {
            lyra_uuid: 0.7,
            orin_uuid: 0.3
        }

def get_trust_dynamic(trust_scores: Dict[str, float]) -> str:
    """Determine the overall trust dynamic of the group"""
    if not trust_scores:
        return "neutral"
    
    values = list(trust_scores.values())
    high_trust_count = sum(1 for t in values if t >= 0.7)
    low_trust_count = sum(1 for t in values if t < 0.3)
    
    if high_trust_count == len(values):
        return "both_high_trust"
    elif low_trust_count == len(values):
        return "both_low_trust"
    else:
        return "mixed_trust"

def select_group_dialogue_pattern(trust_dynamic: str, emotion_name: str, emotion_intensity: float) -> str:
    """Select appropriate dialogue pattern based on group trust and emotion"""
    
    # Prioritize emotional responses if emotion is strong
    if emotion_intensity > 0.6 and emotion_name in GROUP_DIALOGUE_TEMPLATES["emotional_reactions"]:
        return f"emotional_reactions.{emotion_name}"
    
    # Use trust-based patterns
    if trust_dynamic in GROUP_DIALOGUE_TEMPLATES:
        patterns = list(GROUP_DIALOGUE_TEMPLATES[trust_dynamic].keys())
        return f"{trust_dynamic}.{random.choice(patterns)}"
    
    return "fallback"

def generate_group_dialogue(npc_ids: List[str], player_id: str, scene_context: str = "") -> List[Dict[str, str]]:
    """
    Generate group dialogue for multiple NPCs in a scene.
    
    Args:
        npc_ids: List of NPC identifiers to include in dialogue
        player_id: The player identifier
        scene_context: Optional context about the current scene
        
    Returns:
        List of dialogue entries with npc_id, name, and text
    """
    if len(npc_ids) == 0:
        return []
    
    if len(npc_ids) == 1:
        # Single NPC - use existing individual dialogue system
        from .npc_dialogue import generate_npc_dialogue
        dialogue = generate_npc_dialogue(npc_ids[0], player_id)
        
        # Load trust for single NPC
        trust_scores = load_npc_states(player_id)
        npc_trust = trust_scores.get(npc_ids[0], 0.5)
        
        return [{
            "npc_id": npc_ids[0],
            "name": "Companion",  # TODO: Load actual NPC name
            "text": dialogue,
            "trust": npc_trust
        }]
    
    # Load context data
    trust_scores = load_npc_states(player_id)
    emotion_vector = load_emotion_state(player_id)
    memory_recap = load_memory_recap(player_id)
    
    # Handle missing data with fallbacks
    if emotion_vector is None:
        emotion_vector = [0.0] * len(EMOTION_DIMENSIONS)
    
    # Get dominant emotion
    dominant_emotion, emotion_intensity = get_dominant_emotion(emotion_vector)
    
    # Determine trust dynamic
    relevant_trust = {npc_id: trust_scores.get(npc_id, 0.5) for npc_id in npc_ids}
    trust_dynamic = get_trust_dynamic(relevant_trust)
    
    # Select dialogue pattern
    pattern_key = select_group_dialogue_pattern(trust_dynamic, dominant_emotion, emotion_intensity)
    
    # Get dialogue templates
    pattern_parts = pattern_key.split('.')
    if len(pattern_parts) == 2:
        template_group = GROUP_DIALOGUE_TEMPLATES.get(pattern_parts[0], {})
        templates = template_group.get(pattern_parts[1], GROUP_DIALOGUE_TEMPLATES["fallback"])
    else:
        templates = GROUP_DIALOGUE_TEMPLATES["fallback"]
    
    # Select a random template pair/group
    if isinstance(templates, list) and len(templates) > 0:
        selected_template = random.choice(templates)
        
        # Handle different template formats
        if isinstance(selected_template, tuple):
            # Pair of dialogue lines
            dialogue_lines = list(selected_template)
        elif isinstance(selected_template, list):
            # List of dialogue lines
            dialogue_lines = selected_template
        else:
            # Single dialogue line - split for multiple NPCs
            dialogue_lines = [str(selected_template)]
    else:
        dialogue_lines = ["We're here with you.", "Whatever comes next."]
    
    # Create dialogue entries for each NPC
    result = []
    for i, npc_id in enumerate(npc_ids[:len(dialogue_lines)]):  # Limit to available dialogue lines
        # TODO: Load actual NPC names from database
        npc_name = {
            "npc_lyra": "Lyra",
            "npc_orin": "Orin"
        }.get(npc_id, "Companion")
        
        dialogue_text = dialogue_lines[i] if i < len(dialogue_lines) else dialogue_lines[-1]
        
        # Ensure dialogue is within character limit
        if len(dialogue_text) > 150:
            dialogue_text = dialogue_text[:147] + "..."
        
        result.append({
            "npc_id": npc_id,
            "name": npc_name,
            "text": dialogue_text,
            "trust": relevant_trust.get(npc_id, 0.5)
        })
    
    return result

def generate_group_dialogue_with_context(npc_ids: List[str], player_id: str, scene_context: str = "", max_npcs: int = 3) -> List[Dict[str, str]]:
    """
    Generate group dialogue with additional context and limits.
    
    Args:
        npc_ids: List of NPC identifiers
        player_id: Player identifier
        scene_context: Scene context for dialogue generation
        max_npcs: Maximum number of NPCs to include in dialogue
        
    Returns:
        List of dialogue entries, limited by max_npcs
    """
    # Limit NPCs to prevent dialogue overflow
    limited_npc_ids = npc_ids[:max_npcs]
    
    # Generate base dialogue
    dialogue_entries = generate_group_dialogue(limited_npc_ids, player_id, scene_context)
    
    # Add scene context influence if provided
    if scene_context and len(dialogue_entries) > 0:
        # Modify first NPC's dialogue to reference context
        first_entry = dialogue_entries[0]
        if "danger" in scene_context.lower():
            first_entry["text"] = f"Given the danger ahead... {first_entry['text'].lower()}"
        elif "choice" in scene_context.lower():
            first_entry["text"] = f"This choice is important. {first_entry['text']}"
        elif "mystery" in scene_context.lower():
            first_entry["text"] = f"Something mysterious unfolds... {first_entry['text'].lower()}"
    
    return dialogue_entries

# Utility function for backward compatibility
def get_single_npc_dialogue(npc_id: str, player_id: str) -> str:
    """Get dialogue for a single NPC (backward compatibility)"""
    dialogue_entries = generate_group_dialogue([npc_id], player_id)
    return dialogue_entries[0]["text"] if dialogue_entries else "I'm here with you."