# backend/trust.py
"""Simple persistent trust tracker for players."""

from __future__ import annotations

import json
from pathlib import Path


class TrustManager:
    """Manage a player's trust score persisted in a JSON file."""

    def __init__(self, player_name: str, path: str = "backend/player_state.json"):
        self.player_name = player_name
        self.path = Path(path)
        self.trust: float = 0.0
        self.load()

    # persistence -----------------------------------------------------
    def load(self) -> None:
        """Load trust value from ``self.path`` for ``self.player_name``."""
        try:
            with self.path.open("r") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        self.trust = float(data.get(self.player_name, 0))

    def save(self) -> None:
        """Save current trust value to ``self.path``."""
        try:
            with self.path.open("r") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data[self.player_name] = self.trust
        with self.path.open("w") as fh:
            json.dump(data, fh, indent=2)

    # api -------------------------------------------------------------
    def adjust(self, delta: float) -> None:
        """Change trust by ``delta``, clamp to [-100, 100], then save."""
        self.trust += float(delta)
        if self.trust > 100:
            self.trust = 100
        elif self.trust < -100:
            self.trust = -100
        self.save()

    def get(self) -> float:
        """Return the current trust score."""
        return self.trust
