import json
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).parent
BACKEND = BACKEND_DIR / "main.py"
PROFILE_FILE = Path(__file__).resolve().parents[2] / "backend" / "player_profile.json"


def import_app():
    spec = importlib.util.spec_from_file_location("main", BACKEND)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def setup_function(_):
    PROFILE_FILE.write_text("{}", encoding="utf-8")


def test_create_soulseed():
    client = TestClient(import_app())

    payload = {"playerName": "Alice Smith", "archetype": "wizard"}
    resp = client.post("/soulseed", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["playerId"] == "alice-smith"
    assert data["initSceneTag"] == "intro_001"
    assert isinstance(data["soulSeedId"], str) and len(data["soulSeedId"]) == 12

    resp2 = client.post("/soulseed", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["soulSeedId"] == data["soulSeedId"]

    profiles = json.loads(PROFILE_FILE.read_text())
    assert data["playerId"] in profiles
    assert profiles[data["playerId"]]["soulSeedId"] == data["soulSeedId"]


def test_validation_error():
    client = TestClient(import_app())
    resp = client.post("/soulseed", json={"playerName": "", "archetype": "mage"})
    assert resp.status_code == 422
