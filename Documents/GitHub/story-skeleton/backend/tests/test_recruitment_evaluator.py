"""
Unit tests for RecruitmentEvaluator
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
import uuid

from story_recruitment import RecruitmentEvaluator, RecruitmentEvaluation
from npc.models import NPCState


class TestRecruitmentEvaluator:
    
    def setup_method(self):
        """Set up test fixtures"""
        self.evaluator = RecruitmentEvaluator()
        self.mock_db = Mock(spec=Session)
        self.player_id = "test_player_123"
        
        # Create a mock NPC
        self.mock_npc = Mock(spec=NPCState)
        self.mock_npc.id = uuid.uuid4()
        self.mock_npc.name = "Test NPC"
        self.mock_npc.trust = 0.0
        self.mock_npc.meta = {}
    
    def test_low_trust_npc_returns_false(self):
        """Test that NPCs with low trust are not recruited"""
        # Arrange
        self.mock_npc.trust = 0.3  # Below 0.60 threshold
        scene = {"scene_index": 20}  # Act III scene
        
        with patch('story_recruitment.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = self.evaluator.evaluate(
                str(self.mock_npc.id), 
                scene, 
                self.player_id, 
                self.mock_db
            )
        
        # Assert
        assert not result.should_recruit
        assert "Trust 0.30 below threshold 0.6" in result.rationale
        assert result.trust_level == 0.3
    
    def test_high_trust_npc_returns_true_in_act_iii(self):
        """Test that high-trust NPCs are recruited in Act III"""
        # Arrange
        self.mock_npc.trust = 0.75  # Above 0.60 threshold
        scene = {"scene_index": 18}  # Act III scene
        
        with patch('story_recruitment.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = self.evaluator.evaluate(
                str(self.mock_npc.id), 
                scene, 
                self.player_id, 
                self.mock_db
            )
        
        # Assert
        assert result.should_recruit
        assert "Trust 0.75 ≥ 0.6" in result.rationale
        assert "Scene 18 ≥ 16" in result.rationale
        assert result.trust_level == 0.75
    
    def test_early_scene_returns_false(self):
        """Test that recruitment is not offered in early scenes"""
        # Arrange
        self.mock_npc.trust = 0.80  # High trust
        scene = {"scene_index": 10}  # Act II scene (too early)
        
        with patch('story_recruitment.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = self.evaluator.evaluate(
                str(self.mock_npc.id), 
                scene, 
                self.player_id, 
                self.mock_db
            )
        
        # Assert
        assert not result.should_recruit
        assert "Scene 10 too early" in result.rationale
    
    def test_already_companion_returns_false(self):
        """Test that already recruited NPCs are not offered again"""
        # Arrange
        self.mock_npc.trust = 0.80
        self.mock_npc.meta = {"is_companion": True}
        scene = {"scene_index": 20}
        
        with patch('story_recruitment.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = self.evaluator.evaluate(
                str(self.mock_npc.id), 
                scene, 
                self.player_id, 
                self.mock_db
            )
        
        # Assert
        assert not result.should_recruit
        assert "already a companion" in result.rationale
    
    def test_cooldown_period_enforced(self):
        """Test that cooldown prevents rapid re-invitations"""
        # Arrange
        self.mock_npc.trust = 0.80
        self.mock_npc.meta = {
            "is_companion": False,
            "last_invite_scene_index": 19  # Invited 1 scene ago (need 2)
        }
        scene = {"scene_index": 20}
        
        with patch('story_recruitment.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = self.evaluator.evaluate(
                str(self.mock_npc.id), 
                scene, 
                self.player_id, 
                self.mock_db
            )
        
        # Assert
        assert not result.should_recruit
        assert "Cooldown active" in result.rationale
    
    def test_cooldown_expired_returns_true(self):
        """Test that recruitment is allowed after cooldown expires"""
        # Arrange
        self.mock_npc.trust = 0.80
        self.mock_npc.meta = {
            "is_companion": False,
            "last_invite_scene_index": 17  # Invited 3 scenes ago (cooldown expired)
        }
        scene = {"scene_index": 20}
        
        with patch('story_recruitment.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = self.evaluator.evaluate(
                str(self.mock_npc.id), 
                scene, 
                self.player_id, 
                self.mock_db
            )
        
        # Assert
        assert result.should_recruit
        assert "Trust 0.80 ≥ 0.6" in result.rationale
    
    def test_victory_scene_bonus(self):
        """Test that victory scenes provide bonus context"""
        # Arrange
        self.mock_npc.trust = 0.80
        scene = {
            "scene_index": 20,
            "narrative_purpose": "Victory"
        }
        
        with patch('story_recruitment.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = self.evaluator.evaluate(
                str(self.mock_npc.id), 
                scene, 
                self.player_id, 
                self.mock_db
            )
        
        # Assert
        assert result.should_recruit
        assert "Victory scene bonus" in result.rationale
    
    def test_emotion_alignment_bonus(self):
        """Test that emotional alignment provides bonus context"""
        # Arrange
        self.mock_npc.trust = 0.80
        self.mock_npc.meta = {"compatible_emotions": ["joy", "peace"]}
        scene = {"scene_index": 20}
        player_state = {"emotion": "joy"}
        
        with patch('story_recruitment.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = self.evaluator.evaluate(
                str(self.mock_npc.id), 
                scene, 
                self.player_id, 
                self.mock_db,
                player_state
            )
        
        # Assert
        assert result.should_recruit
        assert "Emotional alignment bonus" in result.rationale
    
    def test_npc_not_found_returns_false(self):
        """Test that missing NPCs return false"""
        # Arrange
        scene = {"scene_index": 20}
        
        with patch('story_recruitment.get_npc_by_id', return_value=None):
            # Act
            result = self.evaluator.evaluate(
                "missing_npc_id", 
                scene, 
                self.player_id, 
                self.mock_db
            )
        
        # Assert
        assert not result.should_recruit
        assert "NPC not found" in result.rationale
        assert result.npc_name == "Unknown"
    
    def test_mark_invite_sent(self):
        """Test that marking invite sent updates NPC metadata"""
        # Arrange
        scene_index = 20
        self.mock_npc.meta = {}
        
        # Act
        self.evaluator.mark_invite_sent(self.mock_npc, scene_index, self.mock_db)
        
        # Assert
        assert self.mock_npc.meta["last_invite_scene_index"] == scene_index
        self.mock_db.commit.assert_called_once() 