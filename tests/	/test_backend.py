from pathlib import Path
import importlib.util, json

ROOT = Path(__file__).parents[1]
BACKEND = ROOT / "backend"

def import_main():
    spec = importlib.util.spec_from_file_location("main", BACKEND / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_soulseed_route():
    m = import_main()
    assert hasattr(m, "app"), "FastAPI app missing"
    routes = [r.path for r in m.app.routes]
    assert "/soulseed" in routes

def test_trust_manager_exists():
    assert (BACKEND / "trust.py").exists()
