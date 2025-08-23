import pytest
import numpy as np
from sqlalchemy.orm import Session
from backend.soulmap.service import get_or_create, apply_delta, get_soulmap_dict
from backend.soulmap.mapping import SoulTrait, VECTOR_SIZE, dict_to_vec, vec_to_dict
from backend.db import SessionLocal

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_player_id():
    return "test_player_123"

def test_get_or_create_new_player(db: Session, test_player_id: str):
    """Test getting soulmap for a new player creates zero vector."""
    soulmap = get_or_create(db, test_player_id)
    
    assert soulmap.player_id == test_player_id
    assert len(list(soulmap.vec)) == 64
    
    # Check that all values are zero
    for value in soulmap.vec:
        assert value == 0.0

def test_apply_delta(db: Session, test_player_id: str):
    """Test applying delta to soulmap."""
    # Apply a delta
    delta = {
        "COURAGE": 0.5,
        "COMPASSION": -0.3,
        "WISDOM": 0.2
    }
    
    soulmap = apply_delta(db, test_player_id, delta)
    
    # Get the soulmap as dictionary
    soulmap_dict = get_soulmap_dict(db, test_player_id)
    
    # Check that the traits were updated correctly (using approximate equality for numpy floats)
    assert np.isclose(soulmap_dict["COURAGE"], 0.5, atol=1e-6)
    assert np.isclose(soulmap_dict["COMPASSION"], -0.3, atol=1e-6)
    assert np.isclose(soulmap_dict["WISDOM"], 0.2, atol=1e-6)
    
    # Check that other traits remain zero
    assert np.isclose(soulmap_dict["FEAR"], 0.0, atol=1e-6)
    assert np.isclose(soulmap_dict["HERO"], 0.0, atol=1e-6)

def test_apply_delta_clipping(db: Session, test_player_id: str):
    """Test that values are clipped to -1...+1 range."""
    # Try to set values outside the valid range
    delta = {
        "COURAGE": 2.0,  # Should be clipped to 1.0
        "FEAR": -1.5,    # Should be clipped to -1.0
        "WISDOM": 0.5    # Should remain 0.5
    }
    
    apply_delta(db, test_player_id, delta)
    soulmap_dict = get_soulmap_dict(db, test_player_id)
    
    assert np.isclose(soulmap_dict["COURAGE"], 1.0, atol=1e-6)
    assert np.isclose(soulmap_dict["FEAR"], -1.0, atol=1e-6)
    assert np.isclose(soulmap_dict["WISDOM"], 0.5, atol=1e-6)

def test_apply_delta_accumulation(db: Session, test_player_id: str):
    """Test that multiple updates accumulate correctly."""
    # First update
    delta1 = {"COURAGE": 0.3, "COMPASSION": 0.2}
    apply_delta(db, test_player_id, delta1)
    
    # Second update
    delta2 = {"COURAGE": 0.4, "WISDOM": 0.1}
    apply_delta(db, test_player_id, delta2)
    
    soulmap_dict = get_soulmap_dict(db, test_player_id)
    
    # Check accumulation
    assert np.isclose(soulmap_dict["COURAGE"], 0.7, atol=1e-6)  # 0.3 + 0.4
    assert np.isclose(soulmap_dict["COMPASSION"], 0.2, atol=1e-6)  # Only from first update
    assert np.isclose(soulmap_dict["WISDOM"], 0.1, atol=1e-6)  # Only from second update

def test_mapping_functions():
    """Test the mapping utility functions."""
    # Test dict_to_vec
    trait_dict = {"COURAGE": 0.5, "COMPASSION": -0.3}
    vector = dict_to_vec(trait_dict)
    
    assert len(vector) == 64
    assert vector[SoulTrait.COURAGE.value] == 0.5
    assert vector[SoulTrait.COMPASSION.value] == -0.3
    assert vector[SoulTrait.WISDOM.value] == 0.0  # Not in dict
    
    # Test vec_to_dict
    result_dict = vec_to_dict(vector)
    assert result_dict["COURAGE"] == 0.5
    assert result_dict["COMPASSION"] == -0.3
    assert result_dict["WISDOM"] == 0.0

def test_soul_trait_enum():
    """Test that all 64 traits are defined."""
    assert len(SoulTrait) == 64
    assert VECTOR_SIZE == 64
    
    # Check that all values are unique and in range
    values = [trait.value for trait in SoulTrait]
    assert len(set(values)) == 64  # All unique
    assert min(values) == 0
    assert max(values) == 63 