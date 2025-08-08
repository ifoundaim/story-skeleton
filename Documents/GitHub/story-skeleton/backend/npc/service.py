from .models import NPCState, NPC
from .profile_seed import _friendly_name_for_uuid
from db import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from typing import Dict, List, Optional
import uuid
from sqlalchemy import func

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
        try:
            npc_uuid = uuid.UUID(npc_id)
        except ValueError:
            # If not a valid UUID, generate one based on the string
            npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:{npc_id}")
    else:
        npc_uuid = npc_id
    
    # Check if NPC already exists to avoid duplicate key violations
    existing_npc = db.query(NPCState).filter_by(player_id=player_id, id=npc_uuid).first()
    if existing_npc:
        # If existing name is missing or looks like a raw UUID, upgrade to a friendly deterministic name
        try:
            should_upgrade = False
            if not existing_npc.name:
                should_upgrade = True
            else:
                looks_like_uuid = False
                try:
                    looks_like_uuid = str(uuid.UUID(existing_npc.name)) == str(existing_npc.name).lower()
                except Exception:
                    looks_like_uuid = False
                should_upgrade = should_upgrade or looks_like_uuid
            if should_upgrade:
                friendly = name or _friendly_name_for_uuid(npc_uuid)
                existing_npc.name = friendly
                db.commit()
                db.refresh(existing_npc)
        except Exception:
            pass
        return existing_npc
    
    friendly_name = name or _friendly_name_for_uuid(npc_uuid)
    npc = NPCState(
        id=npc_uuid, 
        player_id=player_id, 
        name=friendly_name,
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
        # Map UUIDs to NPC names based on the story generation logic
        lyra_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:lyra"))
        orin_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:orin"))
        companion_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:companion"))
        sage_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:sage"))
        warrior_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:warrior"))
        
        npc_uuid_str = str(npc_uuid)
        if npc_uuid_str == lyra_uuid:
            npc_name = "Lyra"
        elif npc_uuid_str == orin_uuid:
            npc_name = "Orin"
        elif npc_uuid_str == companion_uuid:
            npc_name = "Companion"
        elif npc_uuid_str == sage_uuid:
            npc_name = "Sage"
        elif npc_uuid_str == warrior_uuid:
            npc_name = "Warrior"
        else:
            npc_name = "Companion"  # Default fallback
        
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
    """Ensure player has default NPCs (Lyra and Orin) using global stable UUIDs.
    IDs match story assignment schema (uuid5(NAMESPACE_OID, "default:<name>")).
    """
    existing_npcs = get_state(player_id, db)
    existing_ids = {str(npc.id) for npc in existing_npcs}

    default_specs = [
        ("lyra", "Lyra"),
        ("orin", "Orin"),
    ]

    created_npcs: List[NPCState] = []
    for key, full_name in default_specs:
        stable_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"default:{key}")
        if str(stable_uuid) not in existing_ids:
            npc = create_default_npc(player_id, str(stable_uuid), full_name, db)
            created_npcs.append(npc)

    return get_state(player_id, db)

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

def get_npc_states(player_id: str, db: Session = None) -> Dict[str, NPCState]:
    """
    Get all NPC states for a player
    
    Args:
        player_id: Player identifier
        db: Database session (optional)
        
    Returns:
        Dictionary mapping NPC IDs to NPCState objects
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        npc_states = db.query(NPCState).filter_by(player_id=player_id).all()
        return {str(npc.id): npc for npc in npc_states}
    finally:
        if should_close:
            db.close()

def onboard_npc(player_id: str, npc_id: str, db: Session) -> NPCState:
    """
    Onboard an NPC as a companion for the player
    
    Args:
        player_id: Player identifier
        npc_id: NPC identifier (UUID string)
        db: Database session
        
    Returns:
        Updated NPCState with companion status
    """
    # Get or create NPC
    npc = get_npc_by_id(player_id, npc_id, db)
    if not npc:
        # Create new NPC with default name
        npc_name = f"Companion-{npc_id[:8]}"
        npc = create_default_npc(player_id, npc_id, npc_name, db)
    
    # Mark as companion
    npc.meta["is_companion"] = True
    npc.meta["onboarded_at"] = db.query(func.now()).scalar().isoformat()
    
    # Boost trust slightly for successful recruitment
    npc.trust = min(npc.trust + 0.05, 1.0)
    
    db.commit()
    db.refresh(npc)
    
    return npc 