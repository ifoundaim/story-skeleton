import json
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "soulmap" / "main.py"
DATA_FILE = ROOT / "soulmap" / "soul_map.json"


def import_app():
    spec = importlib.util.spec_from_file_location("soulmap", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@pytest.fixture(autouse=True)
def clean_file():
    DATA_FILE.write_text("{}", encoding="utf-8")


def test_get_default_map():
    client = TestClient(import_app())
    resp = client.get("/v1/soulmap/tester")
    assert resp.status_code == 200
    data = resp.json()
    assert data["playerId"] == "tester"
    assert "courage" in data["traits"]["coreVirtues"]


def test_apply_delta():
    client = TestClient(import_app())
    client.get("/v1/soulmap/hero")
    resp = client.post(
        "/v1/soulmap/delta",
        json={"playerId": "hero", "choiceId": "battle"},
    )
    assert resp.status_code == 200
    data = json.loads(DATA_FILE.read_text())
    assert data["hero"]["coreVirtues"]["courage"] > 0

