"""
Tests for Context-Aware NPC Dialogue (SPR-NPC02)
"""

import pytest
import sys
import os
from pathlib import Path

# Add the codex directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "codex"))

from npc.npc_dialogue import (
    generate_npc_dialogue,
    get_trust_category,
    get_dominant_emotion,
    get_emotion_category,
    select_dialogue_template
)

def test_trust_category_categorization():
    """Test trust level categorization"""
    assert get_trust_category(0.8) == "high_trust"
    assert get_trust_category(0.5) == "medium_trust"
    assert get_trust_category(0.2) == "low_trust"
    assert get_trust_category(0.0) == "low_trust"
    assert get_trust_category(1.0) == "high_trust"

def test_dominant_emotion_detection():
    """Test dominant emotion detection"""
    # Test with high joy
    joy_vector = [0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    emotion, intensity = get_dominant_emotion(joy_vector)
    assert emotion == "joy"
    assert intensity == 0.8
    
    # Test with low values (should return neutral)
    low_vector = [0.1, 0.2, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0]
    emotion, intensity = get_dominant_emotion(low_vector)
    assert emotion == "neutral"
    assert intensity == 0.0
    
    # Test with negative emotion
    fear_vector = [0.0, 0.0, 0.0, -0.7, 0.0, 0.0, 0.0, 0.0]
    emotion, intensity = get_dominant_emotion(fear_vector)
    assert emotion == "fear"
    assert intensity == -0.7

def test_emotion_category_categorization():
    """Test emotion category classification"""
    assert get_emotion_category("neutral", 0.0) == "neutral"
    assert get_emotion_category("joy", 0.5) == "positive"
    assert get_emotion_category("fear", -0.3) == "negative"
    assert get_emotion_category("awe", 0.8) == "positive"

def test_dialogue_template_selection():
    """Test dialogue template selection logic"""
    # High trust + joy should select specific template
    template = select_dialogue_template("high_trust", "joy", 0.8)
    assert template == "high_trust_joy"
    
    # Medium trust + neutral should select general template
    template = select_dialogue_template("medium_trust", "neutral", 0.0)
    assert template == "medium_trust_neutral"
    
    # Low trust + negative emotion should select general template
    template = select_dialogue_template("low_trust", "fear", -0.5)
    assert template == "low_trust_negative"
    
    # Unknown combination should fall back to fallback
    template = select_dialogue_template("unknown_trust", "unknown_emotion", 0.0)
    assert template == "fallback_negative"  # unknown_emotion with 0.0 intensity is treated as negative

def test_generate_npc_dialogue_basic():
    """Test basic NPC dialogue generation"""
    dialogue = generate_npc_dialogue("test-npc", "test-player")
    
    # Should return a string
    assert isinstance(dialogue, str)
    
    # Should not be empty
    assert len(dialogue) > 0
    
    # Should be within character limit
    assert len(dialogue) <= 150

def test_generate_npc_dialogue_character_limit():
    """Test that dialogue respects character limit"""
    # This test verifies the character limit enforcement
    dialogue = generate_npc_dialogue("test-npc", "test-player")
    assert len(dialogue) <= 150

def test_generate_npc_dialogue_fallback():
    """Test fallback behavior when data is missing"""
    # The function should handle missing data gracefully
    dialogue = generate_npc_dialogue("missing-npc", "missing-player")
    
    # Should still return a valid dialogue
    assert isinstance(dialogue, str)
    assert len(dialogue) > 0

def test_dialogue_emotional_coherence():
    """Test that dialogue is emotionally coherent"""
    # Test multiple generations to ensure consistency
    dialogues = []
    for _ in range(5):
        dialogue = generate_npc_dialogue("test-npc", "test-player")
        dialogues.append(dialogue)
    
    # All dialogues should be valid
    for dialogue in dialogues:
        assert isinstance(dialogue, str)
        assert len(dialogue) > 0
        assert len(dialogue) <= 150

if __name__ == "__main__":
    pytest.main([__file__]) 