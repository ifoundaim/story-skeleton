#!/usr/bin/env python3
"""
Orchestrator — runs all Codex agents in parallel, then executes pytest.
Any failing agent or failing test aborts with a non-zero exit status.

Folder layout assumed:

story-skeleton/
├─ orchestrator.py          ← (this file)
├─ purpose_agents/
│   ├─ __init__.py          # can be empty
│   ├─ agent_backend.py     # must expose run()
│   └─ agent_frontend.py    # must expose run()
└─ tests/
    └─ …

You need OPENAI_API_KEY exported in your shell before running.
"""

from __future__ import annotations

import sys
import pathlib
import subprocess
import concurrent.futures as fut
import json
from typing import Callable, List, Dict, Any

# ─── Ensure repo root is on import path ─────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))                       # <— key line

# ─── Import agent run() functions directly ─────────────────────────────────────
from purpose_agents.agent_backend import run as backend_run  # noqa: E402
from purpose_agents.agent_frontend import run as frontend_run  # noqa: E402

# ────────────────────────────────────────────────────────────────────────────────


def run_agent(fn: Callable[[], Any], name: str) -> Dict[str, Any]:
    """Run a single agent; return dict with success flag + result or error."""
    print(f"▶  Launching {name} …")
    try:
        result = fn()
        print(f"✔  {name} finished ✓")
        return {"name": name, "ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001
        print(f"✖  {name} failed: {exc}")
        return {"name": name, "ok": False, "error": str(exc)}


def run_pytest() -> bool:
    """Execute pytest quietly; return True if all tests pass."""
    print("▶  Running tests …")
    res = subprocess.run(["pytest", "-q"], cwd=ROOT)  # noqa: S603,S607
    return res.returncode == 0


def main() -> None:
    agents = [
        ("backend-agent", backend_run),
        ("frontend-agent", frontend_run),
    ]

    # Run agents in parallel
    with fut.ThreadPoolExecutor() as pool:
        results: List[Dict[str, Any]] = list(
            pool.map(lambda pair: run_agent(pair[1], pair[0]), agents)
        )

    # Abort on agent failure
    if not all(r["ok"] for r in results):
        print(json.dumps(results, indent=2))
        sys.exit("❌ One or more agents failed.")

    # Run test suite
    if not run_pytest():
        sys.exit("❌ Test suite failed.")

    print("🎉 Multi-sprint batch succeeded!")


if __name__ == "__main__":
    main()
