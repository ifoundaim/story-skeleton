from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from db import SessionLocal
from .models import NPCState
from .service import (
    get_state, 
    apply_trust, 
    apply_trust_to_multiple,
    get_trust_scores,
    ensure_default_npcs,
    get_npc_by_id
)

router = APIRouter()

class TrustUpdateRequest(BaseModel):
    player_id: str
    npc_id: str
    delta_trust: float

class MultipleTrustUpdateRequest(BaseModel):
    player_id: str
    trust_deltas: Dict[str, float]  # npc_id -> delta

class NPCDialogueRequest(BaseModel):
    player_id: str
    npc_ids: List[str]
    scene_context: Optional[str] = ""

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/{player_id}')
def get_npcs(player_id: str, db: Session = Depends(get_db)):
    """Get all NPCs for a player, ensuring default NPCs exist"""
    npcs = ensure_default_npcs(player_id, db)
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

@router.get('/{player_id}/trust-scores')
def get_player_trust_scores(player_id: str, db: Session = Depends(get_db)):
    """Get trust scores for all NPCs for a player"""
    trust_scores = get_trust_scores(player_id, db)
    return {'player_id': player_id, 'trust_scores': trust_scores}

@router.get('/{player_id}/npc/{npc_id}')
def get_single_npc(player_id: str, npc_id: str, db: Session = Depends(get_db)):
    """Get a specific NPC by ID"""
    npc = get_npc_by_id(player_id, npc_id, db)
    if not npc:
        raise HTTPException(404, f'NPC {npc_id} not found for player {player_id}')
    
    return {
        'id': str(npc.id),
        'player_id': npc.player_id,
        'name': npc.name,
        'trust': npc.trust,
        'last_seen': npc.last_seen,
        'meta': npc.meta,
    }

@router.post('/update')
def update_npc(request: TrustUpdateRequest, db: Session = Depends(get_db)):
    """Update trust for a single NPC"""
    npc = apply_trust(request.player_id, request.npc_id, request.delta_trust, db)
    return {
        'id': str(npc.id),
        'player_id': npc.player_id,
        'name': npc.name,
        'trust': npc.trust,
        'last_seen': npc.last_seen,
        'meta': npc.meta,
    }

@router.post('/update-multiple')
def update_multiple_npcs(request: MultipleTrustUpdateRequest, db: Session = Depends(get_db)):
    """Update trust for multiple NPCs at once"""
    updated_npcs = apply_trust_to_multiple(request.player_id, request.trust_deltas, db)
    return {
        'player_id': request.player_id,
        'updated_npcs': [
            {
                'id': str(npc.id),
                'player_id': npc.player_id,
                'name': npc.name,
                'trust': npc.trust,
                'last_seen': npc.last_seen,
                'meta': npc.meta,
            }
            for npc in updated_npcs
        ]
    }

@router.post('/dialogue')
def generate_group_dialogue(request: NPCDialogueRequest, db: Session = Depends(get_db)):
    """Generate group dialogue for multiple NPCs"""
    try:
        from codex.npc.npc_group_dialogue import generate_group_dialogue_with_context
        
        # Ensure NPCs exist for the player
        ensure_default_npcs(request.player_id, db)
        
        # Generate dialogue
        dialogue_entries = generate_group_dialogue_with_context(
            request.npc_ids, 
            request.player_id, 
            request.scene_context or ""
        )
        
        return {
            'player_id': request.player_id,
            'npc_ids': request.npc_ids,
            'scene_context': request.scene_context,
            'dialogue': dialogue_entries
        }
    except Exception as e:
        raise HTTPException(500, f'Failed to generate dialogue: {str(e)}') 