"""Player memory handling for Story Engine."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, List
import psycopg


@dataclass
class MemoryManager:
    """Manage short- and long-term memory using Postgres."""

    player_id: str
    dsn: str
    short_window: int = 5
    _recent: List[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.conn = psycopg.connect(self.dsn)
        self._ensure_table()

    # ------------------------------------------------------------------
    def _ensure_table(self) -> None:
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS story_memory ("
                "player_id TEXT,"
                "scene JSONB,"
                "created_at TIMESTAMPTZ DEFAULT NOW())"
            )

    # ------------------------------------------------------------------
    def add_scene(self, scene: dict[str, Any]) -> None:
        self._recent.append(scene)
        if len(self._recent) > self.short_window:
            self._recent.pop(0)
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO story_memory (player_id, scene) VALUES (%s, %s)",
                (self.player_id, json.dumps(scene)),
            )

    # ------------------------------------------------------------------
    def recent(self) -> List[dict[str, Any]]:
        return list(self._recent)
