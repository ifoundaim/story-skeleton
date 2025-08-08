"""
Tests for the Dynamic NPC Scene Integration System (SPR-NPC08)
"""

import pytest
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from npc.scene_integration import (
    NPCSceneIntegrator, 
    assign_npcs_to_scenes,
    get_scene_npcs,
    get_scene_npc_context
)
from npc.models import NPC
from db import SessionLocal


class TestNPCSceneIntegrator:
    """Test the NPCSceneIntegrator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.integrator = NPCSceneIntegrator()
        self.db = SessionLocal()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.db.close()
    
    def test_init(self):
        """Test integrator initialization."""
        assert self.integrator.scene_npc_cache == {}
        assert "Mentor" in self.integrator.role_assignment_rules
        assert "Rival" in self.integrator.role_assignment_rules
        assert "Companion" in self.integrator.role_assignment_rules
    
    def test_categorize_npcs_by_role(self):
        """Test NPC categorization by role."""
        # Create test NPCs
        npc1 = NPC(id=uuid.uuid4(), full_name="Elder Thorne", role="Mentor")
        npc2 = NPC(id=uuid.uuid4(), full_name="Captain Valen", role="Rival")
        npc3 = NPC(id=uuid.uuid4(), full_name="Luna Bright", role="Companion")
        npc4 = NPC(id=uuid.uuid4(), full_name="Unknown", role=None)  # Should default to Companion
        
        npcs = [npc1, npc2, npc3, npc4]
        categorized = self.integrator._categorize_npcs_by_role(npcs)
        
        assert "Mentor" in categorized
        assert "Rival" in categorized
        assert "Companion" in categorized
        assert len(categorized["Mentor"]) == 1
        assert len(categorized["Rival"]) == 1
        assert len(categorized["Companion"]) == 2  # Luna + Unknown
    
    def test_get_act_number(self):
        """Test act number determination."""
        # Test with 3 scenes (all Act 1)
        assert self.integrator._get_act_number(0, 3) == 1
        assert self.integrator._get_act_number(1, 3) == 1
        assert self.integrator._get_act_number(2, 3) == 1
        
        # Test with 6 scenes (2 acts)
        assert self.integrator._get_act_number(0, 6) == 1
        assert self.integrator._get_act_number(1, 6) == 1
        assert self.integrator._get_act_number(2, 6) == 2
        assert self.integrator._get_act_number(3, 6) == 2
        
        # Test with 8 scenes (3 acts)
        assert self.integrator._get_act_number(0, 8) == 1
        assert self.integrator._get_act_number(1, 8) == 1
        assert self.integrator._get_act_number(2, 8) == 2
        assert self.integrator._get_act_number(3, 8) == 2
        assert self.integrator._get_act_number(4, 8) == 3
        assert self.integrator._get_act_number(5, 8) == 3
    
    def test_get_eligible_npcs_for_act(self):
        """Test getting eligible NPCs for specific acts."""
        # Create test NPCs
        mentor = NPC(id=uuid.uuid4(), full_name="Mentor", role="Mentor")
        rival = NPC(id=uuid.uuid4(), full_name="Rival", role="Rival")
        companion = NPC(id=uuid.uuid4(), full_name="Companion", role="Companion")
        
        npcs_by_role = {
            "Mentor": [mentor],
            "Rival": [rival],
            "Companion": [companion]
        }
        
        # Act 1 should include Mentor and Companion
        act1_npcs = self.integrator._get_eligible_npcs_for_act(npcs_by_role, 1)
        assert mentor in act1_npcs
        assert companion in act1_npcs
        assert rival not in act1_npcs
        
        # Act 2 should include Rival and Companion
        act2_npcs = self.integrator._get_eligible_npcs_for_act(npcs_by_role, 2)
        assert rival in act2_npcs
        assert companion in act2_npcs
        assert mentor not in act2_npcs
    
    def test_get_max_npcs_for_scene(self):
        """Test maximum NPCs per scene calculation."""
        # Opening scene (index 0)
        assert self.integrator._get_max_npcs_for_scene(0, 8) == 1
        
        # Early scenes (index 1-3)
        assert self.integrator._get_max_npcs_for_scene(1, 8) == 2
        assert self.integrator._get_max_npcs_for_scene(2, 8) == 2
        assert self.integrator._get_max_npcs_for_scene(3, 8) == 2
        
        # Later scenes (index 4+)
        assert self.integrator._get_max_npcs_for_scene(4, 8) == 3
        assert self.integrator._get_max_npcs_for_scene(5, 8) == 3
        assert self.integrator._get_max_npcs_for_scene(6, 8) == 3
    
    def test_narrative_hooks_match_scene(self):
        """Test narrative hook matching logic."""
        # Create NPC with narrative hooks
        npc = NPC(
            id=uuid.uuid4(),
            full_name="Test NPC",
            narrative_hooks=["Knows ancient secrets", "Tests the player's worthiness"]
        )
        
        # Scene with matching keywords
        scene_text = "The ancient temple holds many secrets that test your worthiness."
        choice_texts = ["Explore the secrets", "Prove your worth"]
        
        assert self.integrator._narrative_hooks_match_scene(npc, scene_text, choice_texts) == True
        
        # Scene without matching keywords
        scene_text_no_match = "The forest is peaceful and quiet."
        choice_texts_no_match = ["Rest here", "Continue walking"]
        
        assert self.integrator._narrative_hooks_match_scene(npc, scene_text_no_match, choice_texts_no_match) == False
    
    def test_select_npcs_for_scene(self):
        """Test NPC selection for scenes."""
        # Create test NPCs
        mentor = NPC(id=uuid.uuid4(), full_name="Mentor", role="Mentor")
        companion = NPC(id=uuid.uuid4(), full_name="Companion", role="Companion")
        rival = NPC(id=uuid.uuid4(), full_name="Rival", role="Rival")
        
        eligible_npcs = [mentor, companion, rival]
        
        # Test selection with max 2 NPCs
        selected = self.integrator._select_npcs_for_scene(
            eligible_npcs, 2, "tag_001", {"text": "Opening scene"}
        )
        
        assert len(selected) <= 2
        # Mentor should be selected first due to priority
        if selected:
            assert selected[0].role == "Mentor"
    
    def test_create_scene_assignment_plan(self):
        """Test scene assignment plan creation."""
        # Create test NPCs
        mentor = NPC(id=uuid.uuid4(), full_name="Mentor", role="Mentor")
        companion = NPC(id=uuid.uuid4(), full_name="Companion", role="Companion")
        rival = NPC(id=uuid.uuid4(), full_name="Rival", role="Rival")
        
        npcs = [mentor, companion, rival]
        
        # Create test story
        story_dict = {
            "tag_001": {"text": "Opening scene"},
            "tag_002": {"text": "Early scene"},
            "tag_003": {"text": "Mid scene"},
            "tag_004": {"text": "Late scene"}
        }
        
        assignment_plan = self.integrator._create_scene_assignment_plan(npcs, story_dict)
        
        # Check that all scenes have assignments
        assert "tag_001" in assignment_plan
        assert "tag_002" in assignment_plan
        assert "tag_003" in assignment_plan
        assert "tag_004" in assignment_plan
        
        # Check that assignments contain valid NPC IDs
        for scene_tag, npc_ids in assignment_plan.items():
            assert isinstance(npc_ids, list)
            for npc_id in npc_ids:
                assert isinstance(npc_id, str)
    
    @pytest.mark.asyncio
    async def test_assign_npcs_to_scenes(self):
        """Test full NPC assignment workflow."""
        # Mock NPC generation
        mock_npcs = [
            NPC(id=uuid.uuid4(), full_name="Mentor", role="Mentor"),
            NPC(id=uuid.uuid4(), full_name="Companion", role="Companion"),
            NPC(id=uuid.uuid4(), full_name="Rival", role="Rival")
        ]
        
        with patch('npc.scene_integration.generate_story_npcs', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_npcs
            
            # Test story
            story_dict = {
                "tag_001": {"text": "Opening scene"},
                "tag_002": {"text": "Early scene"},
                "tag_003": {"text": "Mid scene"}
            }
            
            assignment_plan = await self.integrator.assign_npcs_to_scenes(
                player_id="test_player",
                player_name="Test Player",
                player_archetype="Hero",
                story_theme="Adventure",
                story_dict=story_dict,
                num_npcs=3
            )
            
            # Verify assignment plan
            assert isinstance(assignment_plan, dict)
            assert len(assignment_plan) == 3
            
            # Verify cache was updated
            assert "test_player" in self.integrator.scene_npc_cache
    
    def test_get_npcs_for_scene(self):
        """Test getting NPCs for a specific scene."""
        # Set up cache
        self.integrator.scene_npc_cache["test_player"] = {
            "tag_001": ["npc1", "npc2"],
            "tag_002": ["npc3"]
        }
        
        # Test existing scene
        npcs = self.integrator.get_npcs_for_scene("test_player", "tag_001")
        assert npcs == ["npc1", "npc2"]
        
        # Test non-existing scene
        npcs = self.integrator.get_npcs_for_scene("test_player", "tag_999")
        assert npcs == []
        
        # Test non-existing player
        npcs = self.integrator.get_npcs_for_scene("unknown_player", "tag_001")
        assert npcs == []
    
    def test_get_npc_context_for_scene(self):
        """Test getting detailed NPC context for a scene."""
        # Mock database query
        mock_npc = MagicMock()
        mock_npc.id = uuid.uuid4()
        mock_npc.full_name = "Test NPC"
        mock_npc.role = "Mentor"
        mock_npc.archetype = "Sage"
        mock_npc.trust = 0.7
        mock_npc.personality_traits = ["Wise", "Patient"]
        mock_npc.narrative_hooks = ["Knows secrets"]
        mock_npc.motivation = "To teach"
        mock_npc.relationship_to_player = "Mentor"
        
        with patch.object(self.db, 'query') as mock_query:
            mock_query.return_value.filter_by.return_value.first.return_value = mock_npc
            
            # Set up cache
            self.integrator.scene_npc_cache["test_player"] = {
                "tag_001": [str(mock_npc.id)]
            }
            
            context = self.integrator.get_npc_context_for_scene("test_player", "tag_001", self.db)
            
            assert "npcs_present" in context
            assert "npc_details" in context
            assert len(context["npc_details"]) == 1
            assert context["npc_details"][0]["full_name"] == "Test NPC"


@pytest.mark.asyncio
async def test_assign_npcs_to_scenes_function():
    """Test the convenience function."""
    with patch('npc.scene_integration.npc_integrator.assign_npcs_to_scenes', new_callable=AsyncMock) as mock_assign:
        mock_assign.return_value = {"tag_001": ["npc1"]}
        
        result = await assign_npcs_to_scenes(
            player_id="test_player",
            player_name="Test Player",
            player_archetype="Hero",
            story_theme="Adventure",
            story_dict={},
            num_npcs=3
        )
        
        assert result == {"tag_001": ["npc1"]}


def test_get_scene_npcs_function():
    """Test the convenience function."""
    with patch('npc.scene_integration.npc_integrator.get_npcs_for_scene') as mock_get:
        mock_get.return_value = ["npc1", "npc2"]
        
        result = get_scene_npcs("test_player", "tag_001")
        
        assert result == ["npc1", "npc2"]


def test_get_scene_npc_context_function():
    """Test the convenience function."""
    with patch('npc.scene_integration.npc_integrator.get_npc_context_for_scene') as mock_get:
        mock_get.return_value = {"npcs_present": ["npc1"]}
        
        result = get_scene_npc_context("test_player", "tag_001")
        
        assert result == {"npcs_present": ["npc1"]}


class TestIntegrationScenarios:
    """Test integration scenarios with different story structures."""
    
    def test_hero_archetype_integration(self):
        """Test integration with Hero archetype."""
        integrator = NPCSceneIntegrator()
        
        # Create Hero-appropriate NPCs
        mentor = NPC(id=uuid.uuid4(), full_name="Elder Thorne", role="Mentor")
        rival = NPC(id=uuid.uuid4(), full_name="Captain Valen", role="Rival")
        companion = NPC(id=uuid.uuid4(), full_name="Luna Bright", role="Companion")
        
        npcs = [mentor, rival, companion]
        
        # 8-scene story structure
        story_dict = {
            f"tag_{i:03d}": {"text": f"Scene {i}"} for i in range(1, 9)
        }
        
        assignment_plan = integrator._create_scene_assignment_plan(npcs, story_dict)
        
        # Verify progressive introduction
        # Act 1 (scenes 1-2): Should have Mentor
        assert any("Mentor" in [npc.role for npc in npcs if str(npc.id) in assignment_plan["tag_001"]])
        
        # Act 2 (scenes 3-4): Should have Rival
        assert any("Rival" in [npc.role for npc in npcs if str(npc.id) in assignment_plan["tag_003"]])
        
        # Act 3 (scenes 5-8): Should have multiple NPCs
        assert len(assignment_plan["tag_005"]) >= 2
    
    def test_sage_archetype_integration(self):
        """Test integration with Sage archetype."""
        integrator = NPCSceneIntegrator()
        
        # Create Sage-appropriate NPCs
        apprentice = NPC(id=uuid.uuid4(), full_name="Luna Bright", role="Apprentice")
        sage = NPC(id=uuid.uuid4(), full_name="Master Sage", role="Sage")
        
        npcs = [apprentice, sage]
        
        # 6-scene story structure
        story_dict = {
            f"tag_{i:03d}": {"text": f"Scene {i}"} for i in range(1, 7)
        }
        
        assignment_plan = integrator._create_scene_assignment_plan(npcs, story_dict)
        
        # Verify Sage-appropriate placement
        # Should have Sage in early scenes
        assert any("Sage" in [npc.role for npc in npcs if str(npc.id) in assignment_plan["tag_001"]])
        
        # Should have Apprentice throughout
        assert any("Apprentice" in [npc.role for npc in npcs if str(npc.id) in assignment_plan["tag_002"]]) 