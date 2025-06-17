import json
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
STATE_FILE = BACKEND_DIR / "player_state.json"


def import_app():
    spec = importlib.util.spec_from_file_location("main", BACKEND_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def setup_function(_):
    STATE_FILE.write_text("{}", encoding="utf-8")


def test_start_and_choice():
    client = TestClient(import_app())

    r = client.post("/start", json={"soulSeedId": "abc"})
    assert r.status_code == 200
    data = r.json()
    assert data["sceneTag"] == "intro_001"
    assert "crossroad" in data["text"]
    assert any(c["tag"] == "1" for c in data["choices"])

    r2 = client.post(
        "/choice",
        json={"soulSeedId": "abc", "sceneTag": "intro_001", "choiceTag": "1"},
    )
    assert r2.status_code == 200
    next_data = r2.json()
    assert next_data["sceneTag"] == "mysterious_cave"
    assert "mysterious cave" in next_data["text"].lower()

    state = json.loads(STATE_FILE.read_text())
    assert state["soulMap"]["abc"] == ["mysterious_cave"]

