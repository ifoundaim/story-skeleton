from pathlib import Path
from .common_prompts import call_codex

ROOT = Path(__file__).parents[1]
BACKEND = ROOT / "backend"

PROMPT = f"""
You are updating the PurposePath backend (FastAPI) for two features:
1. Sprint 5 – Soul-Seed endpoint `/soulseed`:
   • POST {{avatarArchetype}} → returns {{soulSeedId, initialSceneTag}}
   • persists soul seed in player_profile.json
2. Sprint 7 – Trust Manager module:
   • Create `trust.py` with TrustManager class (load/save json, update(score))
   • Integrate TrustManager into main.py play_scene()

Coding constraints:
* Keep code Python 3.12, FastAPI style.
* Pass tests in tests/test_backend.py.
Output full updated files.
"""

def run():
    main_file = BACKEND / "main.py"
    call_codex(PROMPT, main_file)
