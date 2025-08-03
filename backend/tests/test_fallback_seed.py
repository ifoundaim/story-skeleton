import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from backend.npc.profile_seed import get_seed_npcs, _load_fallback_npcs, seed_fallback_npcs
from backend.npc.service import get_npc_by_id, get_state
from backend.npc.models import NPCState
from backend.settings import Settings


@pytest.fixture
def mock_settings():
    """Mock settings with USE_FALLBACK_NPCS=True"""
    with patch('backend.npc.profile_seed.settings') as mock_settings:
        mock_settings.USE_FALLBACK_NPCS = True
        yield mock_settings


@pytest.fixture
def mock_settings_disabled():
    """Mock settings with USE_FALLBACK_NPCS=False"""
    with patch('backend.npc.profile_seed.settings') as mock_settings:
        mock_settings.USE_FALLBACK_NPCS = False
        yield mock_settings


@pytest.fixture
def temp_fallback_file():
    """Create a temporary fallback NPCs JSON file"""
    fallback_data = [
        {
            "id": "lyra_orinova",
            "full_name": "Lyra Orinova",
            "summary": "Resourceful sky-sailor who trades secrets for starlight maps.",
            "archetype": "Explorer",
            "baseline_trust": 0.40,
            "portrait_url": ""
        },
        {
            "id": "orin_kael",
            "full_name": "Orin Kael",
            "summary": "Veteran guardian driven by an oath to protect the innocent.",
            "archetype": "Guardian",
            "baseline_trust": 0.35,
            "portrait_url": ""
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(fallback_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


def test_get_seed_npcs_with_fallback_enabled(mock_settings):
    """Test that get_seed_npcs returns fallback data when flag is enabled"""
    with patch('backend.npc.profile_seed._load_fallback_npcs') as mock_load:
        mock_load.return_value = [{"id": "test_npc", "full_name": "Test NPC"}]
        result = get_seed_npcs()
        
        assert result == [{"id": "test_npc", "full_name": "Test NPC"}]
        mock_load.assert_called_once()


def test_get_seed_npcs_with_fallback_disabled(mock_settings_disabled):
    """Test that get_seed_npcs returns empty list when flag is disabled"""
    with patch('backend.npc.profile_seed.generate_dynamic_npcs') as mock_generate:
        mock_generate.return_value = []
        result = get_seed_npcs()
        
        assert result == []
        mock_generate.assert_called_once()


def test_load_fallback_npcs_success(temp_fallback_file):
    """Test successful loading of fallback NPCs from JSON file"""
    with patch('backend.npc.profile_seed.os.path.join') as mock_join:
        mock_join.return_value = temp_fallback_file
        result = _load_fallback_npcs()
        
        assert len(result) == 2
        assert result[0]["id"] == "lyra_orinova"
        assert result[0]["full_name"] == "Lyra Orinova"
        assert result[1]["id"] == "orin_kael"
        assert result[1]["full_name"] == "Orin Kael"


def test_load_fallback_npcs_file_not_found():
    """Test handling of missing fallback NPCs file"""
    with patch('backend.npc.profile_seed.os.path.join') as mock_join:
        mock_join.return_value = "/nonexistent/file.json"
        result = _load_fallback_npcs()
        
        assert result == []


def test_load_fallback_npcs_invalid_json():
    """Test handling of invalid JSON in fallback NPCs file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("invalid json content")
        temp_path = f.name
    
    try:
        with patch('backend.npc.profile_seed.os.path.join') as mock_join:
            mock_join.return_value = temp_path
            result = _load_fallback_npcs()
            
            assert result == []
    finally:
        os.unlink(temp_path)


def test_seed_fallback_npcs_creates_npcs(db, mock_settings):
    """Test that seed_fallback_npcs creates NPCs in database"""
    player_id = "test_player_fallback"
    
    # Mock the get_seed_npcs function to return test data
    test_npcs = [
        {
            "id": "lyra_orinova",
            "full_name": "Lyra Orinova",
            "summary": "Resourceful sky-sailor who trades secrets for starlight maps.",
            "archetype": "Explorer",
            "baseline_trust": 0.40,
            "portrait_url": ""
        }
    ]
    
    with patch('backend.npc.profile_seed.get_seed_npcs') as mock_get_seed:
        mock_get_seed.return_value = test_npcs
        
        # Ensure no NPCs exist initially
        existing_npcs = get_state(player_id, db)
        assert len(existing_npcs) == 0
        
        # Call the function
        seed_fallback_npcs(player_id, db)
        
        # Verify NPC was created
        created_npcs = get_state(player_id, db)
        assert len(created_npcs) == 1
        
        npc = created_npcs[0]
        assert npc.name == "Lyra Orinova"
        assert npc.trust == 0.40
        assert npc.meta["summary"] == "Resourceful sky-sailor who trades secrets for starlight maps."
        assert npc.meta["archetype"] == "Explorer"
        assert npc.meta["created_from_fallback"] == True


def test_seed_fallback_npcs_idempotent(db, mock_settings):
    """Test that seed_fallback_npcs is idempotent - doesn't create duplicates"""
    player_id = "test_player_idempotent"
    
    test_npcs = [
        {
            "id": "lyra_orinova",
            "full_name": "Lyra Orinova",
            "summary": "Resourceful sky-sailor who trades secrets for starlight maps.",
            "archetype": "Explorer",
            "baseline_trust": 0.40,
            "portrait_url": ""
        }
    ]
    
    with patch('backend.npc.profile_seed.get_seed_npcs') as mock_get_seed:
        mock_get_seed.return_value = test_npcs
        
        # Call the function twice
        seed_fallback_npcs(player_id, db)
        seed_fallback_npcs(player_id, db)
        
        # Verify only one NPC was created
        created_npcs = get_state(player_id, db)
        assert len(created_npcs) == 1
        
        npc = created_npcs[0]
        assert npc.name == "Lyra Orinova"


def test_seed_fallback_npcs_multiple_npcs(db, mock_settings):
    """Test that seed_fallback_npcs creates multiple NPCs"""
    player_id = "test_player_multiple"
    
    test_npcs = [
        {
            "id": "lyra_orinova",
            "full_name": "Lyra Orinova",
            "summary": "Resourceful sky-sailor who trades secrets for starlight maps.",
            "archetype": "Explorer",
            "baseline_trust": 0.40,
            "portrait_url": ""
        },
        {
            "id": "orin_kael",
            "full_name": "Orin Kael",
            "summary": "Veteran guardian driven by an oath to protect the innocent.",
            "archetype": "Guardian",
            "baseline_trust": 0.35,
            "portrait_url": ""
        }
    ]
    
    with patch('backend.npc.profile_seed.get_seed_npcs') as mock_get_seed:
        mock_get_seed.return_value = test_npcs
        
        # Call the function
        seed_fallback_npcs(player_id, db)
        
        # Verify both NPCs were created
        created_npcs = get_state(player_id, db)
        assert len(created_npcs) == 2
        
        # Check first NPC
        lyra = next(npc for npc in created_npcs if npc.name == "Lyra Orinova")
        assert lyra.trust == 0.40
        assert lyra.meta["archetype"] == "Explorer"
        
        # Check second NPC
        orin = next(npc for npc in created_npcs if npc.name == "Orin Kael")
        assert orin.trust == 0.35
        assert orin.meta["archetype"] == "Guardian" 