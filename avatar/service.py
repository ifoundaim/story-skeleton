from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path
from typing import Optional

from .models import AvatarSeed

# default local asset directory
DATA_DIR = Path(os.getenv("AVATAR_DATA_DIR", Path(__file__).resolve().parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _generate_clip_vector(prompt: str, image_bytes: bytes | None) -> list[float]:
    """Create a deterministic 768-dim vector based on inputs."""
    base = prompt.encode("utf-8") + (image_bytes or b"")
    digest = hashlib.sha256(base).digest()
    vec = [(digest[i % len(digest)] / 255.0) for i in range(768)]
    return vec


def save_avatar_seed(seed: AvatarSeed) -> Path:
    """Save AvatarSeed JSON under DATA_DIR."""
    path = DATA_DIR / f"{seed.playerId}_seed.json"
    path.write_text(seed.model_dump_json(indent=2), encoding="utf-8")
    return path


def create_placeholder_assets(player_id: str) -> tuple[Path, Path]:
    """Generate placeholder GLB and PNG files."""
    glb_path = DATA_DIR / f"{player_id}.glb"
    png_path = DATA_DIR / f"{player_id}.png"
    if not glb_path.exists():
        glb_path.write_bytes(b"GLB_PLACEHOLDER")
    if not png_path.exists():
        png_path.write_bytes(b"PNG_PLACEHOLDER")
    return glb_path, png_path


def generate_avatar(
    player_id: str,
    prompt: str,
    image_bytes: Optional[bytes] = None,
    hair: float = 0.5,
    eyes: float = 0.5,
    body: float = 0.5,
    outfit: float = 0.5,
    accessories: float = 0.5,
) -> AvatarSeed:
    """Generate a simple AvatarSeed and placeholder assets."""
    vec = _generate_clip_vector(prompt, image_bytes)
    glb_path, png_path = create_placeholder_assets(player_id)

    seed = AvatarSeed(
        playerId=player_id,
        prompt=prompt,
        clipVector=vec,
        hair=hair,
        eyes=eyes,
        body=body,
        outfit=outfit,
        accessories=accessories,
        glbUrl=f"/static/{glb_path.name}",
        pngUrl=f"/static/{png_path.name}",
    )
    save_avatar_seed(seed)
    return seed
