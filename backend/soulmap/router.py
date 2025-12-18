import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import math

from backend.helix_client import get_helix_client
from backend.helix_sync import helix_sync_service

from .db import SessionLocal, SoulMap
from .mapping import VECTOR_SIZE
from .service import apply_delta, get_or_create, get_soulmap_dict

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()
logger = logging.getLogger(__name__)

class SoulMapUpdateRequest(BaseModel):
    player_id: str
    delta: Dict[str, float]


class NearestNeighborsRequest(BaseModel):
    player_id: Optional[str] = Field(default=None, description="Player to derive embedding from")
    embedding: Optional[List[float]] = Field(default=None, description="Explicit 64-D embedding")
    limit: int = Field(default=5, ge=1, le=25)


@router.get("/soulmap/player/{player_id}")
def get_soulmap(player_id: str, db: Session = Depends(get_db)):
    """Get soulmap for a player from database."""
    try:
        soulmap = get_or_create(db, player_id)
        traits = get_soulmap_dict(db, player_id)
        return {
            "player_id": player_id,
            "traits": traits,
            "vector_size": 64,
            "vector": [float(x) for x in list(soulmap.vec)],
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


@router.post("/soulmap/nearest-neighbors")
def nearest_neighbors(request: NearestNeighborsRequest, db: Session = Depends(get_db)):
    """Return Helix similarity results using either a stored or ad-hoc embedding."""
    embedding = request.embedding
    if embedding is None:
        if not request.player_id:
            raise HTTPException(status_code=400, detail="Provide embedding or player_id")
        soulmap = get_or_create(db, request.player_id)
        embedding = [float(x) for x in list(soulmap.vec)]
        # Ensure the caller's latest embedding is present in Helix
        helix_sync_service.sync_blocking(request.player_id, embedding)
    else:
        embedding = [float(x) for x in embedding]

    if len(embedding) != VECTOR_SIZE:
        raise HTTPException(status_code=400, detail=f"Embedding must contain {VECTOR_SIZE} values")

    client = get_helix_client()
    neighbors: List[Dict[str, Any]] = []

    if client.ready:
        neighbors = client.find_similar_souls(embedding, request.limit)
    else:
        logger.warning("Helix client unavailable; falling back to local similarity search")

    # Local fallback either when Helix is unavailable or returned nothing
    if not neighbors:
        neighbors = _local_neighbour_search(
            db=db,
            embedding=embedding,
            limit=request.limit,
            exclude_player_id=request.player_id,
        )

    return {"neighbors": neighbors}

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


def _local_neighbour_search(
    db: Session,
    embedding: List[float],
    limit: int,
    exclude_player_id: Optional[str],
) -> List[Dict[str, Any]]:
    """Fallback similarity search using soul maps stored in Postgres."""
    candidates: List[Dict[str, Any]] = []
    base_vector = [float(x) for x in embedding]
    base_norm = _vector_norm(base_vector)
    if base_norm == 0.0:
        # Avoid division by zero; we'll still surface neighbours, scores will be 0
        base_norm = 1.0

    query = db.query(SoulMap)
    if exclude_player_id:
        query = query.filter(SoulMap.player_id != exclude_player_id)

    for row in query:
        target_vector = [float(x) for x in list(row.vec)]
        score = _cosine_similarity(base_vector, target_vector, base_norm)
        candidates.append(
            {
                "user_id": row.player_id,
                "score": score,
                "raw": {"user_id": row.player_id, "score": score},
            }
        )

    sorted_candidates = sorted(
        (c for c in candidates if not math.isnan(c["score"])),
        key=lambda item: item["score"],
        reverse=True,
    )
    return sorted_candidates[:limit]


def _vector_norm(vector: List[float]) -> float:
    return math.sqrt(sum(x * x for x in vector))


def _cosine_similarity(base: List[float], target: List[float], base_norm: float) -> float:
    if len(target) != len(base):
        # pad or trim target to match base length
        if len(target) < len(base):
            target = target + [0.0] * (len(base) - len(target))
        else:
            target = target[: len(base)]

    target_norm = _vector_norm(target)
    if base_norm == 0.0 or target_norm == 0.0:
        return 0.0

    dot_product = sum(a * b for a, b in zip(base, target))
    return dot_product / (base_norm * target_norm)
