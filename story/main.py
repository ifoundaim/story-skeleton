"""FastAPI service exposing GPT-4o story generation."""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai

from .engine import generate_scene, log_choice
from .memory import MemoryManager

app = FastAPI(title="Story Engine")

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
DB_DSN = os.environ.get("STORY_DB_DSN", "postgresql://localhost/story")

client = openai.Client(api_key=OPENAI_KEY)


class SceneRequest(BaseModel):
    playerId: str
    avatarSeed: dict[str, Any]
    soulMap: dict[str, Any]
    intent: str


@app.post("/scene")
def scene(req: SceneRequest) -> dict[str, Any]:
    mm = MemoryManager(req.playerId, DB_DSN)
    scene_data = generate_scene(
        client, mm, req.avatarSeed, req.soulMap, req.intent
    )
    return scene_data


class ChoiceRequest(BaseModel):
    playerId: str
    sceneId: str
    choiceId: str
    delta: dict[str, Any]


@app.post("/choice")
def choice(req: ChoiceRequest) -> dict[str, bool]:
    log_choice(req.playerId, req.sceneId, req.choiceId, req.delta)
    return {"logged": True}
