from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from .db import SoulMap, SessionLocal
from .mapping import VECTOR_SIZE, dict_to_vec, vec_to_dict, clip_vector, add_vectors

def get_or_create(db: Session, player_id: str) -> SoulMap:
    """Get existing soulmap or create new one with zero vector."""
    soulmap = db.query(SoulMap).filter_by(player_id=player_id).first()
    
    if not soulmap:
        # Create new soulmap with zero vector
        zero_vector = [0.0] * VECTOR_SIZE
        soulmap = SoulMap(player_id=player_id, vec=zero_vector)
        db.add(soulmap)
        db.commit()
        db.refresh(soulmap)
    
    return soulmap

def get_soulmap(db: Session, player_id: str) -> Optional[SoulMap]:
    """Get soulmap for player, return None if not found."""
    return db.query(SoulMap).filter_by(player_id=player_id).first()

def apply_delta(db: Session, player_id: str, delta_dict: Dict[str, float]) -> SoulMap:
    """Apply delta to player's soulmap, clipping values to -1...+1 range."""
    # Get or create soulmap
    soulmap = get_or_create(db, player_id)
    
    # Convert current vector to list
    current_vector = list(soulmap.vec)
    
    # Convert delta dict to vector
    delta_vector = dict_to_vec(delta_dict)
    
    # Add vectors and clip
    new_vector = add_vectors(current_vector, delta_vector)
    clipped_vector = clip_vector(new_vector, -1.0, 1.0)
    
    # Update soulmap
    soulmap.vec = clipped_vector
    db.commit()
    db.refresh(soulmap)
    
    return soulmap

def get_soulmap_dict(db: Session, player_id: str) -> Dict[str, float]:
    """Get soulmap as trait dictionary."""
    soulmap = get_or_create(db, player_id)
    return vec_to_dict(list(soulmap.vec))

def set_soulmap(db: Session, player_id: str, trait_dict: Dict[str, float]) -> SoulMap:
    """Set soulmap to specific trait values, clipping to -1...+1 range."""
    # Convert dict to vector and clip
    vector = dict_to_vec(trait_dict)
    clipped_vector = clip_vector(vector, -1.0, 1.0)
    
    # Get or create soulmap
    soulmap = get_or_create(db, player_id)
    
    # Update vector
    soulmap.vec = clipped_vector
    db.commit()
    db.refresh(soulmap)
    
    return soulmap 