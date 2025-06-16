from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, constr
from pathlib import Path
import hashlib
import json
import re
import shutil

app = FastAPI(title="SoulSeed API")
app.mount("/static", StaticFiles(directory="."), name="static")

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


@app.post("/avatar/upload", tags=["avatar_upload"])
def avatar_upload(playerId: str, file: UploadFile = File(...)):
    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Invalid file type")
    ext = ".png" if file.content_type == "image/png" else ".jpg"
    base = Path("uploads") / playerId
    base.mkdir(parents=True, exist_ok=True)
    dest = base / f"orig_001{ext}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    return {"url": f"/static/{dest.as_posix()}"}
