from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel
import json
from .db import SessionLocal
from .service import get_soulmap_dict, apply_delta

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

@router.get("/soulmap/player/{player_id}")
def get_soulmap(player_id: str, db: Session = Depends(get_db)):
    """Get soulmap for a player from database."""
    try:
        traits = get_soulmap_dict(db, player_id)
        return {
            "player_id": player_id,
            "traits": traits,
            "vector_size": 64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get soulmap: {str(e)}")

@router.patch("/soulmap/update")
def update_soulmap(request: SoulMapUpdateRequest, db: Session = Depends(get_db)):
    """Update soulmap with delta values."""
    try:
        # Apply the delta to the soulmap
        updated_soulmap = apply_delta(db, request.player_id, request.delta)
        
        # Get the updated traits
        traits = get_soulmap_dict(db, request.player_id)
        
        return {
            "player_id": request.player_id,
            "traits": traits,
            "vector_size": 64,
            "message": "Soulmap updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update soulmap: {str(e)}")

@router.get("/soulmap/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "soulmap-v3-working"}

@router.get("/soulmap/test/{player_id}")
def test_soulmap(player_id: str, db: Session = Depends(get_db)):
    """Simple test endpoint."""
    try:
        traits = get_soulmap_dict(db, player_id)
        return {
            "player_id": player_id,
            "traits": traits,
            "vector_size": 64,
            "message": "Test data working"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get test soulmap: {str(e)}")
