import json
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
BACKEND_FILE = ROOT / "backend" / "main.py"
STATE_FILE = ROOT / "backend" / "player_state.json"

def import_app():
    spec = importlib.util.spec_from_file_location("main", BACKEND_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def setup_function(_):
    STATE_FILE.write_text(json.dumps({"trust": {"demo": -5}}), encoding="utf-8")


def test_get_trust():
    client = TestClient(import_app())
    resp = client.get("/trust", params={"soulSeedId": "demo"})
    assert resp.status_code == 200
    assert resp.json()["trust"] == -5

