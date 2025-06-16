import io
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).parent
BACKEND = BACKEND_DIR / "main.py"


def import_app():
    spec = importlib.util.spec_from_file_location("main", BACKEND)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def setup_function(_):
    uploads = Path("uploads")
    if uploads.exists():
        for item in uploads.rglob("*"):
            if item.is_file():
                item.unlink()
        for child in sorted(uploads.glob("*")):
            if child.is_dir():
                child.rmdir()
        uploads.rmdir()


def test_avatar_upload():
    client = TestClient(import_app())
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    files = {"file": ("test.png", io.BytesIO(png), "image/png")}
    resp = client.post("/avatar/upload?playerId=alice", files=files)
    assert resp.status_code == 200
    expected = Path("uploads/alice/orig_001.png")
    assert expected.exists()
