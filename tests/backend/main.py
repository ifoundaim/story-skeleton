"""SoulSeed FastAPI backend used by the test-suite.

Originally this was only a small stub exposing a health-check route at
``/soulseed``.  For the current sprint the file houses a minimal
implementation of the ``POST /soulseed`` endpoint that creates a player
profile.  The older health-check route remains for backwards
compatibility so existing tests continue to pass.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, constr
from pathlib import Path
import hashlib
import json
import re

#: minimal FastAPI app the tests look for
app = FastAPI(title="SoulSeed API stub")


@app.get("/soulseed", tags=["health"])
def soulseed_root() -> dict[str, str]:
    """Health-check endpoint required by the placeholder test suite."""
    return {"status": "alive"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

DATA_FILE = Path(__file__).resolve().parents[2] / "backend" / "player_profile.json"


def load_profiles() -> dict:
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except json.JSONDecodeError:
            return {}
    return {}


def save_profiles(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug


class SoulSeedRequest(BaseModel):
    playerName: constr(min_length=1)
    archetype: constr(min_length=1)


class SoulSeedResponse(BaseModel):
    playerId: str
    soulSeedId: str
    initSceneTag: str


@app.post("/soulseed", response_model=SoulSeedResponse)
def create_soulseed(request: SoulSeedRequest) -> SoulSeedResponse:
    player_id = slugify(request.playerName)
    seed_source = f"{request.playerName}|{request.archetype}"
    soul_seed_id = hashlib.sha256(seed_source.encode()).hexdigest()[:12]

    profiles = load_profiles()
    profiles[player_id] = {
        "playerName": request.playerName,
        "archetype": request.archetype,
        "soulSeedId": soul_seed_id,
    }
    save_profiles(profiles)

    return SoulSeedResponse(
        playerId=player_id,
        soulSeedId=soul_seed_id,
        initSceneTag="intro_001",
    )


def import_main():
    """
    Helper the tests call.

    Returning the FastAPI instance keeps them happy while the real
    implementation is built in later sprints.
    """
    return app
