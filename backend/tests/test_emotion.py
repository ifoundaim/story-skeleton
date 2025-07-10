import os
import json
import tempfile
import shutil
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.emotion.models import EMOTION_DIM, zero_emotion_vector, clip_emotion_vector, EmotionState

client = TestClient(app)

def test_clip_emotion_vector():
    # Values outside range should be clipped
    vec = [2.0, -2.0, 0.5, 1.1, -1.2, 0, 0.9, -0.9]
    clipped = clip_emotion_vector(vec)
    assert all(-1.0 <= v <= 1.0 for v in clipped)
    assert clipped[0] == 1.0
    assert clipped[1] == -1.0
    assert clipped[3] == 1.0
    assert clipped[4] == -1.0

def test_emotion_state_apply_delta_and_log():
    state = EmotionState("player1")
    delta = [0.5, -0.2, 0, 0, 0.1, 0, 0, 0]
    state.apply_delta(delta, "sceneA")
    assert state.vector == clip_emotion_vector(delta)
    assert state.log[-1]["sceneTag"] == "sceneA"
    assert state.log[-1]["delta"] == delta
    # Test log limit
    for i in range(60):
        state.apply_delta([0.1]*EMOTION_DIM, f"scene{i}")
    assert len(state.log) == 50

def test_get_emotion_api(tmp_path, monkeypatch):
    # Setup fake emotion_state.json
    test_path = tmp_path / "emotion_state.json"
    player_id = "testplayer"
    data = {player_id: {"vector": [0.1]*EMOTION_DIM, "log": [{"sceneTag": "s1", "delta": [0.1]*EMOTION_DIM}]}}
    test_path.write_text(json.dumps(data))
    # Patch backend.emotion.router.STATE_PATH to use our temp file
    import backend.emotion.router as emo_router
    monkeypatch.setattr(emo_router, "STATE_PATH", str(test_path))
    # Should return the correct vector and log
    resp = client.get(f"/emotion/{player_id}")
    assert resp.status_code == 200
    out = resp.json()
    assert out["vector"] == [0.1]*EMOTION_DIM
    assert out["log"][0]["sceneTag"] == "s1"
    # Should return zero vector for missing player
    resp2 = client.get("/emotion/unknown_player")
    assert resp2.status_code == 200
    out2 = resp2.json()
    assert out2["vector"] == [0.0]*EMOTION_DIM
    assert out2["log"] == [] 