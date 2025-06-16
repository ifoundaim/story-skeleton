from pathlib import Path
import importlib.util

ROOT = Path(__file__).parents[2]
TRUST_PATH = ROOT / "backend" / "trust.py"

spec = importlib.util.spec_from_file_location("trust", TRUST_PATH)
trust_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trust_module)
TrustManager = trust_module.TrustManager


def test_adjust_increase(tmp_path):
    path = tmp_path / "state.json"
    tm = TrustManager("alice", path=str(path))
    before = tm.get()
    tm.adjust(5)
    tm_reloaded = TrustManager("alice", path=str(path))
    assert tm_reloaded.get() == before + 5


def test_adjust_decrease(tmp_path):
    path = tmp_path / "state.json"
    tm = TrustManager("bob", path=str(path))
    tm.adjust(5)
    tm2 = TrustManager("bob", path=str(path))
    tm2.adjust(-3)
    tm3 = TrustManager("bob", path=str(path))
    assert tm3.get() == 2
