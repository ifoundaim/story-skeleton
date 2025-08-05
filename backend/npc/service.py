from .models import NPCState, NPC
from db import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from typing import Dict, List, Optional
import uuid

def get_state(player_id: str, db: Session) -> list[NPCState]:
    return db.query(NPCState).filter_by(player_id=player_id).all()

def get_npc_by_id(player_id: str, npc_id: str, db: Session) -> Optional[NPCState]:
    """Get a specific NPC by ID for a player"""
    try:
        if isinstance(npc_id, str):
            npc_uuid = uuid.UUID(npc_id)
        else:
            npc_uuid = npc_id
        return db.query(NPCState).filter_by(player_id=player_id, id=npc_uuid).one()
    except (NoResultFound, ValueError):
        return None

def get_trust_scores(player_id: str, db: Session) -> Dict[str, float]:
    """Get trust scores for all NPCs for a player"""
    npcs = get_state(player_id, db)
    return {str(npc.id): npc.trust for npc in npcs}

def create_default_npc(player_id: str, npc_id: str, name: str, db: Session) -> NPCState:
    """Create a new NPC with default values"""
    if isinstance(npc_id, str):
        npc_uuid = uuid.UUID(npc_id)
    else:
        npc_uuid = npc_id
    
    npc = NPCState(
        id=npc_uuid, 
        player_id=player_id, 
        name=name, 
        trust=0.0, 
        meta={"personality": "balanced", "created": True}
    )
    db.add(npc)
    db.commit()
    db.refresh(npc)
    return npc

def apply_trust(player_id: str, npc_id: str, delta: float, db: Session) -> NPCState:
    # Ensure npc_id is a UUID object
    if isinstance(npc_id, str):
        npc_uuid = uuid.UUID(npc_id)
    else:
        npc_uuid = npc_id
    try:
        npc = db.query(NPCState).filter_by(player_id=player_id, id=npc_uuid).one()
    except NoResultFound:
        # Create new NPC with default trust 0.0
        # Use more descriptive names based on UUID
        default_names = {
            "npc_lyra": "Lyra",
            "npc_orin": "Orin",
            "companion": "Companion"
        }
        npc_name = default_names.get(npc_id, "Companion")
        npc = create_default_npc(player_id, npc_uuid, npc_name, db)
    
    # Clamp trust
    npc.trust = min(max(npc.trust + delta, 0.0), 1.0)
    db.commit()
    db.refresh(npc)
    return npc

def apply_trust_to_multiple(player_id: str, trust_deltas: Dict[str, float], db: Session) -> List[NPCState]:
    """Apply trust deltas to multiple NPCs at once"""
    updated_npcs = []
    for npc_id, delta in trust_deltas.items():
        if delta != 0.0:  # Only update NPCs with non-zero deltas
            updated_npc = apply_trust(player_id, npc_id, delta, db)
            updated_npcs.append(updated_npc)
    return updated_npcs

def ensure_default_npcs(player_id: str, db: Session) -> List[NPCState]:
    """Ensure player has default NPCs (Lyra and Orin)"""
    existing_npcs = get_state(player_id, db)
    existing_ids = {str(npc.id) for npc in existing_npcs}
    
    default_npcs = [
        ("lyra", "Lyra"),
        ("orin", "Orin")
    ]
    
    created_npcs = []
    for npc_id, name in default_npcs:
        if npc_id not in existing_ids:
            # Generate a consistent UUID for default NPCs
            npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:{npc_id}")
            npc = create_default_npc(player_id, str(npc_uuid), name, db)
            created_npcs.append(npc)
    
    return existing_npcs + created_npcs

# New functions for the NPC table (Sprint NPC01 requirements)

def ensure_npc_profile(npc_id: str, full_name: str, baseline_trust: float = 0.0, db: Session = None) -> NPC:
    """
    Creates idempotent NPC entries in the npc table.
    If NPC already exists, returns existing NPC without modification.
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        # Convert npc_id to UUID if it's a string
        if isinstance(npc_id, str):
            try:
                npc_uuid = uuid.UUID(npc_id)
            except ValueError:
                # If not a valid UUID, generate one based on the string
                npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, npc_id)
        else:
            npc_uuid = npc_id
        
        # Check if NPC already exists
        existing_npc = db.query(NPC).filter_by(id=npc_uuid).first()
        if existing_npc:
            return existing_npc
        
        # Create new NPC
        npc = NPC(
            id=npc_uuid,
            full_name=full_name,
            baseline_trust=baseline_trust,
            trust=baseline_trust  # Initialize trust to baseline_trust
        )
        db.add(npc)
        db.commit()
        db.refresh(npc)
        return npc
    
    finally:
        if should_close:
            db.close()

def apply_trust_new(player_id: str, npc_id: str, delta: float, db: Session = None) -> NPC:
    """
    Increments or decrements NPC trust based on choices.
    This function works with the new NPC table.
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        # Convert npc_id to UUID if it's a string
        if isinstance(npc_id, str):
            try:
                npc_uuid = uuid.UUID(npc_id)
            except ValueError:
                # If not a valid UUID, generate one based on the string
                npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, npc_id)
        else:
            npc_uuid = npc_id
        
        # Get NPC from the new table
        npc = db.query(NPC).filter_by(id=npc_uuid).first()
        if not npc:
            raise ValueError(f"NPC with id {npc_id} not found")
        
        # Apply trust delta and clamp to 0.0-1.0 range
        npc.trust = min(max(npc.trust + delta, 0.0), 1.0)
        db.commit()
        db.refresh(npc)
        return npc
    
    finally:
        if should_close:
            db.close()

def get_companions(player_id: str, db: Session) -> List[NPCState]:
    """Get active companions for a player (legacy function for backward compatibility)"""
    return get_state(player_id, db) 