from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .models import NPCState
from .service import get_state, apply_trust
from backend.db import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/{player_id}')
def get_npcs(player_id: str, db: Session = Depends(get_db)):
    npcs = get_state(player_id, db)
    return [
        {
            'id': str(npc.id),
            'player_id': npc.player_id,
            'name': npc.name,
            'trust': npc.trust,
            'last_seen': npc.last_seen,
            'meta': npc.meta,
        }
        for npc in npcs
    ]

@router.post('/update')
def update_npc(payload: dict, db: Session = Depends(get_db)):
    player_id = payload.get('player_id')
    npc_id = payload.get('npc_id')
    delta = payload.get('delta_trust', 0.0)
    if not player_id or not npc_id:
        raise HTTPException(400, 'Missing player_id or npc_id')
    npc = apply_trust(player_id, npc_id, float(delta), db)
    return {
        'id': str(npc.id),
        'player_id': npc.player_id,
        'name': npc.name,
        'trust': npc.trust,
        'last_seen': npc.last_seen,
        'meta': npc.meta,
    } 