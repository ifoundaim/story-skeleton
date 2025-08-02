from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict
from pydantic import BaseModel
from .service import get_soulmap_dict, apply_delta
from .db import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()

class SoulMapUpdateRequest(BaseModel):
    player_id: str
    delta: Dict[str, float]

@router.get('/soulmap/player/{player_id}')
def get_soulmap(player_id: str, db: Session = Depends(get_db)):
    """Get soulmap for a player as trait dictionary."""
    try:
        soulmap_dict = get_soulmap_dict(db, player_id)
        return {
            'player_id': player_id,
            'traits': soulmap_dict,
            'vector_size': 64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get soulmap: {str(e)}")

@router.patch('/soulmap/update')
def update_soulmap(request: SoulMapUpdateRequest, db: Session = Depends(get_db)):
    """Update soulmap with delta values."""
    try:
        soulmap = apply_delta(db, request.player_id, request.delta)
        updated_dict = get_soulmap_dict(db, request.player_id)
        
        return {
            'player_id': request.player_id,
            'traits': updated_dict,
            'vector_size': 64,
            'message': 'Soulmap updated successfully'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update soulmap: {str(e)}")

@router.get('/soulmap/health')
def health_check():
    """Health check endpoint."""
    return {'status': 'healthy', 'service': 'soulmap-v2'} 