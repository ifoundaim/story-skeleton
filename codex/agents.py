from __future__ import annotations

"""Agent role definitions and stubs for each sprint."""

from typing import Any, Callable


class Agent:
    """Simple callable agent wrapper."""

    def __init__(self, name: str, handler: Callable[[], Any]):
        self.name = name
        self.handler = handler

    def run(self) -> Any:
        return self.handler()


# --- Sprint agent stubs -------------------------------------------------------

def ritual_agent() -> str:
    return "TR01 done"


def avatar_agent() -> str:
    return "AV01 done"


def soulmap_agent() -> str:
    return "SM01 done"


def story_agent() -> str:
    return "ST01 done"


AGENTS: dict[str, Agent] = {
    "TR01": Agent("Ritual", ritual_agent),
    "AV01": Agent("Avatar", avatar_agent),
    "SM01": Agent("SoulMap", soulmap_agent),
    "ST01": Agent("Story", story_agent),
}
