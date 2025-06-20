import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND = ROOT_DIR / "backend" / "main.py"
AVATAR_DIR = ROOT_DIR / "avatar" / "data"


def import_app():
    spec = importlib.util.spec_from_file_location("main", BACKEND)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def setup_function(_):
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    for p in AVATAR_DIR.glob("*"):
        p.unlink()


def test_avatar_create():
    client = TestClient(import_app())

    files = {"reference": ("ref.png", b"123", "image/png")}
    data = {
        "playerId": "tester",
        "prompt": "cool hero",
        "hair": "0.1",
    }
    r = client.post("/avatar/create", data=data, files=files)
    assert r.status_code == 200
    js = r.json()
    assert js["playerId"] == "tester"
    assert js["pngUrl"].endswith("tester.png")
    seed_file = AVATAR_DIR / "tester_seed.json"
    assert seed_file.exists()
