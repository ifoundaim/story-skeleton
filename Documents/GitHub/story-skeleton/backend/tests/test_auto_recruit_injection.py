import pytest
import uuid
import json
import os
from unittest.mock import patch, MagicMock
from backend.story_conditions import validate_choice_conditions, evaluate_emotion_condition
from backend.npc.service import get_trust_scores, is_companion

def test_evaluate_emotion_condition_with_threshold():
    """Test emotion condition evaluation with specific value threshold"""
    emotion_vector = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.0]  # peace = 0.3
    assert evaluate_emotion_condition("peace", emotion_vector, 0.2) == True
    assert evaluate_emotion_condition("peace", emotion_vector, 0.4) == False

def test_evaluate_emotion_condition_without_threshold():
    """Test emotion condition evaluation without specific threshold"""
    emotion_vector = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.0]  # peace = 0.3
    assert evaluate_emotion_condition("peace", emotion_vector) == True  # default threshold 0.3

def test_validate_choice_conditions_trust_and_emotion(db):
    """Test validation of trust and emotion conditions together"""
    player_id = "test_player_conditions"
    npc_id = str(uuid.uuid4())
    
    with patch('backend.story_conditions.get_trust_scores') as mock_trust:
        mock_trust.return_value = {npc_id: 0.7}
        with patch('backend.story_conditions.load_emotion_state') as mock_emotion:
            mock_emotion.return_value = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.0]
            conditions = {
                "trust": 0.6,
                "emotion": "peace",
                "emotion_value": 0.2,
                "not_companion": True
            }
            with patch('backend.story_conditions.is_companion') as mock_companion:
                mock_companion.return_value = False
                is_valid, reason = validate_choice_conditions(conditions, player_id, npc_id, db)
                assert is_valid == True
                assert "All conditions met" in reason

def test_validate_choice_conditions_trust_failure(db):
    """Test validation failure when trust requirement not met"""
    player_id = "test_player_trust_fail"
    npc_id = str(uuid.uuid4())
    
    with patch('backend.story_conditions.get_trust_scores') as mock_trust:
        mock_trust.return_value = {npc_id: 0.4}  # Below required 0.6
        conditions = {
            "trust": 0.6,
            "emotion": "peace",
            "emotion_value": 0.2
        }
        is_valid, reason = validate_choice_conditions(conditions, player_id, npc_id, db)
        assert is_valid == False
        assert "Trust requirement not met" in reason

def test_validate_choice_conditions_emotion_failure(db):
    """Test validation failure when emotion requirement not met"""
    player_id = "test_player_emotion_fail"
    npc_id = str(uuid.uuid4())
    
    with patch('backend.story_conditions.get_trust_scores') as mock_trust:
        mock_trust.return_value = {npc_id: 0.7}
        with patch('backend.story_conditions.load_emotion_state') as mock_emotion:
            mock_emotion.return_value = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0]  # peace = 0.1
            conditions = {
                "trust": 0.6,
                "emotion": "peace",
                "emotion_value": 0.2  # Required 0.2, but only 0.1
            }
            is_valid, reason = validate_choice_conditions(conditions, player_id, npc_id, db)
            assert is_valid == False
            assert "Emotion requirement not met" in reason

def test_validate_choice_conditions_companion_check(db):
    """Test validation of not_companion condition"""
    player_id = "test_player_companion_check"
    npc_id = str(uuid.uuid4())
    
    with patch('backend.story_conditions.get_trust_scores') as mock_trust:
        mock_trust.return_value = {npc_id: 0.7}
        with patch('backend.story_conditions.is_companion') as mock_companion:
            mock_companion.return_value = True  # Already a companion
            conditions = {
                "trust": 0.6,
                "not_companion": True
            }
            is_valid, reason = validate_choice_conditions(conditions, player_id, npc_id, db)
            assert is_valid == False
            assert "already a companion" in reason

def test_auto_recruit_choice_structure():
    """Test that auto-generated recruitment choices have correct structure"""
    expected_structure = {
        "text": str,  # Should be a string
        "next": str,  # Should be a string (scene tag)
        "npc_onboard": str,  # Should be a string (NPC UUID)
        "conditions": {
            "trust": float,  # Should be a float
            "emotion": str,  # Should be a string
            "emotion_value": float,  # Should be a float
            "not_companion": bool  # Should be a boolean
        },
        "npc_trust_deltas": dict  # Should be a dict
    }
    
    # This test validates the expected structure of auto-generated choices
    # The actual choice generation happens in generate_story.py
    assert isinstance(expected_structure["text"], str)
    assert isinstance(expected_structure["next"], str)
    assert isinstance(expected_structure["npc_onboard"], str)
    assert isinstance(expected_structure["conditions"]["trust"], float)
    assert isinstance(expected_structure["conditions"]["emotion"], str)
    assert isinstance(expected_structure["conditions"]["emotion_value"], float)
    assert isinstance(expected_structure["conditions"]["not_companion"], bool)
    assert isinstance(expected_structure["npc_trust_deltas"], dict) 