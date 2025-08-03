"""
Tests for NPC06 - Dynamic NPC Seed Generator & Profile Factory
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from backend.npc.profile_seed import generate_dynamic_npcs, seed_dynamic_npcs
from backend.npc.service import get_npc_by_id, get_state
from backend.npc.models import NPCState


@pytest.fixture
def mock_npc_response():
    """Mock NPC response from LLM"""
    return [
        {
            "id": "lyra_explorer",
            "full_name": "Lyra Explorer",
            "archetype": "Explorer",
            "role": "Mentor",
            "skill_tag": "Survival",
            "one_line_summary": "Wise guide from the Crystal Forest who knows ancient paths.",
            "baseline_trust": 0.35
        },
        {
            "id": "thorne_guardian",
            "full_name": "Thorne Guardian",
            "archetype": "Guardian",
            "role": "Guardian",
            "skill_tag": "Combat",
            "one_line_summary": "Stoic warrior from the Iron Tower who protects the innocent.",
            "baseline_trust": 0.42
        },
        {
            "id": "mira_healer",
            "full_name": "Mira Healer",
            "archetype": "Healer",
            "role": "Healer",
            "skill_tag": "Magic",
            "one_line_summary": "Gentle healer from the Sacred Temple who mends wounds.",
            "baseline_trust": 0.28
        },
        {
            "id": "dante_trickster",
            "full_name": "Dante Trickster",
            "archetype": "Trickster",
            "role": "Trickster",
            "skill_tag": "Social",
            "one_line_summary": "Clever rogue from the Shadow Guild who knows all secrets.",
            "baseline_trust": 0.25
        },
        {
            "id": "selene_mystic",
            "full_name": "Selene Mystic",
            "archetype": "Mystic",
            "role": "Wild-card",
            "skill_tag": "Tech",
            "one_line_summary": "Enigmatic mystic from the Floating City who sees beyond.",
            "baseline_trust": 0.38
        },
        {
            "id": "caelis_courier",
            "full_name": "Caelis Courier",
            "full_name": "Caelis Courier",
            "archetype": "Courier",
            "role": "Rival",
            "skill_tag": "Combat",
            "one_line_summary": "Swift messenger from the Cloud Kingdom who races the wind.",
            "baseline_trust": 0.22
        }
    ]


def test_generate_dynamic_npcs_success(mock_npc_response):
    """Test successful dynamic NPC generation"""
    with patch('purpose_agents.npc_seed.generate_dynamic_npcs') as mock_generate:
        mock_generate.return_value = mock_npc_response
        
        result = generate_dynamic_npcs(
            archetype="Hero",
            theme="redemption",
            ask="How do I find my way?",
            seek="I seek inner strength",
            knock="I knock on the door of destiny",
            count=6
        )
        
        assert len(result) == 6
        assert result[0]["id"] == "lyra_explorer"
        assert result[0]["full_name"] == "Lyra Explorer"
        assert result[0]["role"] == "Mentor"
        assert result[0]["skill_tag"] == "Survival"
        assert result[0]["baseline_trust"] == 0.35


def test_generate_dynamic_npcs_import_error():
    """Test fallback when NPC seed module is not available"""
    with patch('builtins.__import__', side_effect=ImportError("No module named 'purpose_agents.npc_seed'")):
        result = generate_dynamic_npcs(
            archetype="Hero",
            theme="redemption",
            ask="How do I find my way?",
            seek="I seek inner strength",
            knock="I knock on the door of destiny"
        )
        
        assert result == []


def test_generate_dynamic_npcs_exception_handling():
    """Test exception handling in dynamic NPC generation"""
    with patch('purpose_agents.npc_seed.generate_dynamic_npcs', side_effect=Exception("LLM API error")):
        result = generate_dynamic_npcs(
            archetype="Hero",
            theme="redemption",
            ask="How do I find my way?",
            seek="I seek inner strength",
            knock="I knock on the door of destiny"
        )
        
        assert result == []


def test_seed_dynamic_npcs_creates_npcs(db, mock_npc_response):
    """Test that seed_dynamic_npcs creates NPCs in database"""
    player_id = "test_player_dynamic"
    
    # Ensure no NPCs exist initially
    existing_npcs = get_state(player_id, db)
    assert len(existing_npcs) == 0
    
    # Call the function
    seed_dynamic_npcs(player_id, mock_npc_response, db)
    
    # Verify NPCs were created
    created_npcs = get_state(player_id, db)
    assert len(created_npcs) == 6
    
    # Check first NPC
    lyra = next(npc for npc in created_npcs if npc.name == "Lyra Explorer")
    assert lyra.trust == 0.35
    assert lyra.baseline_trust == 0.35
    assert lyra.summary == "Wise guide from the Crystal Forest who knows ancient paths."
    assert lyra.meta["role"] == "Mentor"
    assert lyra.meta["skill_tag"] == "Survival"
    assert lyra.meta["created_from_dynamic"] == True


def test_seed_dynamic_npcs_idempotent(db, mock_npc_response):
    """Test that seed_dynamic_npcs is idempotent - doesn't create duplicates"""
    player_id = "test_player_dynamic_idempotent"
    
    # Call the function twice
    seed_dynamic_npcs(player_id, mock_npc_response, db)
    seed_dynamic_npcs(player_id, mock_npc_response, db)
    
    # Verify only 6 NPCs were created (no duplicates)
    created_npcs = get_state(player_id, db)
    assert len(created_npcs) == 6


def test_seed_dynamic_npcs_handles_missing_fields(db):
    """Test that seed_dynamic_npcs handles missing optional fields gracefully"""
    player_id = "test_player_missing_fields"
    
    # NPC data with missing optional fields
    npc_data = [
        {
            "id": "minimal_npc",
            "full_name": "Minimal NPC",
            "archetype": "Warrior",
            "role": "Guardian",
            "skill_tag": "Combat",
            "one_line_summary": "Warrior from the Iron Fortress.",
            "baseline_trust": 0.30
            # Missing portrait_url, some meta fields
        }
    ]
    
    # Call the function
    seed_dynamic_npcs(player_id, npc_data, db)
    
    # Verify NPC was created with defaults
    created_npcs = get_state(player_id, db)
    assert len(created_npcs) == 1
    
    npc = created_npcs[0]
    assert npc.name == "Minimal NPC"
    assert npc.trust == 0.30
    assert npc.baseline_trust == 0.30
    assert npc.summary == "Warrior from the Iron Fortress."
    assert npc.portrait_url == ""  # Default empty string
    assert npc.meta["role"] == "Guardian"
    assert npc.meta["skill_tag"] == "Combat"


def test_seed_dynamic_npcs_trust_clamping(db):
    """Test that seed_dynamic_npcs clamps trust values to valid range"""
    player_id = "test_player_trust_clamping"
    
    # NPC data with out-of-range trust values
    npc_data = [
        {
            "id": "high_trust_npc",
            "full_name": "High Trust NPC",
            "archetype": "Hero",
            "role": "Mentor",
            "skill_tag": "Magic",
            "one_line_summary": "Hero from the Sacred Temple.",
            "baseline_trust": 0.8  # Above max
        },
        {
            "id": "low_trust_npc",
            "full_name": "Low Trust NPC",
            "archetype": "Villain",
            "role": "Rival",
            "skill_tag": "Combat",
            "one_line_summary": "Villain from the Dark Castle.",
            "baseline_trust": 0.1  # Below min
        }
    ]
    
    # Call the function
    seed_dynamic_npcs(player_id, npc_data, db)
    
    # Verify trust values were clamped
    created_npcs = get_state(player_id, db)
    assert len(created_npcs) == 2
    
    high_trust_npc = next(npc for npc in created_npcs if npc.name == "High Trust NPC")
    low_trust_npc = next(npc for npc in created_npcs if npc.name == "Low Trust NPC")
    
    assert high_trust_npc.trust == 0.45  # Clamped to max
    assert high_trust_npc.baseline_trust == 0.45
    assert low_trust_npc.trust == 0.20  # Clamped to min
    assert low_trust_npc.baseline_trust == 0.20


def test_seed_dynamic_npcs_skill_coverage(db, mock_npc_response):
    """Test that generated NPCs cover all required skills"""
    player_id = "test_player_skill_coverage"
    
    # Call the function
    seed_dynamic_npcs(player_id, mock_npc_response, db)
    
    # Verify all skills are covered
    created_npcs = get_state(player_id, db)
    skills = [npc.meta["skill_tag"] for npc in created_npcs]
    
    required_skills = ["Combat", "Social", "Tech", "Magic", "Survival"]
    covered_skills = set(skills)
    
    # Check that we have at least one of each required skill
    for skill in required_skills:
        assert skill in covered_skills, f"Missing skill: {skill}"


def test_seed_dynamic_npcs_role_uniqueness(db, mock_npc_response):
    """Test that generated NPCs have unique roles"""
    player_id = "test_player_role_uniqueness"
    
    # Call the function
    seed_dynamic_npcs(player_id, mock_npc_response, db)
    
    # Verify roles are unique
    created_npcs = get_state(player_id, db)
    roles = [npc.meta["role"] for npc in created_npcs]
    
    # Check for unique roles
    assert len(roles) == len(set(roles)), "Duplicate roles found"
    
    # Verify we have the expected roles
    expected_roles = ["Mentor", "Guardian", "Healer", "Trickster", "Wild-card", "Rival"]
    for role in expected_roles:
        assert role in roles, f"Missing role: {role}"


def test_seed_dynamic_npcs_world_hooks(db, mock_npc_response):
    """Test that generated NPCs include world hooks in summaries"""
    player_id = "test_player_world_hooks"
    
    # Call the function
    seed_dynamic_npcs(player_id, mock_npc_response, db)
    
    # Verify summaries contain world hooks
    created_npcs = get_state(player_id, db)
    world_hook_indicators = ['forest', 'tower', 'temple', 'guild', 'city', 'castle', 'fortress', 'kingdom', 'crystal', 'iron', 'sacred', 'shadow', 'floating', 'cloud']
    
    for npc in created_npcs:
        summary_lower = npc.summary.lower()
        has_world_hook = any(indicator in summary_lower for indicator in world_hook_indicators)
        assert has_world_hook, f"NPC {npc.name} missing world hook in summary: {npc.summary}" 