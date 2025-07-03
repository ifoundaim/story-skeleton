from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from .models import SoulMap
from .vector_utils import clip_vector, add_vectors
import numpy as np
import uuid
from backend.db import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()

VECTOR_SIZE = 64

def zero_vector():
    return [0.0] * VECTOR_SIZE

@router.get('/player/{player_id}')
def get_soulmap(player_id: str, db: Session = Depends(get_db)):
    row = db.query(SoulMap).filter_by(player_id=player_id).order_by(SoulMap.updated_at.desc()).first()
    if row:
        return {'player_id': player_id, 'vector': list(row.vector)}
    return {'player_id': player_id, 'vector': zero_vector()}

@router.post('/update')
def update_soulmap(payload: dict, db: Session = Depends(get_db)):
    player_id = payload.get('player_id')
    delta = payload.get('delta')
    if not player_id or not isinstance(delta, list) or len(delta) != VECTOR_SIZE:
        raise HTTPException(400, 'Invalid payload')
    row = db.query(SoulMap).filter_by(player_id=player_id).order_by(SoulMap.updated_at.desc()).first()
    base = list(row.vector) if row else zero_vector()
    new_vec = clip_vector(add_vectors(base, delta))
    new_row = SoulMap(id=uuid.uuid4(), player_id=player_id, vector=new_vec)
    db.add(new_row)
    db.commit()
    return {'player_id': player_id, 'vector': new_vec} 