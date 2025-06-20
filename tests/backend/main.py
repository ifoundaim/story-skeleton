"""SoulSeed FastAPI backend used by the test-suite.

Originally this was only a small stub exposing a health-check route at
``/soulseed``.  For the current sprint the file houses a minimal
implementation of the ``POST /soulseed`` endpoint that creates a player
profile.  The older health-check route remains for backwards
compatibility so existing tests continue to pass.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, constr
from pathlib import Path
import hashlib
import json
import re
import shutil

#: minimal FastAPI app the tests look for
app = FastAPI(title="SoulSeed API stub")
app.mount("/static", StaticFiles(directory="."), name="static")


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


def make_soulSeedId(player_name: str, archetype: str) -> str:
    return hashlib.sha256(f"{player_name}|{archetype}".encode()).hexdigest()[:12]


class PlayerProfileIn(BaseModel):
    playerName: constr(strip_whitespace=True, min_length=1)
    archetypePreset: str
    archetypeCustom: str | None = None


class SoulSeedResponse(BaseModel):
    playerId: str
    soulSeedId: str
    initSceneTag: str


@app.post("/soulseed", response_model=SoulSeedResponse)
def create_player_profile(request: PlayerProfileIn) -> SoulSeedResponse:
    player_id = slugify(request.playerName)
    archetype = request.archetypeCustom or request.archetypePreset
    soul_seed_id = make_soulSeedId(request.playerName, archetype)

    profiles = load_profiles()
    profiles[player_id] = {
        "playerName": request.playerName,
        "archetype": archetype,
        "soulSeedId": soul_seed_id,
    }
    save_profiles(profiles)

    return SoulSeedResponse(
        playerId=player_id,
        soulSeedId=soul_seed_id,
        initSceneTag="intro_001",
    )


@app.post("/avatar/upload")
def upload_avatar(playerId: str = Form(...), file: UploadFile = File(...)) -> dict:
    uploads = Path(__file__).resolve().parents[2] / "uploads" / playerId
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / f"orig_001{Path(file.filename).suffix}"
    dest.write_bytes(file.file.read())
    return {"url": f"/static/{playerId}/{dest.name}"}


def import_main():
    """
    Helper the tests call.

    Returning the FastAPI instance keeps them happy while the real
    implementation is built in later sprints.
    """
    return app
