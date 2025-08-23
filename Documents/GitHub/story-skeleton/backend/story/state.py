from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime


Phase = Literal["early", "mid", "late"]


@dataclass
class Promise:
    id: str
    description: str
    created_at_scene: int
    npc_id: Optional[str] = None
    due_by_scene: Optional[int] = None
    fulfilled: bool = False
    breached: bool = False


@dataclass
class Reputation:
    truthful: float = 0.5
    merciful: float = 0.5
    loyal: float = 0.5
    resolute: float = 0.5

    def apply_delta(self, delta: Dict[str, float]) -> None:
        """Apply reputation changes, clamping to [0.0, 1.0] range."""
        for key, change in delta.items():
            if hasattr(self, key):
                current = getattr(self, key)
                new_value = max(0.0, min(1.0, current + change))
                setattr(self, key, new_value)


@dataclass
class Resources:
    supplies: int = 0
    injuries: int = 0
    time: int = 0

    def apply_delta(self, delta: Dict[str, int]) -> None:
        """Apply resource changes."""
        for key, change in delta.items():
            if hasattr(self, key):
                current = getattr(self, key)
                new_value = current + change
                # Clamp supplies and time to non-negative, injuries can be negative (healing)
                if key in ["supplies", "time"]:
                    new_value = max(0, new_value)
                setattr(self, key, new_value)


@dataclass
class StoryState:
    scene_index: int
    phase: Phase
    tension: float
    target_curve: List[float]
    player: Dict[str, Any]
    npcs: Dict[str, Dict[str, Any]]  # trust: float, arc_state: str, interactions: int, last_invite_scene: Optional[int]
    party: List[str]
    flags: Dict[str, Any] = field(default_factory=dict)
    
    # Consequence Fabric additions
    world_flags: Dict[str, bool | str | int] = field(default_factory=dict)
    promises: List[Promise] = field(default_factory=list)
    reputation: Reputation = field(default_factory=Reputation)
    resources: Resources = field(default_factory=Resources)

    def update_phase_from_curve(self) -> None:
        # Derive phase from scene index heuristics (0–6 early, 7–21 mid, 22–29 late)
        if self.scene_index <= 6:
            self.phase = "early"
        elif self.scene_index <= 21:
            self.phase = "mid"
        else:
            self.phase = "late"

    def bump_interactions(self, npc_id: str, amount: int = 1) -> None:
        npc = self.npcs.get(npc_id)
        if npc is None:
            return
        npc["interactions"] = int(npc.get("interactions", 0)) + amount

    def set_arc(self, npc_id: str, new_state: str) -> None:
        npc = self.npcs.get(npc_id)
        if npc is None:
            return
        npc["arc_state"] = new_state

    def apply_trust_delta(self, npc_id: str, delta: float) -> None:
        npc = self.npcs.get(npc_id)
        if npc is None:
            return
        trust_before = float(npc.get("trust", 0.0))
        trust_after = max(0.0, min(1.0, trust_before + delta))
        npc["trust"] = trust_after

    def set_last_invite_scene(self, npc_id: str, scene_index: int) -> None:
        npc = self.npcs.get(npc_id)
        if npc is None:
            return
        npc["last_invite_scene"] = scene_index

    @property
    def target_tension(self) -> float:
        if not self.target_curve:
            return self.tension
        idx = max(0, min(len(self.target_curve) - 1, self.scene_index))
        return float(self.target_curve[idx])

    def record_recent_tags(self, tags: List[str]) -> None:
        recent_tags: List[str] = self.flags.setdefault("recent_tags", [])
        recent_tags.extend(tags)
        # Truncate to a reasonable window (use diversity.window if present)
        diversity_cfg = (self.flags.get("config") or {}).get("diversity") or {}
        window = int(diversity_cfg.get("window", 4)) * 3  # keep a larger memory to allow counting repeats
        if len(recent_tags) > window:
            self.flags["recent_tags"] = recent_tags[-window:]

    # Consequence Fabric methods
    def set_world_flag(self, key: str, value: bool | str | int) -> None:
        """Set a world flag to a specific value."""
        self.world_flags[key] = value

    def clear_world_flag(self, key: str) -> None:
        """Remove a world flag."""
        self.world_flags.pop(key, None)

    def add_promise(self, promise_id: str, description: str, npc_id: Optional[str] = None, 
                   due_by_scene: Optional[int] = None) -> None:
        """Add a new promise to track."""
        promise = Promise(
            id=promise_id,
            description=description,
            created_at_scene=self.scene_index,
            npc_id=npc_id,
            due_by_scene=due_by_scene
        )
        self.promises.append(promise)

    def fulfill_promise(self, promise_id: str) -> bool:
        """Mark a promise as fulfilled. Returns True if found and not already fulfilled."""
        for promise in self.promises:
            if promise.id == promise_id and not promise.fulfilled and not promise.breached:
                promise.fulfilled = True
                return True
        return False

    def breach_promise(self, promise_id: str) -> bool:
        """Mark a promise as breached. Returns True if found and not already breached."""
        for promise in self.promises:
            if promise.id == promise_id and not promise.fulfilled and not promise.breached:
                promise.breached = True
                return True
        return False

    def get_active_promises(self, npc_id: Optional[str] = None) -> List[Promise]:
        """Get all active (unfulfilled, unbreached) promises, optionally filtered by NPC."""
        active = [p for p in self.promises if not p.fulfilled and not p.breached]
        if npc_id:
            active = [p for p in active if p.npc_id == npc_id]
        return active

    def get_overdue_promises(self) -> List[Promise]:
        """Get promises that are past their due date."""
        return [p for p in self.promises 
                if not p.fulfilled and not p.breached 
                and p.due_by_scene is not None 
                and self.scene_index > p.due_by_scene]

    def apply_reputation_delta(self, delta: Dict[str, float]) -> None:
        """Apply reputation changes."""
        self.reputation.apply_delta(delta)

    def apply_resource_delta(self, delta: Dict[str, int]) -> None:
        """Apply resource changes."""
        self.resources.apply_delta(delta)

