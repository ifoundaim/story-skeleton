import pytest
import uuid
from backend.npc.profile_seed import ensure_npc_profile
from backend.npc.service import get_npc_by_id, get_state
from backend.npc.models import NPCState

def test_ensure_npc_profile_with_archetype(db):
    """Test that NPC profiles are created with archetype information"""
    player_id = "test_player_archetype"
    npc_id = str(uuid.uuid4())
    
    scene = {
        "npc_profile": {
            "id": npc_id,
            "name": "Lyra",
            "archetype": "Healer",
            "recruitable": True,
            "default_trust": 0.45
        }
    }
    
    ensure_npc_profile(scene, player_id)
    
    created_npc = get_npc_by_id(player_id, npc_id, db)
    assert created_npc.name == "Lyra"
    assert created_npc.trust == 0.45
    assert created_npc.meta.get("archetype") == "Healer"

def test_ensure_npc_profile_with_correct_trust(db):
    """Test that NPC profiles are created with correct trust values"""
    player_id = "test_player_trust"
    npc_id = str(uuid.uuid4())
    
    scene = {
        "npc_profile": {
            "id": npc_id,
            "name": "Orin",
            "default_trust": 0.7
        }
    }
    
    ensure_npc_profile(scene, player_id)
    
    created_npc = get_npc_by_id(player_id, npc_id, db)
    assert created_npc.trust == 0.7

def test_ensure_npc_profile_companion_terminology(db):
    """Test that fallback names use companion terminology"""
    player_id = "test_player_companion"
    npc_id = str(uuid.uuid4())
    
    scene = {
        "npcs_present": [npc_id]
    }
    
    ensure_npc_profile(scene, player_id)
    
    created_npc = get_npc_by_id(player_id, npc_id, db)
    assert created_npc.name == "Companion"

def test_ensure_npc_profile_mixed_sources_with_archetype(db):
    """Test that both npc_profile and npcs_present work with archetypes"""
    player_id = "test_player_mixed_archetype"
    npc_id_1 = str(uuid.uuid4())
    npc_id_2 = str(uuid.uuid4())
    
    scene = {
        "npc_profile": {
            "id": npc_id_1,
            "name": "Kael",
            "archetype": "Warrior",
            "default_trust": 0.6
        },
        "npcs_present": [npc_id_2]
    }
    
    ensure_npc_profile(scene, player_id)
    
    npc_1 = get_npc_by_id(player_id, npc_id_1, db)
    npc_2 = get_npc_by_id(player_id, npc_id_2, db)
    
    assert npc_1.meta.get("archetype") == "Warrior"
    assert npc_1.trust == 0.6
    assert npc_2.name == "Companion"

def test_ensure_npc_profile_idempotent_with_archetype(db):
    """Test that calling the helper multiple times doesn't affect archetype data"""
    player_id = "test_player_idempotent_archetype"
    npc_id = str(uuid.uuid4())
    
    scene = {
        "npc_profile": {
            "id": npc_id,
            "name": "Vera",
            "archetype": "Mage",
            "default_trust": 0.5
        }
    }
    
    # Call the helper twice
    ensure_npc_profile(scene, player_id)
    ensure_npc_profile(scene, player_id)
    
    # Verify only one NPC was created with correct archetype
    all_npcs = get_state(player_id, db)
    npc_count = len([npc for npc in all_npcs if str(npc.id) == npc_id])
    assert npc_count == 1
    
    created_npc = get_npc_by_id(player_id, npc_id, db)
    assert created_npc.meta.get("archetype") == "Mage" 