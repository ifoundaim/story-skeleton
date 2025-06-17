<<<<<<< HEAD
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
=======
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
>>>>>>> 21591e2d54e369f7ecd73f9b9dec1f71d79d7af7
from pydantic import BaseModel, constr
from pathlib import Path
from fastapi.staticfiles import StaticFiles
import hashlib
import json
import re

app = FastAPI(title="SoulSeed API")

DATA_FILE = Path(__file__).resolve().parent / "player_profile.json"
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
STORY_FILE = Path(__file__).resolve().parent / "story.json"
STATE_FILE = Path(__file__).resolve().parent / "player_state.json"
EDITOR_FILE = Path(__file__).resolve().parent / "editor.html"

app.mount(
    "/static",
    StaticFiles(directory=UPLOADS_DIR, check_dir=False),
    name="static",
)


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


def load_json(path: Path, fallback: dict) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f) or fallback
        except json.JSONDecodeError:
            return fallback
    return fallback


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-+", "-", slug)


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


class StartRequest(BaseModel):
    soulSeedId: str


class ChoiceRequest(BaseModel):
    soulSeedId: str
    tag: str


class SceneResponse(BaseModel):
    sceneTag: str
    text: str
    choices: list


@app.post("/avatar/upload")
async def upload_avatar(
    playerId: str = Form(...), file: UploadFile = File(...)
) -> dict:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix
    dest_dir = UPLOADS_DIR / playerId
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"orig_001{ext}"
    content = await file.read()
    dest.write_bytes(content)
    return {"url": f"/static/{playerId}/{dest.name}"}


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
        playerId=player_id, soulSeedId=soul_seed_id, initSceneTag="intro_001"
    )


def _scene_to_response(tag: str, story: dict) -> SceneResponse:
    scene = story[tag]
    choices = [
        {"tag": k, "label": v.replace("_", " ").title()}
        for k, v in scene.get("choices", {}).items()
    ]
    return SceneResponse(sceneTag=tag, text=scene["text"], choices=choices)


@app.post("/start", response_model=SceneResponse)
def start_story(req: StartRequest) -> SceneResponse:
    story = load_json(STORY_FILE, {})
    initial_tag = "intro_001"

    state = load_json(STATE_FILE, {"soulMap": {}})
    soul_map = state.setdefault("soulMap", {})
    soul_map[req.soulSeedId] = [initial_tag]
    save_json(STATE_FILE, state)

    return _scene_to_response(initial_tag, story)


@app.post("/choose", response_model=SceneResponse)
def choose(req: ChoiceRequest) -> SceneResponse:
    story = load_json(STORY_FILE, {})
    state = load_json(STATE_FILE, {"soulMap": {}})
    soul_map = state.setdefault("soulMap", {})

    history = soul_map.get(req.soulSeedId)
    if not history:
        raise HTTPException(400, "No story in progress")

    current_tag = history[-1]
    current = story.get(current_tag)
    if current is None or req.tag not in current.get("choices", {}):
        raise HTTPException(400, "Invalid choice")

    next_tag = current["choices"][req.tag]
    history.append(next_tag)
    save_json(STATE_FILE, state)

    return _scene_to_response(next_tag, story)


@app.get("/trust")
def get_trust(soulSeedId: str) -> dict:
    state = load_json(STATE_FILE, {"trust": {}})
    return {"trust": float(state.get("trust", {}).get(soulSeedId, 0))}


<<<<<<< HEAD
@app.post("/reset")
def reset_story(soulSeedId: str = Form(...)) -> dict:
    state = load_json(STATE_FILE, {"soulMap": {}})
    soul_map = state.get("soulMap", {})
    if soulSeedId in soul_map:
        del soul_map[soulSeedId]
        save_json(STATE_FILE, state)
    return {"reset": True}
=======
@app.get("/editor", response_class=HTMLResponse)
def story_editor() -> HTMLResponse:
    """Serve a basic HTML page for editing the story JSON."""
    if EDITOR_FILE.exists():
        return HTMLResponse(EDITOR_FILE.read_text())
    return HTMLResponse("<html><body><h1>Story Editor</h1></body></html>")

>>>>>>> 21591e2d54e369f7ecd73f9b9dec1f71d79d7af7
