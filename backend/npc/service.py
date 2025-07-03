from .models import NPCState
from backend.db import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
import uuid

def get_state(player_id: str, db: Session) -> list[NPCState]:
    return db.query(NPCState).filter_by(player_id=player_id).all()

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
        npc = NPCState(id=npc_uuid, player_id=player_id, name="Companion", trust=0.0, meta={})
        db.add(npc)
        db.commit()
        db.refresh(npc)
    # Clamp trust
    npc.trust = min(max(npc.trust + delta, 0.0), 1.0)
    db.commit()
    db.refresh(npc)
    return npc 