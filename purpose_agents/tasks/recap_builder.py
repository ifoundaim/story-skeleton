import json
import os
from datetime import datetime
from typing import List, Dict, Any

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "memory_state.json")


def _load_memory() -> dict:
    if not os.path.exists(MEMORY_PATH):
        return {}
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_memory(memory: dict) -> None:
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


def build_memory(player_id: str, story: Dict[str, Any], history: List[str]) -> str:
    """
    Build a 3rd-person narrative recap of the player's journey.
    """
    lines = []
    for idx, tag in enumerate(history):
        scene = story.get(tag)
        if not scene:
            continue
        text = scene.get("text", "")
        npc_text = scene.get("npc_text", "")
        # Compose scene description
        if text:
            lines.append(text)
        if npc_text:
            lines.append(npc_text)
        # Optionally, summarize choices or emotion/trust deltas
        # (Not all stories have these, so we keep it simple)
    # Compose into a single narrative
    recap = " ".join(lines)
    # Truncate to ~300 words
    words = recap.split()
    if len(words) > 300:
        recap = " ".join(words[:300]) + "..."
    return recap


def update_memory(player_id: str, story: Dict[str, Any], history: List[str]) -> str:
    memory = _load_memory()
    recap = build_memory(player_id, story, history)
    memory[player_id] = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "recap": recap
    }
    _save_memory(memory)
    return recap 