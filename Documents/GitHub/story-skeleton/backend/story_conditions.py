"""
Story condition validation and evaluation for choice availability.
"""

from typing import Dict, Any, List, Tuple, Optional
from npc.service import get_trust_scores, is_companion
from emotion.router import load_emotion_state

def get_dominant_emotion(emotion_vector: List[float]) -> Tuple[str, float]:
    """Get the dominant emotion and its intensity from an emotion vector."""
    if not emotion_vector:
        return "neutral", 0.0
    
    emotion_names = ["joy", "grief", "awe", "fear", "desire", "disgust", "peace", "rage"]
    
    max_intensity = max(emotion_vector)
    max_index = emotion_vector.index(max_intensity)
    
    if max_index < len(emotion_names):
        return emotion_names[max_index], max_intensity
    
    return "neutral", 0.0

def evaluate_emotion_condition(condition_value: str, emotion_vector: List[float], emotion_value: float = None) -> bool:
    """Evaluate emotion-based conditions"""
    if not emotion_vector:
        return False

    emotion_names = ["joy", "grief", "awe", "fear", "desire", "disgust", "peace", "rage"]

    if condition_value.lower() in [name.lower() for name in emotion_names]:
        emotion_idx = emotion_names.index(condition_value.lower())
        if emotion_idx < len(emotion_vector):
            emotion_intensity = emotion_vector[emotion_idx]
            threshold = emotion_value if emotion_value is not None else 0.3
            return emotion_intensity >= threshold

    dominant_emotion, intensity = get_dominant_emotion(emotion_vector)
    if condition_value.lower() == dominant_emotion.lower():
        return intensity > 0.3
    return False

def validate_choice_conditions(conditions: Dict[str, Any], player_id: str, npc_id: str, db) -> Tuple[bool, str]:
    """
    Validate if choice conditions are met for a given player and NPC.
    
    Args:
        conditions: Dictionary of conditions to check
        player_id: Player ID
        npc_id: NPC ID
        db: Database session
        
    Returns:
        Tuple of (is_valid, reason)
    """
    if not conditions:
        return True, "No conditions to validate"
    
    # Check trust condition
    if "trust" in conditions:
        trust_threshold = conditions["trust"]
        trust_scores = get_trust_scores(player_id, db)
        current_trust = trust_scores.get(npc_id, 0.0)
        
        if current_trust < trust_threshold:
            return False, f"Trust requirement not met: required {trust_threshold}, current {current_trust:.1f}"
    
    # Check emotion condition
    if "emotion" in conditions:
        emotion_type = conditions["emotion"]
        emotion_vector = load_emotion_state(player_id)
        emotion_value_threshold = conditions.get("emotion_value")
        
        if not evaluate_emotion_condition(emotion_type, emotion_vector, emotion_value_threshold):
            emotion_names = ["joy", "grief", "awe", "fear", "desire", "disgust", "peace", "rage"]
            if emotion_type.lower() in [name.lower() for name in emotion_names]:
                emotion_idx = emotion_names.index(emotion_type.lower())
                if emotion_vector and emotion_idx < len(emotion_vector):
                    current_value = emotion_vector[emotion_idx]
                    required_value = emotion_value_threshold if emotion_value_threshold is not None else 0.3
                    return False, f"Emotion requirement not met: required {emotion_type} >= {required_value:.1f}, current {current_value:.1f}"

            current_emotion, intensity = get_dominant_emotion(emotion_vector) if emotion_vector else ("neutral", 0.0)
            return False, f"Emotion requirement not met: required {emotion_type}, current {current_emotion} ({intensity:.1f})"
    
    # Check companion condition
    if "not_companion" in conditions and conditions["not_companion"]:
        if is_companion(player_id, npc_id, db):
            return False, f"NPC {npc_id} is already a companion"
    
    return True, "All conditions met" 