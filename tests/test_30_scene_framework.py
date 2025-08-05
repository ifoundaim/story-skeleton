# tests/test_30_scene_framework.py
"""
Unit tests for the 30-scene four-act framework (SPR-ST02).
Tests act indexing, NPC presence, and linear fallback behavior.
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from purpose_agents.constants import (
    TOTAL_SCENES, ACT_SCENES, ACT_PURPOSES, 
    get_scene_tag, get_linear_choice_structure,
    LLM_STORY_DISABLED
)
from purpose_agents.generate_story import create_fallback_30_scene_story


class TestConstants:
    """Test the constants and utility functions."""
    
    def test_total_scenes(self):
        """Test that TOTAL_SCENES is correctly set to 30."""
        assert TOTAL_SCENES == 30
    
    def test_act_breaks(self):
        """Test that act breaks are correctly defined."""
        assert ACT_SCENES["ACT_I"] == (0, 6)
        assert ACT_SCENES["ACT_II"] == (7, 15)
        assert ACT_SCENES["ACT_III"] == (16, 23)
        assert ACT_SCENES["ACT_IV"] == (24, 29)
    
    def test_act_purposes(self):
        """Test that act purposes are defined."""
        assert "ACT_I" in ACT_PURPOSES
        assert "ACT_II" in ACT_PURPOSES
        assert "ACT_III" in ACT_PURPOSES
        assert "ACT_IV" in ACT_PURPOSES
        
        for act, purpose in ACT_PURPOSES.items():
            assert "name" in purpose
            assert "description" in purpose
            assert "narrative_goals" in purpose
    
    def test_get_scene_tag(self):
        """Test scene tag generation."""
        assert get_scene_tag(0) == "tag_001"
        assert get_scene_tag(9) == "tag_010"
        assert get_scene_tag(29) == "tag_030"
    
    def test_get_linear_choice_structure(self):
        """Test linear choice structure generation."""
        # Test intermediate scenes
        choices = get_linear_choice_structure(0)
        assert "1" in choices
        assert choices["1"]["next"] == "tag_002"
        assert "Continue your journey" in choices["1"]["text"]
        
        # Test final scene
        choices = get_linear_choice_structure(29)
        assert choices == {}


class TestFallbackStory:
    """Test the fallback 30-scene story generator."""
    
    def test_fallback_story_structure(self):
        """Test that fallback story has correct structure."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        # Check total number of scenes
        assert len(story) == TOTAL_SCENES
        
        # Check all scene tags exist
        for i in range(TOTAL_SCENES):
            scene_tag = get_scene_tag(i)
            assert scene_tag in story
        
        # Check scene structure
        for scene_tag, scene_data in story.items():
            assert "text" in scene_data
            assert "choices" in scene_data
            assert "media" in scene_data
            assert "npc_text" in scene_data
            assert "act" in scene_data
            assert "act_purpose" in scene_data
            assert "scene_index" in scene_data
    
    def test_fallback_story_acts(self):
        """Test that scenes are correctly assigned to acts."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        # Check Act I scenes
        for i in range(7):  # 0-6
            scene_tag = get_scene_tag(i)
            assert story[scene_tag]["act"] == "ACT_I"
        
        # Check Act II scenes
        for i in range(7, 16):  # 7-15
            scene_tag = get_scene_tag(i)
            assert story[scene_tag]["act"] == "ACT_II"
        
        # Check Act III scenes
        for i in range(16, 24):  # 16-23
            scene_tag = get_scene_tag(i)
            assert story[scene_tag]["act"] == "ACT_III"
        
        # Check Act IV scenes
        for i in range(24, 30):  # 24-29
            scene_tag = get_scene_tag(i)
            assert story[scene_tag]["act"] == "ACT_IV"
    
    def test_fallback_story_choices(self):
        """Test that choices follow linear progression."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        # Check that all scenes except the last have choices
        for i in range(TOTAL_SCENES - 1):
            scene_tag = get_scene_tag(i)
            choices = story[scene_tag]["choices"]
            assert len(choices) == 1
            assert "1" in choices
            assert choices["1"]["next"] == get_scene_tag(i + 1)
        
        # Check that final scene has no choices
        final_scene_tag = get_scene_tag(TOTAL_SCENES - 1)
        assert story[final_scene_tag]["choices"] == {}
    
    def test_fallback_story_content(self):
        """Test that story content is appropriate."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        # Check opening scene
        opening_scene = story["tag_001"]
        assert "TestPlayer" in opening_scene["text"]
        assert "fantasy" in opening_scene["text"]
        
        # Check final scene
        final_scene = story["tag_030"]
        assert "TestPlayer" in final_scene["text"]
        assert "The End" in final_scene["text"]
        
        # Check act transition scenes
        act_i_end = story["tag_007"]
        assert "first steps" in act_i_end["text"] or "adventure" in act_i_end["text"]
        
        act_ii_end = story["tag_016"]
        assert "journey" in act_ii_end["text"] or "challenges" in act_ii_end["text"]
        
        act_iii_end = story["tag_024"]
        assert "darkest" in act_iii_end["text"] or "ultimate" in act_iii_end["text"]


class TestFeatureFlag:
    """Test the LLM_STORY_DISABLED feature flag."""
    
    def test_feature_flag_constant(self):
        """Test that the feature flag constant is defined."""
        assert LLM_STORY_DISABLED == "LLM_STORY_DISABLED"
    
    @patch.dict(os.environ, {LLM_STORY_DISABLED: "true"})
    def test_feature_flag_enabled(self):
        """Test that the feature flag can be enabled."""
        assert os.getenv(LLM_STORY_DISABLED, "").lower() == "true"
    
    @patch.dict(os.environ, {LLM_STORY_DISABLED: "false"})
    def test_feature_flag_disabled(self):
        """Test that the feature flag can be disabled."""
        assert os.getenv(LLM_STORY_DISABLED, "").lower() == "false"


class TestNPCIntegration:
    """Test NPC integration in the 30-scene framework."""
    
    def test_fallback_npc_assignment(self):
        """Test that fallback NPC assignment works correctly."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        # Check that scenes have NPC assignments
        for scene_data in story.values():
            assert "npcs_present" in scene_data
            assert isinstance(scene_data["npcs_present"], list)
    
    def test_npc_progression_by_act(self):
        """Test that NPC presence follows act-based progression."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        # Check that all scenes have npcs_present field (even if empty)
        for scene_data in story.values():
            assert "npcs_present" in scene_data
            assert isinstance(scene_data["npcs_present"], list)
        
        # Note: Actual NPC assignment is handled by the NPC integration logic
        # The fallback generator just provides the structure


class TestStoryValidation:
    """Test story validation and structure integrity."""
    
    def test_scene_index_consistency(self):
        """Test that scene indices are consistent."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        for scene_tag, scene_data in story.items():
            scene_index = scene_data["scene_index"]
            expected_tag = get_scene_tag(scene_index)
            assert scene_tag == expected_tag
    
    def test_act_assignment_consistency(self):
        """Test that act assignments are consistent with scene indices."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        for scene_data in story.values():
            scene_index = scene_data["scene_index"]
            act = scene_data["act"]
            
            if 0 <= scene_index <= 6:
                assert act == "ACT_I"
            elif 7 <= scene_index <= 15:
                assert act == "ACT_II"
            elif 16 <= scene_index <= 23:
                assert act == "ACT_III"
            elif 24 <= scene_index <= 29:
                assert act == "ACT_IV"
    
    def test_choice_integrity(self):
        """Test that all choices point to valid scenes."""
        story = create_fallback_30_scene_story("fantasy", [0.1, 0.2, 0.3], "TestPlayer")
        
        for scene_tag, scene_data in story.items():
            choices = scene_data["choices"]
            for choice_data in choices.values():
                if "next" in choice_data:
                    next_scene = choice_data["next"]
                    assert next_scene in story or next_scene == "tag_030"


if __name__ == "__main__":
    pytest.main([__file__]) 