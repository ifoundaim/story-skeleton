# backend/main.py
"""
central FastAPI app for SoulSeed
"""

# 1️⃣ Future imports must come first
from __future__ import annotations

# 2️⃣ Load environment variables before anything else
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# 3️⃣ Standard library imports
import hashlib
import json
import re
import sys
from typing import Any, Union

# 4️⃣ Third-party imports
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, constr

# ─── Ensure both backend and repo root are on import path ────────────────────
REPO_ROOT = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))   # for ritual
sys.path.insert(0, str(REPO_ROOT))  # for purpose_agents

import ritual
from purpose_agents.generate_story import generate_story  # dynamic story generation

# ─────────────────────────────── paths ───────────────────────────────────────
DATA_FILE   = BASE_DIR / "player_profile.json"
STORY_FILE  = BASE_DIR / "story.json"
STATE_FILE  = BASE_DIR / "player_state.json"
EDITOR_FILE = BASE_DIR / "editor.html"
UPLOADS_DIR = BASE_DIR.parent / "uploads"

app = FastAPI(title="SoulSeed API")
app.mount("/static", StaticFiles(directory=UPLOADS_DIR, check_dir=False), name="static")

@app.on_event("startup")
async def _init() -> None:
    print("🔧 [main] startup: initializing ritual subsystem")
    await ritual.setup()


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")) or fallback
        except json.JSONDecodeError:
            print(f"⚠️ [main] JSON decode failed for {path}, using fallback")
            return fallback
    return fallback

def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

_slug_re = re.compile(r"[^a-z0-9]+")

def slugify(value: str) -> str:
    return _slug_re.sub("-", value.lower()).strip("-")

def make_soul_seed_id(player_name: str, archetype: str) -> str:
    raw = f"{player_name}|{archetype}"
    sid = hashlib.sha256(raw.encode()).hexdigest()[:12]
    print(f"🆔 [main] generated soulSeedId={sid} from {raw}")
    return sid


# ─────────────────────────────── models ──────────────────────────────────────
class PlayerProfileIn(BaseModel):
    playerName: constr(strip_whitespace=True, min_length=1)
    archetypePreset: str
    archetypeCustom: str | None = None

class SoulSeedResponse(BaseModel):
    playerId: str
    soulSeedId: str
    initSceneTag: str

class RitualRequest(BaseModel):
    playerId: str
    askText: constr(max_length=280)
    seekText: constr(max_length=280)
    knockText: constr(max_length=280)
    theme: str

class RitualResponse(BaseModel):
    theme: str
    intentVector: list[float]
    nextSceneTag: str

class StartRequest(BaseModel):
    soulSeedId: str

class ChoiceRequest(BaseModel):
    soulSeedId: str
    sceneTag: str
    choiceTag:  Union[str, int] | None = Field(None, alias="choiceTag")
    tag:        Union[str, int] | None = Field(None, alias="tag")
    choice:     Union[str, int] | None = Field(None, alias="choice")
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @property
    def choice_val(self) -> Union[str, int]:
        return (
            self.choiceTag
            if self.choiceTag is not None
            else (self.tag if self.tag is not None else self.choice)
        )

ChoiceRequest.model_rebuild()

class SceneResponse(BaseModel):
    sceneTag: str
    text: str
    choices: list[dict[str, str]]

# ────────────────────────────── ritual endpoint ──────────────────────────────
@app.post("/ritual", response_model=RitualResponse)
async def api_ritual(payload: RitualRequest) -> RitualResponse:
    print(f"🔮 [main] /ritual payload={payload.json()}")

    data = await ritual.record(
        payload.playerId,
        payload.askText,
        payload.seekText,
        payload.knockText,
        payload.theme,
    )

    try:
        first_tag, tree = await generate_story(
            payload.playerId,
            data["theme"],
            data["intentVector"],
        )
    except Exception as e:
        print(f"⚠️ [main] story generation failed: {e}")
        raise HTTPException(500, "Failed to generate story tree")

    state = _read_json(STATE_FILE, {"stories": {}})
    state["stories"][payload.playerId] = {"tree": tree, "current": first_tag}
    _write_json(STATE_FILE, state)

    print(f"✅ [main] /ritual returning nextSceneTag={first_tag}")
    return RitualResponse(
        theme=data["theme"],
        intentVector=data["intentVector"],
        nextSceneTag=first_tag,
    )


@app.post("/avatar/upload")
async def upload_avatar(
    playerId: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, str]:
    print(f"📷 [main] upload avatar for playerId={playerId}, filename={file.filename}")
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix
    dest_dir = UPLOADS_DIR / playerId
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"orig_001{ext}"
    dest.write_bytes(await file.read())

    url = f"/static/{playerId}/{dest.name}"
    print(f"✅ [main] avatar stored at {dest}, serving at {url}")
    return {"url": url}


# ────────────────────────── profile / soul-seed ──────────────────────────────
@app.post("/soulseed", response_model=SoulSeedResponse)
def create_player_profile(payload: PlayerProfileIn) -> SoulSeedResponse:
    print(f"🎬 [main] /soulseed payload={payload.json()}")
    player_id = slugify(payload.playerName)
    archetype = payload.archetypeCustom or payload.archetypePreset
    soul_seed_id = make_soul_seed_id(payload.playerName, archetype)

    profiles = _read_json(DATA_FILE, {})
    profiles[player_id] = {
        "playerName": payload.playerName,
        "archetype": archetype,
        "soulSeedId": soul_seed_id,
    }
    _write_json(DATA_FILE, profiles)
    print(f"✅ [main] saved profile for player={player_id}")

    return SoulSeedResponse(
        playerId=player_id,
        soulSeedId=soul_seed_id,
        initSceneTag="intro_001",
    )


def _scene_to_response(tag: str, story: dict[str, Any]) -> SceneResponse:
    scene = story[tag]
    choices = [
        {"tag": str(k), "label": v.get("text", "").replace("_", " ").title()}
        for k, v in scene.get("choices", {}).items()
    ]
    return SceneResponse(sceneTag=tag, text=scene["text"], choices=choices)

# ───────────────────────── ritual endpoint ─────────────────────────────────
@app.post("/start", response_model=SceneResponse)
def api_start(req: StartRequest) -> SceneResponse:
    print(f"▶️ [main] /start called with soulSeedId={req.soulSeedId}")
    state = _read_json(STATE_FILE, {"stories": {}})
    st = state["stories"].get(req.soulSeedId)

    if st:
        print("✅ [main] using dynamic story tree")
        return _scene_to_response(st["current"], st["tree"])

    print("⚠️ [main] falling back to static story.json")
    story = _read_json(STORY_FILE, {})
    return _scene_to_response("intro_001", story)


def _choose_py(req: ChoiceRequest) -> SceneResponse:
    print(f"▶️ [main] choose({req.soulSeedId}, {req.sceneTag}, choice={req.choice_val})")
    state = _read_json(STATE_FILE, {"stories": {}})
    story_data = state["stories"].get(req.soulSeedId)

    if story_data is None:
        raise HTTPException(404, "No story tree found for this player")

    tree = story_data["tree"]
    scene = tree.get(req.sceneTag)
    if scene is None:
        raise HTTPException(404, f"Scene '{req.sceneTag}' not found")

    str_key_map = {str(k): v["next"] for k, v in scene.get("choices", {}).items()}
    key = str(req.choice_val)
    if key not in str_key_map:
        raise HTTPException(400, f"Choice '{key}' not found in scene")

    next_tag = str_key_map[key]
    state["stories"][req.soulSeedId]["current"] = next_tag
    _write_json(STATE_FILE, state)

    print(f"✅ [main] next sceneTag={next_tag}")
    return _scene_to_response(next_tag, tree)

# ────────────────────────────── choice endpoint ──────────────────────────────
@app.post("/choice", response_model=SceneResponse)
@app.post("/choose", response_model=SceneResponse)
def api_choose(req: ChoiceRequest = Body(...)) -> SceneResponse:
    try:
        return _choose_py(req)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/trust")
def api_trust(soulSeedId: str) -> dict[str, float]:
    print(f"🔍 [main] /trust lookup soulSeedId={soulSeedId}")
    st = _read_json(STATE_FILE, {"trust": {}}).get("trust", {})
    trust_val = float(st.get(soulSeedId, 0))
    print(f"✅ [main] /trust -> {trust_val}")
    return {"trust": trust_val}


@app.post("/reset")
def api_reset(soulSeedId: str | None = Form(default=None)) -> dict[str, bool]:
    if soulSeedId is None:
        raise HTTPException(404, "Missing soulSeedId")
    _reset(soulSeedId)
    return {"reset": True}


@app.get("/editor", response_class=HTMLResponse)
def story_editor() -> HTMLResponse:
    if EDITOR_FILE.exists():
        return HTMLResponse(EDITOR_FILE.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Story Editor placeholder</h1>")
