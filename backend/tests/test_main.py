import json
import importlib.util
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "backend" / "main.py"
PROFILE_FILE = ROOT / "backend" / "player_profile.json"
STATE_FILE = ROOT / "backend" / "player_state.json"


def import_app():
    spec = importlib.util.spec_from_file_location("main", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@pytest.fixture(autouse=True)
def clean_files():
    PROFILE_FILE.write_text("{}", encoding="utf-8")
    STATE_FILE.write_text("{}", encoding="utf-8")


@pytest.mark.asyncio
async def test_soulseed_creation():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/soulseed",
            json={"playerName": "Alice", "archetypePreset": "wizard"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["playerId"] == "alice"
    assert data["initSceneTag"] == "intro_001"
    assert isinstance(data["soulSeedId"], str) and len(data["soulSeedId"]) == 12
    profiles = json.loads(PROFILE_FILE.read_text())
    assert data["playerId"] in profiles


@pytest.mark.asyncio
async def test_start_and_choice_flow():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        start = await ac.post("/start", json={"soulSeedId": "abc"})
        assert start.status_code == 200
        assert start.json()["sceneTag"] == "intro_001"

        choice = await ac.post(
            "/choice",
            json={"soulSeedId": "abc", "sceneTag": "intro_001", "choiceTag": "1"},
        )
    assert choice.status_code == 200
    assert choice.json()["sceneTag"] == "dark_forest"
    state = json.loads(STATE_FILE.read_text())
    assert state["soulMap"]["abc"] == ["dark_forest"]


@pytest.mark.asyncio
async def test_choice_invalid_tag():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with pytest.raises(KeyError):
            await ac.post(
                "/choice",
                json={
                    "soulSeedId": "bad",
                    "sceneTag": "intro_001",
                    "choiceTag": "99",
                },
            )


@pytest.mark.asyncio
async def test_start_missing_soulseed():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/start", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_trust_endpoint():
    STATE_FILE.write_text(json.dumps({"trust": {"demo": 5}}), encoding="utf-8")
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/trust", params={"soulSeedId": "demo"})
    assert resp.status_code == 200
    assert resp.json()["trust"] == 5.0


@pytest.mark.asyncio
async def test_trust_missing_soulseed():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/trust")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reset_missing_endpoint():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/reset")
    assert resp.status_code == 404
