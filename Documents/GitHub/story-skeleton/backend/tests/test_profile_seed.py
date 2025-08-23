import pytest
import uuid
from backend.npc.profile_seed import ensure_npc_profile
from backend.npc.service import get_npc_by_id, get_state
from backend.npc.models import NPCState

def test_ensure_npc_profile_with_npc_profile_block(db):
    """Test that NPC profiles are created from explicit npc_profile blocks"""
    player_id = "test_player_1"
    npc_id = str(uuid.uuid4())
    
    scene = {
        "npc_profile": {
            "id": npc_id,
            "name": "Test NPC",
            "recruitable": True,
            "default_trust": 0.5
        }
    }
    
    # Ensure no NPC exists initially
    existing_npc = get_npc_by_id(player_id, npc_id, db)
    assert existing_npc is None
    
    # Call the helper
    ensure_npc_profile(scene, player_id)
    
    # Verify NPC was created
    created_npc = get_npc_by_id(player_id, npc_id, db)
    assert created_npc is not None
    assert created_npc.name == "Test NPC"
    assert created_npc.trust == 0.0  # Default trust from create_default_npc
    assert created_npc.active_companion == False

def test_ensure_npc_profile_with_npcs_present_fallback(db):
    """Test that NPC profiles are created from npcs_present array"""
    player_id = "test_player_2"
    npc_id = str(uuid.uuid4())
    
    scene = {
        "npcs_present": [npc_id]
    }
    
    # Ensure no NPC exists initially
    existing_npc = get_npc_by_id(player_id, npc_id, db)
    assert existing_npc is None
    
    # Call the helper
    ensure_npc_profile(scene, player_id)
    
    # Verify NPC was created with default name
    created_npc = get_npc_by_id(player_id, npc_id, db)
    assert created_npc is not None
    assert created_npc.name == npc_id.title()  # Default name from title()
    assert created_npc.trust == 0.0

def test_ensure_npc_profile_with_multiple_npcs(db):
    """Test that multiple NPCs are handled correctly"""
    player_id = "test_player_3"
    npc_id_1 = str(uuid.uuid4())
    npc_id_2 = str(uuid.uuid4())
    
    scene = {
        "npc_profile": [
            {
                "id": npc_id_1,
                "name": "First NPC",
                "recruitable": True,
                "default_trust": 0.3
            },
            {
                "id": npc_id_2,
                "name": "Second NPC",
                "recruitable": False,
                "default_trust": 0.7
            }
        ]
    }
    
    # Call the helper
    ensure_npc_profile(scene, player_id)
    
    # Verify both NPCs were created
    npc_1 = get_npc_by_id(player_id, npc_id_1, db)
    npc_2 = get_npc_by_id(player_id, npc_id_2, db)
    
    assert npc_1 is not None
    assert npc_1.name == "First NPC"
    assert npc_2 is not None
    assert npc_2.name == "Second NPC"

def test_ensure_npc_profile_idempotent(db):
    """Test that calling the helper multiple times doesn't create duplicates"""
    player_id = "test_player_4"
    npc_id = str(uuid.uuid4())
    
    scene = {
        "npcs_present": [npc_id]
    }
    
    # Call the helper twice
    ensure_npc_profile(scene, player_id)
    ensure_npc_profile(scene, player_id)
    
    # Verify only one NPC was created
    all_npcs = get_state(player_id, db)
    npc_count = len([npc for npc in all_npcs if str(npc.id) == npc_id])
    assert npc_count == 1

def test_ensure_npc_profile_empty_scene(db):
    """Test that empty scenes don't cause errors"""
    player_id = "test_player_5"
    
    scene = {}
    
    # Should not raise any exceptions
    ensure_npc_profile(scene, player_id)
    
    # Verify no NPCs were created
    all_npcs = get_state(player_id, db)
    assert len(all_npcs) == 0

def test_ensure_npc_profile_mixed_sources(db):
    """Test that both npc_profile and npcs_present work together"""
    player_id = "test_player_6"
    npc_id_1 = str(uuid.uuid4())
    npc_id_2 = str(uuid.uuid4())
    
    scene = {
        "npc_profile": {
            "id": npc_id_1,
            "name": "Profile NPC"
        },
        "npcs_present": [npc_id_2]
    }
    
    # Call the helper
    ensure_npc_profile(scene, player_id)
    
    # Verify both NPCs were created
    npc_1 = get_npc_by_id(player_id, npc_id_1, db)
    npc_2 = get_npc_by_id(player_id, npc_id_2, db)
    
    assert npc_1 is not None
    assert npc_1.name == "Profile NPC"
    assert npc_2 is not None
    assert npc_2.name == npc_id_2.title()

def test_ensure_npc_profile_invalid_data(db):
    """Test that invalid data doesn't cause errors"""
    player_id = "test_player_7"
    
    scene = {
        "npc_profile": "not_a_dict",
        "npcs_present": ["not_a_uuid", 123, None]
    }
    
    # Should not raise any exceptions
    ensure_npc_profile(scene, player_id)
    
    # Verify no NPCs were created
    all_npcs = get_state(player_id, db)
    assert len(all_npcs) == 0 