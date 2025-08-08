from fastapi import APIRouter, HTTPException
from .models import EmotionState, zero_emotion_vector
import json
import os

router = APIRouter()
STATE_PATH = os.path.join(os.path.dirname(__file__), "../emotion_state.json")


def load_states():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r") as f:
        return json.load(f)

def save_states(states):
    with open(STATE_PATH, "w") as f:
        json.dump(states, f)

@router.get("/emotion/{player_id}")
def get_emotion(player_id: str):
    states = load_states()
    state = states.get(player_id)
    if not state:
        return {"vector": zero_emotion_vector(), "log": []}
    return state 