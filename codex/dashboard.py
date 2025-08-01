from __future__ import annotations

"""FastAPI dashboard exposing orchestrator status."""

from fastapi import FastAPI

from .orchestrator import Orchestrator

app = FastAPI(title="Codex Orchestrator")
orc = Orchestrator()


@app.on_event("startup")
async def startup() -> None:
    await orc.start([])


@app.get("/tasks")
async def list_tasks() -> dict:
    return {
        "queued": [t.sprint for t in orc.queue._queue._queue],
        "active": {k: v.sprint for k, v in orc.active.items()},
        "completed": [{"sprint": t.sprint, "status": t.status} for t in orc.queue.completed],
    }
