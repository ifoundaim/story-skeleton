"""
Context-Aware NPC Dialogue Generator (SPR-NPC02)

Generates dynamic NPC responses based on:
- Trust score from npc_state.json
- Emotion vector from emotion_state.json  
- Memory recap from memory_state.json
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Emotion dimensions from emotion models
EMOTION_DIMENSIONS = ["joy", "grief", "awe", "fear", "desire", "disgust", "peace", "rage"]

# Dialogue templates based on trust + emotion combinations
DIALOGUE_TEMPLATES = {
    # High trust + positive emotions
    "high_trust_joy": [
        "Your courage inspires me! Let's face this together.",
        "I believe in you completely. You have what it takes.",
        "Your determination fills me with hope. We'll succeed!"
    ],
    "high_trust_awe": [
        "The wonder in your eyes... it reminds me why we're here.",
        "You see the magic in everything. It's beautiful.",
        "Your sense of wonder guides us forward."
    ],
    "high_trust_peace": [
        "Your calm presence soothes my worries.",
        "In your peace, I find strength. We'll be alright.",
        "Your serenity is our anchor in this storm."
    ],
    
    # High trust + challenging emotions
    "high_trust_fear": [
        "I'm here with you. We'll face this fear together.",
        "Your fear is natural, but you're not alone.",
        "I trust you to find your courage when it matters."
    ],
    "high_trust_grief": [
        "I feel your pain. Let me help carry this burden.",
        "Your heart is heavy, but I'm here to share the weight.",
        "We'll honor what you've lost by moving forward."
    ],
    
    # Medium trust responses
    "medium_trust_neutral": [
        "I'm learning to trust you. Show me what you're capable of.",
        "We're building something here. Let's see where it leads.",
        "You've earned some of my trust. Don't waste it."
    ],
    "medium_trust_positive": [
        "You're growing on me. Keep making good choices.",
        "I see potential in you. Don't let me down.",
        "You're proving yourself. I like what I see."
    ],
    
    # Low trust responses
    "low_trust_neutral": [
        "I'm watching you closely. Don't give me reason to doubt.",
        "Trust is earned, not given. You have work to do.",
        "I don't know you yet. Prove yourself to me."
    ],
    "low_trust_negative": [
        "Your actions concern me. I need to see better from you.",
        "I'm not sure about you. Change my mind.",
        "You're testing my patience. Choose wisely."
    ],
    
    # Fallback responses
    "fallback_positive": [
        "I'm here with you on this journey.",
        "Let's see what the path ahead holds for us.",
        "Together we can face whatever comes."
    ],
    "fallback_neutral": [
        "I'm observing your choices.",
        "The path forward is yours to choose.",
        "I'll be here to see how this unfolds."
    ],
    "fallback_negative": [
        "I'm watching how you handle this.",
        "Your decisions will shape what comes next.",
        "Choose your path carefully."
    ]
}

def load_npc_state(player_id: str, npc_id: str) -> Optional[float]:
    """Load trust value for specific NPC from npc_state.json"""
    try:
        # For now, we'll use a simplified approach since npc_state.json might not exist
        # In a real implementation, this would query the database
        return 0.5  # Default medium trust
    except Exception as e:
        print(f"Error loading NPC state: {e}")
        return None

def load_emotion_state(player_id: str) -> Optional[List[float]]:
    """Load emotion vector from emotion_state.json"""
    try:
        emotion_path = Path(__file__).parent.parent.parent / "backend" / "emotion_state.json"
        if emotion_path.exists():
            with open(emotion_path, 'r') as f:
                emotion_states = json.load(f)
                player_data = emotion_states.get(player_id, {})
                return player_data.get("vector", [0.0] * len(EMOTION_DIMENSIONS))
        return [0.0] * len(EMOTION_DIMENSIONS)  # Default neutral
    except Exception as e:
        print(f"Error loading emotion state: {e}")
        return None

def load_memory_recap(player_id: str) -> Optional[str]:
    """Load memory recap from memory_state.json"""
    try:
        memory_path = Path(__file__).parent / "memory" / "memory_state.json"
        if memory_path.exists():
            with open(memory_path, 'r') as f:
                memory_states = json.load(f)
                player_data = memory_states.get(player_id, {})
                return player_data.get("recap", "")
        return ""
    except Exception as e:
        print(f"Error loading memory recap: {e}")
        return None

def get_dominant_emotion(emotion_vector: List[float]) -> Tuple[str, float]:
    """Get the dominant emotion and its intensity"""
    if not emotion_vector or len(emotion_vector) != len(EMOTION_DIMENSIONS):
        return "neutral", 0.0
    
    max_index = max(range(len(emotion_vector)), key=lambda i: abs(emotion_vector[i]))
    max_value = emotion_vector[max_index]
    
    # Only consider it dominant if it's above a threshold
    if abs(max_value) < 0.3:
        return "neutral", 0.0
    
    return EMOTION_DIMENSIONS[max_index], max_value

def get_trust_category(trust: float) -> str:
    """Categorize trust level"""
    if trust >= 0.7:
        return "high_trust"
    elif trust >= 0.3:
        return "medium_trust"
    else:
        return "low_trust"

def get_emotion_category(emotion_name: str, intensity: float) -> str:
    """Categorize emotion for template selection"""
    if emotion_name == "neutral":
        return "neutral"
    elif intensity > 0:
        return "positive"
    else:
        return "negative"

def select_dialogue_template(trust_category: str, emotion_name: str, emotion_intensity: float) -> str:
    """Select appropriate dialogue template based on trust and emotion"""
    emotion_category = get_emotion_category(emotion_name, emotion_intensity)
    
    # Try specific combinations first
    template_key = f"{trust_category}_{emotion_name}"
    if template_key in DIALOGUE_TEMPLATES:
        return template_key
    
    # Fall back to general categories
    template_key = f"{trust_category}_{emotion_category}"
    if template_key in DIALOGUE_TEMPLATES:
        return template_key
    
    # Final fallback
    return f"fallback_{emotion_category}"

def generate_npc_dialogue(npc_id: str, player_id: str) -> str:
    """
    Generate dynamic NPC dialogue based on trust, emotion, and memory context.
    
    Args:
        npc_id: The NPC identifier
        player_id: The player identifier
        
    Returns:
        Generated dialogue string (max 150 characters)
    """
    # Load context data
    trust = load_npc_state(player_id, npc_id)
    emotion_vector = load_emotion_state(player_id)
    memory_recap = load_memory_recap(player_id)
    
    # Handle missing data with fallbacks
    if trust is None:
        trust = 0.5  # Default medium trust
    
    if emotion_vector is None:
        emotion_vector = [0.0] * len(EMOTION_DIMENSIONS)
    
    # Get dominant emotion
    dominant_emotion, emotion_intensity = get_dominant_emotion(emotion_vector)
    
    # Categorize trust level
    trust_category = get_trust_category(trust)
    
    # Select dialogue template
    template_key = select_dialogue_template(trust_category, dominant_emotion, emotion_intensity)
    
    # Get template options
    template_options = DIALOGUE_TEMPLATES.get(template_key, DIALOGUE_TEMPLATES["fallback_neutral"])
    
    # Select a random template (for now, just use the first one)
    # In a more sophisticated implementation, this could be weighted by context
    dialogue = template_options[0] if template_options else "I'm here with you."
    
    # Ensure dialogue is within character limit
    if len(dialogue) > 150:
        dialogue = dialogue[:147] + "..."
    
    return dialogue

def generate_npc_dialogue_with_context(npc_id: str, player_id: str, scene_context: str = "") -> str:
    """
    Enhanced version that can incorporate scene context for more specific dialogue.
    
    Args:
        npc_id: The NPC identifier
        player_id: The player identifier
        scene_context: Optional scene description for context-aware responses
        
    Returns:
        Generated dialogue string
    """
    base_dialogue = generate_npc_dialogue(npc_id, player_id)
    
    # For now, return the base dialogue
    # Future enhancement: incorporate scene_context for more specific responses
    return base_dialogue 