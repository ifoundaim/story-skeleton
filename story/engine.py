"""GPT-4o powered scene generation pipeline."""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List

import openai
import httpx

from .memory import MemoryManager


SAFE_SCENE_STUB = {
    "sceneId": "safe_stub",
    "title": "A Calm Moment",
    "description": "The world pauses briefly while things realign.",
    "dialogue": ["..."],
    "options": [{"id": "retry", "text": "Continue"}],
}


def _build_system_prompt(avatar_seed: dict[str, Any], soul_map: dict[str, Any]) -> str:
    return (
        "You are the Story Engine for PurposePath. "
        "Generate immersive anime-style scenes in JSON. "
        "Use the player's avatar traits and soul map to tailor the narrative."  
    )


def _build_user_prompt(
    intent: str, memory: List[dict[str, Any]],
) -> str:
    recent = "\n".join(json.dumps(m) for m in memory)
    return (
        f"Intent: {intent}\n"
        f"Recent Scenes: {recent}\n"
        "Craft the next beat as JSON using the schema."
    )


def generate_scene(
    client: openai.Client,
    memory: MemoryManager,
    avatar_seed: dict[str, Any],
    soul_map: dict[str, Any],
    intent: str,
) -> dict[str, Any]:
    system_prompt = _build_system_prompt(avatar_seed, soul_map)
    user_prompt = _build_user_prompt(intent, memory.recent())

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    retries = 2
    start = time.perf_counter()
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"},
            )
            scene = json.loads(resp.choices[0].message.content)
            if _validate_scene(scene):
                latency = time.perf_counter() - start
                scene["latency"] = latency
                memory.add_scene(scene)
                print("scene_gen", json.dumps(scene))
                return scene
        except Exception:
            pass
    # fallback
    scene = SAFE_SCENE_STUB | {"latency": time.perf_counter() - start}
    print("scene_gen", json.dumps(scene))
    return scene


def _validate_scene(scene: Dict[str, Any]) -> bool:
    try:
        assert isinstance(scene.get("sceneId"), str)
        assert isinstance(scene.get("title"), str)
        assert isinstance(scene.get("description"), str)
        assert isinstance(scene.get("dialogue"), list)
        opts = scene.get("options")
        assert isinstance(opts, list) and 1 <= len(opts) <= 4
        for o in opts:
            assert "id" in o and "text" in o
        return True
    except AssertionError:
        return False


def log_choice(
    player_id: str,
    scene_id: str,
    choice_id: str,
    delta: Dict[str, Any],
    *,
    base_url: str = "http://localhost:8000",
) -> None:
    payload = {
        "playerId": player_id,
        "sceneId": scene_id,
        "choiceId": choice_id,
        "timestamp": int(time.time()),
    }
    try:
        with httpx.Client(timeout=2) as client:
            client.post(f"{base_url}/story_choices", json=payload)
            client.post(f"{base_url}/v1/soulmap/delta", json=delta)
    finally:
        print("checkpoint_choice", json.dumps(payload))
