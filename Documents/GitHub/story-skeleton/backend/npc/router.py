from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from db import SessionLocal
from .models import NPCState, NPC
from .service import (
    get_state, 
    apply_trust, 
    apply_trust_to_multiple,
    get_trust_scores,
    ensure_default_npcs,
    get_npc_by_id,
    ensure_npc_profile,
    apply_trust_new
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

class NPCProfileRequest(BaseModel):
    npc_id: str
    full_name: str
    baseline_trust: float = 0.0

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/{player_id}')
def get_npcs(player_id: str, db: Session = Depends(get_db)):
    """Get all NPCs for a player, ensuring default NPCs exist, and normalize names."""
    npcs = ensure_default_npcs(player_id, db)
    normalized = []
    import uuid as _uuid
    for npc in npcs:
        display_name = npc.name
        try:
            # If the name looks like a UUID, map to a friendly default
            if display_name and display_name.replace('-', '').isalnum():
                try:
                    is_uuid = str(_uuid.UUID(display_name))
                    # Map stable defaults based on id
                    from .profile_seed import _friendly_name_for_uuid as _fname
                    display_name = _fname(_uuid.UUID(str(npc.id)))
                except Exception:
                    pass
        except Exception:
            pass
        normalized.append({
            'id': str(npc.id),
            'player_id': npc.player_id,
            'name': display_name,
            'trust': npc.trust,
            'last_seen': npc.last_seen,
            'meta': npc.meta,
        })
    return normalized

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

@router.post('/{player_id}/repair-names')
def repair_npc_names(player_id: str, db: Session = Depends(get_db)):
    """Upgrade legacy NPCState names that look like raw UUIDs to friendly names.
    Returns updated NPCs for verification.
    """
    from .profile_seed import _friendly_name_for_uuid
    import uuid as _uuid
    updated = []
    for npc in get_state(player_id, db):
        name = npc.name or ""
        looks_like_uuid = False
        try:
            looks_like_uuid = str(_uuid.UUID(name)).lower() == name.lower()
        except Exception:
            looks_like_uuid = False
        if looks_like_uuid:
            friendly = _friendly_name_for_uuid(npc.id)
            npc.name = friendly
            updated.append(npc)
    if updated:
        db.commit()
        for npc in updated:
            db.refresh(npc)
    return [
        {
            'id': str(npc.id),
            'player_id': npc.player_id,
            'name': npc.name,
            'trust': npc.trust,
            'last_seen': npc.last_seen,
            'meta': npc.meta,
        }
        for npc in get_state(player_id, db)
    ]

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

# New endpoints for the NPC table (Sprint NPC01 requirements)

@router.post('/profile')
def create_npc_profile(request: NPCProfileRequest, db: Session = Depends(get_db)):
    """Create an idempotent NPC profile in the new npc table"""
    try:
        npc = ensure_npc_profile(request.npc_id, request.full_name, request.baseline_trust, db)
        return {
            'id': str(npc.id),
            'full_name': npc.full_name,
            'baseline_trust': npc.baseline_trust,
            'trust': npc.trust,
        }
    except Exception as e:
        raise HTTPException(500, f'Failed to create NPC profile: {str(e)}')

@router.get('/profile/{npc_id}')
def get_npc_profile(npc_id: str, db: Session = Depends(get_db)):
    """Get an NPC profile from the new npc table"""
    try:
        import uuid
        if isinstance(npc_id, str):
            try:
                npc_uuid = uuid.UUID(npc_id)
            except ValueError:
                npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, npc_id)
        else:
            npc_uuid = npc_id
        
        npc = db.query(NPC).filter_by(id=npc_uuid).first()
        if not npc:
            raise HTTPException(404, f'NPC profile {npc_id} not found')
        
        return {
            'id': str(npc.id),
            'full_name': npc.full_name,
            'baseline_trust': npc.baseline_trust,
            'trust': npc.trust,
        }
    except Exception as e:
        raise HTTPException(500, f'Failed to get NPC profile: {str(e)}')

@router.post('/profile/{npc_id}/trust')
def update_npc_trust(npc_id: str, delta: float, db: Session = Depends(get_db)):
    """Update trust for an NPC in the new npc table"""
    try:
        npc = apply_trust_new(None, npc_id, delta, db)
        return {
            'id': str(npc.id),
            'full_name': npc.full_name,
            'baseline_trust': npc.baseline_trust,
            'trust': npc.trust,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f'Failed to update NPC trust: {str(e)}')

@router.get('/profiles')
def get_all_npc_profiles(db: Session = Depends(get_db)):
    """Get all NPC profiles from the new npc table"""
    try:
        npcs = db.query(NPC).all()
        return [
            {
                'id': str(npc.id),
                'full_name': npc.full_name,
                'baseline_trust': npc.baseline_trust,
                'trust': npc.trust,
            }
            for npc in npcs
        ]
    except Exception as e:
        raise HTTPException(500, f'Failed to get NPC profiles: {str(e)}') 