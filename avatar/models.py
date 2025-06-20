from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List

class AvatarSeed(BaseModel):
    """Lightweight descriptor for a generated avatar."""
    playerId: str
    prompt: str
    clipVector: List[float] = Field(default_factory=list, description="768-dim CLIP vector")
    hair: float = 0.5
    eyes: float = 0.5
    body: float = 0.5
    outfit: float = 0.5
    accessories: float = 0.5
    glbUrl: str = ""
    pngUrl: str = ""
