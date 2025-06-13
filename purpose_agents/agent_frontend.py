"""Simple stub that proves the module imports and provides run()."""
from pathlib import Path
HERE = Path(__file__).parent

def run() -> str:
    # real sprint code will go here
    print(f"[{__name__}] I am alive inside", HERE)
    return "ok"
