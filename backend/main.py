from fastapi import FastAPI
from pydantic import BaseModel, constr
from pathlib import Path
import hashlib
import json
import re

app = FastAPI(title="SoulSeed API")

DATA_FILE = Path(__file__).resolve().parent / "player_profile.json"


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


def make_soulSeedId(playerName: str, archetype: str) -> str:
    seed_source = f"{playerName}|{archetype}"
    return hashlib.sha256(seed_source.encode()).hexdigest()[:12]


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

