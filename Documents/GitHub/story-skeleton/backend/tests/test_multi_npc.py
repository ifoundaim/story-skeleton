"""
Tests for Multi-NPC Support and Group Dialogue Dynamics (SPR-NPC03)
"""

import pytest
import uuid
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

# Import the modules we're testing
from npc.models import NPCState
from npc.service import (
    get_state, 
    apply_trust, 
    apply_trust_to_multiple,
    get_trust_scores,
    ensure_default_npcs,
    get_npc_by_id
)
from npc.router import (
    get_npcs,
    update_npc,
    update_multiple_npcs,
    generate_group_dialogue
)

class TestMultiNPCService:
    """Test multi-NPC service functions"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_npcs(self):
        """Sample NPC data for testing"""
        lyra_id = str(uuid.uuid4())
        orin_id = str(uuid.uuid4())
        return [
            NPCState(
                id=uuid.UUID(lyra_id),
                player_id="test_player",
                name="Lyra",
                trust=0.7,
                meta={"personality": "supportive"}
            ),
            NPCState(
                id=uuid.UUID(orin_id),
                player_id="test_player", 
                name="Orin",
                trust=0.3,
                meta={"personality": "skeptical"}
            )
        ]
    
    def test_get_trust_scores(self, mock_db, sample_npcs):
        """Test getting trust scores for all NPCs"""
        mock_db.query.return_value.filter_by.return_value.all.return_value = sample_npcs
        
        trust_scores = get_trust_scores("test_player", mock_db)
        
        assert len(trust_scores) == 2
        assert trust_scores[str(sample_npcs[0].id)] == 0.7
        assert trust_scores[str(sample_npcs[1].id)] == 0.3
    
    def test_apply_trust_to_multiple(self, mock_db, sample_npcs):
        """Test applying trust deltas to multiple NPCs"""
        # Mock database queries for each NPC
        def mock_query_side_effect(*args, **kwargs):
            query_mock = Mock()
            query_mock.filter_by.return_value.one.side_effect = sample_npcs
            return query_mock
        
        mock_db.query.side_effect = mock_query_side_effect
        
        trust_deltas = {
            str(sample_npcs[0].id): 0.2,
            str(sample_npcs[1].id): -0.1
        }
        
        with patch('npc.service.apply_trust') as mock_apply_trust:
            mock_apply_trust.side_effect = sample_npcs
            
            updated_npcs = apply_trust_to_multiple("test_player", trust_deltas, mock_db)
            
            assert len(updated_npcs) == 2
            assert mock_apply_trust.call_count == 2
    
    def test_ensure_default_npcs(self, mock_db):
        """Test ensuring default NPCs exist"""
        # Mock empty existing NPCs
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        
        with patch('npc.service.create_default_npc') as mock_create:
            mock_create.return_value = Mock(spec=NPCState)
            
            npcs = ensure_default_npcs("test_player", mock_db)
            
            # Should create Lyra and Orin
            assert mock_create.call_count == 2
    
    def test_get_npc_by_id(self, mock_db, sample_npcs):
        """Test getting a specific NPC by ID"""
        target_npc = sample_npcs[0]
        mock_db.query.return_value.filter_by.return_value.one.return_value = target_npc
        
        result = get_npc_by_id("test_player", str(target_npc.id), mock_db)
        
        assert result == target_npc
    
    def test_get_npc_by_id_not_found(self, mock_db):
        """Test getting NPC that doesn't exist"""
        from sqlalchemy.exc import NoResultFound
        mock_db.query.return_value.filter_by.return_value.one.side_effect = NoResultFound()
        
        result = get_npc_by_id("test_player", "nonexistent", mock_db)
        
        assert result is None


class TestGroupDialogue:
    """Test group dialogue generation"""
    
    def test_single_npc_dialogue_fallback(self):
        """Test that single NPC dialogue falls back to individual system"""
        from codex.npc.npc_group_dialogue import generate_group_dialogue
        
        with patch('codex.npc.npc_group_dialogue.generate_npc_dialogue') as mock_gen:
            mock_gen.return_value = "Hello, traveler."
            
            result = generate_group_dialogue(["npc_lyra"], "test_player")
            
            assert len(result) == 1
            assert result[0]["text"] == "Hello, traveler."
            assert result[0]["npc_id"] == "npc_lyra"
    
    def test_multi_npc_dialogue(self):
        """Test multi-NPC group dialogue generation"""
        from codex.npc.npc_group_dialogue import generate_group_dialogue
        
        with patch('codex.npc.npc_group_dialogue.load_npc_states') as mock_load:
            mock_load.return_value = {"npc_lyra": 0.7, "npc_orin": 0.3}
            
            with patch('codex.npc.npc_group_dialogue.load_emotion_state') as mock_emotion:
                mock_emotion.return_value = [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                
                result = generate_group_dialogue(["npc_lyra", "npc_orin"], "test_player")
                
                assert len(result) == 2
                assert result[0]["npc_id"] == "npc_lyra"
                assert result[1]["npc_id"] == "npc_orin"
                assert "trust" in result[0]
                assert "trust" in result[1]
    
    def test_trust_dynamic_classification(self):
        """Test trust dynamic classification"""
        from codex.npc.npc_group_dialogue import get_trust_dynamic
        
        # Both high trust
        high_trust = {"npc1": 0.8, "npc2": 0.9}
        assert get_trust_dynamic(high_trust) == "both_high_trust"
        
        # Both low trust
        low_trust = {"npc1": 0.1, "npc2": 0.2}
        assert get_trust_dynamic(low_trust) == "both_low_trust"
        
        # Mixed trust
        mixed_trust = {"npc1": 0.8, "npc2": 0.2}
        assert get_trust_dynamic(mixed_trust) == "mixed_trust"
    
    def test_dialogue_character_limit(self):
        """Test that dialogue respects character limits"""
        from codex.npc.npc_group_dialogue import generate_group_dialogue
        
        with patch('codex.npc.npc_group_dialogue.load_npc_states') as mock_load:
            mock_load.return_value = {"npc_lyra": 0.5}
            
            with patch('codex.npc.npc_group_dialogue.load_emotion_state') as mock_emotion:
                mock_emotion.return_value = [0.0] * 8
                
                result = generate_group_dialogue(["npc_lyra"], "test_player")
                
                assert len(result) == 1
                assert len(result[0]["text"]) <= 150


class TestMultiNPCAPI:
    """Test multi-NPC API endpoints"""
    
    @pytest.fixture
    def mock_db_dependency(self):
        """Mock database dependency"""
        return Mock(spec=Session)
    
    def test_get_npcs_ensures_defaults(self, mock_db_dependency):
        """Test that getting NPCs ensures default NPCs exist"""
        sample_npcs = [
            Mock(id=uuid.uuid4(), player_id="test", name="Lyra", trust=0.5, last_seen=None, meta={}),
            Mock(id=uuid.uuid4(), player_id="test", name="Orin", trust=0.3, last_seen=None, meta={})
        ]
        
        with patch('npc.router.ensure_default_npcs') as mock_ensure:
            mock_ensure.return_value = sample_npcs
            
            result = get_npcs("test_player", mock_db_dependency)
            
            assert len(result) == 2
            assert mock_ensure.called
    
    def test_update_multiple_npcs_endpoint(self, mock_db_dependency):
        """Test multiple NPC trust update endpoint"""
        from npc.router import MultipleTrustUpdateRequest
        
        request = MultipleTrustUpdateRequest(
            player_id="test_player",
            trust_deltas={"npc1": 0.2, "npc2": -0.1}
        )
        
        mock_npcs = [
            Mock(id="npc1", player_id="test_player", name="NPC1", trust=0.7, last_seen=None, meta={}),
            Mock(id="npc2", player_id="test_player", name="NPC2", trust=0.4, last_seen=None, meta={})
        ]
        
        with patch('npc.router.apply_trust_to_multiple') as mock_apply:
            mock_apply.return_value = mock_npcs
            
            result = update_multiple_npcs(request, mock_db_dependency)
            
            assert result["player_id"] == "test_player"
            assert len(result["updated_npcs"]) == 2
            assert mock_apply.called
    
    def test_group_dialogue_endpoint(self, mock_db_dependency):
        """Test group dialogue generation endpoint"""
        from npc.router import NPCDialogueRequest
        
        request = NPCDialogueRequest(
            player_id="test_player",
            npc_ids=["npc_lyra", "npc_orin"],
            scene_context="A tense moment"
        )
        
        mock_dialogue = [
            {"npc_id": "npc_lyra", "name": "Lyra", "text": "We should be careful.", "trust": 0.7},
            {"npc_id": "npc_orin", "name": "Orin", "text": "I agree.", "trust": 0.3}
        ]
        
        with patch('codex.npc.npc_group_dialogue.generate_group_dialogue_with_context') as mock_gen:
            mock_gen.return_value = mock_dialogue
            
            with patch('npc.router.ensure_default_npcs'):
                result = generate_group_dialogue(request, mock_db_dependency)
                
                assert result["player_id"] == "test_player"
                assert len(result["dialogue"]) == 2
                assert result["scene_context"] == "A tense moment"


class TestStoryIntegration:
    """Test story generation and choice integration"""
    
    def test_story_includes_npc_presence(self):
        """Test that generated stories include NPC presence information"""
        from purpose_agents.generate_story import create_fallback_8_node_story
        
        story = create_fallback_8_node_story("test_theme", [0.5] * 8)
        
        # Check that at least one node has NPC presence info
        has_npcs_present = any("npcs_present" in node for node in story.values())
        assert has_npcs_present
    
    def test_choice_includes_multi_npc_trust_deltas(self):
        """Test that choices can include multi-NPC trust deltas"""
        from purpose_agents.generate_story import create_fallback_8_node_story
        
        story = create_fallback_8_node_story("test_theme", [0.5] * 8)
        
        # Check that at least one choice has multi-NPC trust deltas
        has_multi_trust = False
        for node in story.values():
            for choice in node.get("choices", {}).values():
                if "npc_trust_deltas" in choice:
                    has_multi_trust = True
                    break
            if has_multi_trust:
                break
        
        assert has_multi_trust
    
    def test_backward_compatibility_maintained(self):
        """Test that legacy single trust_delta is still supported"""
        from purpose_agents.generate_story import create_fallback_8_node_story
        
        story = create_fallback_8_node_story("test_theme", [0.5] * 8)
        
        # Check that choices still have trust_delta for backward compatibility
        has_legacy_trust = False
        for node in story.values():
            for choice in node.get("choices", {}).values():
                if "trust_delta" in choice:
                    has_legacy_trust = True
                    break
            if has_legacy_trust:
                break
        
        assert has_legacy_trust


if __name__ == "__main__":
    pytest.main([__file__])