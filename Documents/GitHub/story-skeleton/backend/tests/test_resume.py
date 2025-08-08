import json
import importlib.util
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
import os
import backend.soulmap.router as soulmap_router
import backend.npc.router as npc_router
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "backend" / "main.py"
PROFILE_FILE = ROOT / "backend" / "player_profile.json"
STATE_FILE = ROOT / "backend" / "player_state.json"

os.environ["TESTING"] = "1"

def import_app():
    spec = importlib.util.spec_from_file_location("main", APP_PATH)
    if spec is None:
        raise ImportError(f"Could not load spec for {APP_PATH}")
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"Spec loader is None for {APP_PATH}")
    spec.loader.exec_module(module)
    return module.app

@pytest.fixture(autouse=True)
def clean_files():
    PROFILE_FILE.write_text("{}", encoding="utf-8")
    STATE_FILE.write_text("{}", encoding="utf-8")

@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    class DummySession:
        def query(self, *a, **kw): return self
        def filter_by(self, **kw): return self
        def first(self): return None
        def add(self, *a, **kw): pass
        def commit(self): pass
        def close(self): pass
    monkeypatch.setattr("backend.db.SessionLocal", lambda: DummySession())
    yield

def dummy_get_db():
    class DummyDB:
        def query(self, *a, **kw):
            class DummyQ:
                def filter_by(self, **kw):
                    class DummyF:
                        def order_by(self, *a, **kw):
                            class DummyO:
                                def first(self):
                                    return None
                            return DummyO()
                    return DummyF()
            return DummyQ()
    yield DummyDB()

soulmap_router.get_db = dummy_get_db
npc_router.get_db = dummy_get_db

@pytest.fixture(autouse=True)
def patch_ritual_pool(monkeypatch):
    import backend.ritual

    # Patch ritual.setup to do nothing
    async def dummy_setup():
        return None
    monkeypatch.setattr(backend.ritual, "setup", dummy_setup)

    # Patch ritual.record to return a dummy intentVector and tree
    async def dummy_record(playerId, askText, seekText, knockText, theme):
        # Return a dummy intentVector and a simple story tree
        tree = {
            "intro_001": {
                "text": "Start",
                "choices": {"1": {"next": "scene_002", "text": "Go"}},
                "media": {"images": [], "audio": []}
            },
            "scene_002": {
                "text": "Next scene",
                "choices": {},
                "media": {"images": [], "audio": []}
            }
        }
        return {
            "intentVector": [0.0] * 64,
            "theme": theme,
            "playerId": playerId,
            "tree": tree
        }
    monkeypatch.setattr(backend.ritual, "record", dummy_record)

@pytest.mark.asyncio
async def test_resume_and_history_flow():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create player profile
        resp = await ac.post("/soulseed", json={"playerName": "Bob", "archetypePreset": "rogue"})
        assert resp.status_code == 200
        data = resp.json()
        player_id = data["playerId"]
        soul_seed_id = data["soulSeedId"]

        # Start ritual (generates story tree)
        ritual_payload = {
            "playerId": player_id,
            "askText": "What is my quest?",
            "seekText": "I seek adventure.",
            "knockText": "Let me in!",
            "theme": "hero's journey"
        }
        resp = await ac.post("/ritual", json=ritual_payload)
        assert resp.status_code == 200
        next_tag = resp.json()["nextSceneTag"]

        # Start journey
        resp = await ac.post("/start", json={"soulSeedId": soul_seed_id})
        assert resp.status_code == 200
        scene = resp.json()
        assert scene["sceneTag"] == next_tag

        # Make a choice (simulate a scene transition)
        # Get the current story tree from state
        state = json.loads(STATE_FILE.read_text())
        story = state["stories"][soul_seed_id]["tree"]
        current_tag = state["stories"][soul_seed_id]["current"]
        choices = story[current_tag]["choices"]
        if not choices:
            pytest.skip("No choices in the first scene, can't test history.")
        first_choice = next(iter(choices.keys()))
        next_scene_tag = choices[first_choice]["next"] if isinstance(choices[first_choice], dict) else choices[first_choice]
        resp = await ac.post("/choice", json={"soulSeedId": soul_seed_id, "sceneTag": current_tag, "choiceTag": first_choice})
        assert resp.status_code == 200
        # Check that history is updated
        state = json.loads(STATE_FILE.read_text())
        history = state["stories"][soul_seed_id]["history"]
        assert history[-1] == next_scene_tag
        assert state["stories"][soul_seed_id]["current"] == next_scene_tag

        # Test /resume/{player_id} returns current and full history
        resp = await ac.get(f"/resume/{player_id}")
        assert resp.status_code == 200
        resume_data = resp.json()
        assert resume_data["current"] == next_scene_tag
        assert resume_data["history"] == history
        assert isinstance(resume_data["tree"], dict)

@pytest.mark.asyncio
async def test_restart_only_wipes_intended_player():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create two player profiles
        resp1 = await ac.post("/soulseed", json={"playerName": "Carol", "archetypePreset": "bard"})
        resp2 = await ac.post("/soulseed", json={"playerName": "Dave", "archetypePreset": "paladin"})
        id1 = resp1.json()["soulSeedId"]
        id2 = resp2.json()["soulSeedId"]
        # Start ritual for both
        for pid in [resp1.json()["playerId"], resp2.json()["playerId"]]:
            await ac.post("/ritual", json={"playerId": pid, "askText": "A", "seekText": "B", "knockText": "C", "theme": "hero's journey"})
        # Restart only Carol
        resp = await ac.post("/restart", json={"soulSeedId": id1})
        assert resp.status_code == 200
        state = json.loads(STATE_FILE.read_text())
        assert id1 not in state["stories"]
        assert id2 in state["stories"]

@pytest.mark.asyncio
async def test_restart_does_not_remove_profile():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/soulseed", json={"playerName": "Eve", "archetypePreset": "druid"})
        player_id = resp.json()["playerId"]
        soul_seed_id = resp.json()["soulSeedId"]
        await ac.post("/ritual", json={"playerId": player_id, "askText": "A", "seekText": "B", "knockText": "C", "theme": "hero's journey"})
        # Restart
        resp = await ac.post("/restart", json={"soulSeedId": soul_seed_id})
        assert resp.status_code == 200
        # Profile should still exist
        profiles = json.loads(PROFILE_FILE.read_text())
        assert player_id in profiles

@pytest.mark.asyncio
async def test_history_valid_if_tree_changes():
    app = import_app()
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/soulseed", json={"playerName": "Frank", "archetypePreset": "monk"})
        player_id = resp.json()["playerId"]
        soul_seed_id = resp.json()["soulSeedId"]
        await ac.post("/ritual", json={"playerId": player_id, "askText": "A", "seekText": "B", "knockText": "C", "theme": "hero's journey"})
        # Simulate a choice
        state = json.loads(STATE_FILE.read_text())
        story = state["stories"][soul_seed_id]["tree"]
        current_tag = state["stories"][soul_seed_id]["current"]
        choices = story[current_tag]["choices"]
        if not choices:
            pytest.skip("No choices in the first scene, can't test history.")
        first_choice = next(iter(choices.keys()))
        next_scene_tag = choices[first_choice]["next"] if isinstance(choices[first_choice], dict) else choices[first_choice]
        await ac.post("/choice", json={"soulSeedId": soul_seed_id, "sceneTag": current_tag, "choiceTag": first_choice})
        # Now, simulate a tree change (remove a tag from the tree)
        state = json.loads(STATE_FILE.read_text())
        state["stories"][soul_seed_id]["tree"].pop(next_scene_tag, None)
        STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
        # Resume should still return history and not crash
        resp = await ac.get(f"/resume/{player_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert next_scene_tag in data["history"] 