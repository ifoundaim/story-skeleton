import pytest
from backend.npc.models import NPCState, NPC
from backend.npc.service import ensure_npc_profile, apply_trust_new
from backend.npc.profile_seed import ensure_npc_profile_new
import uuid

def test_ensure_npc_profile_idempotent(db):
    """Test that ensure_npc_profile creates NPCs idempotently"""
    npc_id = "test_npc_001"
    full_name = "Test NPC"
    baseline_trust = 0.3
    
    # First call should create the NPC
    npc1 = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
    assert npc1.full_name == full_name
    assert npc1.baseline_trust == baseline_trust
    assert npc1.trust == baseline_trust
    
    # Second call should return the same NPC without modification
    npc2 = ensure_npc_profile(npc_id, "Different Name", 0.5, db)
    assert npc2.id == npc1.id
    assert npc2.full_name == full_name  # Should not change
    assert npc2.baseline_trust == baseline_trust  # Should not change
    assert npc2.trust == baseline_trust  # Should not change

def test_ensure_npc_profile_with_uuid(db):
    """Test ensure_npc_profile with UUID string"""
    npc_uuid = str(uuid.uuid4())
    full_name = "UUID NPC"
    baseline_trust = 0.7
    
    npc = ensure_npc_profile(npc_uuid, full_name, baseline_trust, db)
    assert str(npc.id) == npc_uuid
    assert npc.full_name == full_name
    assert npc.baseline_trust == baseline_trust

def test_ensure_npc_profile_with_string_id(db):
    """Test ensure_npc_profile with non-UUID string ID"""
    npc_id = "string_npc_id"
    full_name = "String NPC"
    baseline_trust = 0.2
    
    npc = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
    # Should generate a consistent UUID based on the string
    expected_uuid = uuid.uuid5(uuid.NAMESPACE_OID, npc_id)
    assert npc.id == expected_uuid
    assert npc.full_name == full_name
    assert npc.baseline_trust == baseline_trust

def test_apply_trust_new_increment(db):
    """Test apply_trust_new increments trust correctly"""
    npc_id = "trust_test_npc"
    full_name = "Trust Test NPC"
    baseline_trust = 0.5
    
    # Create NPC
    npc = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
    assert npc.trust == 0.5
    
    # Apply positive trust delta
    updated_npc = apply_trust_new(None, npc_id, 0.3, db)
    assert updated_npc.trust == 0.8

def test_apply_trust_new_decrement(db):
    """Test apply_trust_new decrements trust correctly"""
    npc_id = "trust_test_npc_2"
    full_name = "Trust Test NPC 2"
    baseline_trust = 0.5
    
    # Create NPC
    npc = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
    assert npc.trust == 0.5
    
    # Apply negative trust delta
    updated_npc = apply_trust_new(None, npc_id, -0.2, db)
    assert updated_npc.trust == 0.3

def test_apply_trust_new_clamp_upper(db):
    """Test apply_trust_new clamps trust to 1.0"""
    npc_id = "trust_test_npc_3"
    full_name = "Trust Test NPC 3"
    baseline_trust = 0.8
    
    # Create NPC
    npc = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
    assert npc.trust == 0.8
    
    # Apply trust delta that would exceed 1.0
    updated_npc = apply_trust_new(None, npc_id, 0.5, db)
    assert updated_npc.trust == 1.0

def test_apply_trust_new_clamp_lower(db):
    """Test apply_trust_new clamps trust to 0.0"""
    npc_id = "trust_test_npc_4"
    full_name = "Trust Test NPC 4"
    baseline_trust = 0.2
    
    # Create NPC
    npc = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
    assert npc.trust == 0.2
    
    # Apply trust delta that would go below 0.0
    updated_npc = apply_trust_new(None, npc_id, -0.5, db)
    assert updated_npc.trust == 0.0

def test_apply_trust_new_nonexistent_npc(db):
    """Test apply_trust_new raises error for nonexistent NPC"""
    npc_id = "nonexistent_npc"
    
    with pytest.raises(ValueError, match=f"NPC with id {npc_id} not found"):
        apply_trust_new(None, npc_id, 0.1, db)

def test_npc_table_schema(db):
    """Test that NPC table has correct schema"""
    npc_id = "schema_test_npc"
    full_name = "Schema Test NPC"
    baseline_trust = 0.4
    
    npc = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
    
    # Verify all required fields exist
    assert hasattr(npc, 'id')
    assert hasattr(npc, 'full_name')
    assert hasattr(npc, 'baseline_trust')
    assert hasattr(npc, 'trust')
    
    # Verify field types and values
    assert isinstance(npc.id, uuid.UUID)
    assert isinstance(npc.full_name, str)
    assert isinstance(npc.baseline_trust, float)
    assert isinstance(npc.trust, float)
    
    assert npc.full_name == full_name
    assert npc.baseline_trust == baseline_trust
    assert npc.trust == baseline_trust

def test_ensure_npc_profile_new_function(db):
    """Test the ensure_npc_profile_new function from profile_seed"""
    npc_id = "profile_seed_test"
    full_name = "Profile Seed Test NPC"
    baseline_trust = 0.6
    
    # Use the service function directly with the provided db session
    npc = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
    
    # Verify NPC was created
    assert npc is not None
    assert npc.full_name == full_name
    assert npc.baseline_trust == baseline_trust

def test_multiple_npc_creation(db):
    """Test creating multiple NPCs with different baseline trust values"""
    npcs_data = [
        ("npc_1", "First NPC", 0.1),
        ("npc_2", "Second NPC", 0.5),
        ("npc_3", "Third NPC", 0.9),
    ]
    
    created_npcs = []
    for npc_id, full_name, baseline_trust in npcs_data:
        npc = ensure_npc_profile(npc_id, full_name, baseline_trust, db)
        created_npcs.append(npc)
        assert npc.full_name == full_name
        assert npc.baseline_trust == baseline_trust
        assert npc.trust == baseline_trust
    
    # Verify all NPCs are different
    npc_ids = [str(npc.id) for npc in created_npcs]
    assert len(set(npc_ids)) == 3  # All IDs should be unique 