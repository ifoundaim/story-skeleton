"""
backend/main.py – central FastAPI app for SoulSeed
(route list is in the doc-string of the first message)
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Union

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, constr

# ─────────────────────────────── paths ───────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
DATA_FILE   = BASE_DIR / "player_profile.json"
STORY_FILE  = BASE_DIR / "story.json"
STATE_FILE  = BASE_DIR / "player_state.json"
EDITOR_FILE = BASE_DIR / "editor.html"
UPLOADS_DIR = BASE_DIR.parent / "uploads"             # one level above backend/

app = FastAPI(title="SoulSeed API")
app.mount("/static", StaticFiles(directory=UPLOADS_DIR, check_dir=False), name="static")

# ────────────────────────────── helpers ──────────────────────────────────────
def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")) or fallback
        except json.JSONDecodeError:
            return fallback
    return fallback


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """simple slug without external deps"""
    return _slug_re.sub("-", value.lower()).strip("-").strip("-")


def make_soul_seed_id(player_name: str, archetype: str) -> str:
    return hashlib.sha256(f"{player_name}|{archetype}".encode()).hexdigest()[:12]

# ─────────────────────────────── models ──────────────────────────────────────
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
    sceneTag: str
    #  front-end may send any of these ↓
    choiceTag:  Union[str, int] | None = Field(None, alias="choiceTag")
    tag:        Union[str, int] | None = Field(None, alias="tag")
    choice:     Union[str, int] | None = Field(None, alias="choice")

    # let Pydantic accept field-names **and** aliases
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # single accessor the rest of the code can use
    @property
    def choice_val(self) -> Union[str, int]:
        return (
            self.choiceTag
            if self.choiceTag is not None
            else (self.tag if self.tag is not None else self.choice)
        )


class SceneResponse(BaseModel):
    sceneTag: str
    text: str
    choices: list[dict[str, str]]

# ─────────────────────────── avatar upload ───────────────────────────────────
@app.post("/avatar/upload")
async def upload_avatar(
    playerId: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, str]:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    ext       = Path(file.filename).suffix
    dest_dir  = UPLOADS_DIR / playerId
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest      = dest_dir / f"orig_001{ext}"
    dest.write_bytes(await file.read())

    return {"url": f"/static/{playerId}/{dest.name}"}

# ────────────────────────── profile / soul-seed ──────────────────────────────
@app.post("/soulseed", response_model=SoulSeedResponse)
def create_player_profile(payload: PlayerProfileIn) -> SoulSeedResponse:
    player_id    = slugify(payload.playerName)
    archetype    = payload.archetypeCustom or payload.archetypePreset
    soul_seed_id = make_soul_seed_id(payload.playerName, archetype)

    profiles            = _read_json(DATA_FILE, {})
    profiles[player_id] = {
        "playerName": payload.playerName,
        "archetype":  archetype,
        "soulSeedId": soul_seed_id,
    }
    _write_json(DATA_FILE, profiles)

    return SoulSeedResponse(playerId=player_id,
                            soulSeedId=soul_seed_id,
                            initSceneTag="intro_001")

# ─────────────────────────── story helpers ───────────────────────────────────
def _scene_to_response(tag: str, story: dict[str, Any]) -> SceneResponse:
    scene   = story[tag]
    choices = [
        {"tag": str(k), "label": v.replace("_", " ").title()}
        for k, v in scene.get("choices", {}).items()
    ]
    return SceneResponse(sceneTag=tag, text=scene["text"], choices=choices)

# start
@app.post("/start", response_model=SceneResponse)
def api_start(req: StartRequest) -> SceneResponse:
    story = _read_json(STORY_FILE, {})
    state = _read_json(STATE_FILE, {"soulMap": {}})

    initial_tag = "intro_001"
    state.setdefault("soulMap", {})[req.soulSeedId] = [initial_tag]
    _write_json(STATE_FILE, state)

    return _scene_to_response(initial_tag, story)

# choose – pure python part
def _choose_py(req: ChoiceRequest) -> SceneResponse:
    story = _read_json(STORY_FILE, {})
    state = _read_json(STATE_FILE, {"soulMap": {}})

    scene = story.get(req.sceneTag)
    if scene is None:
        raise HTTPException(404, "Scene not found")

    str_key_map = {str(k): v for k, v in scene.get("choices", {}).items()}
    key         = str(req.choice_val)
    if key not in str_key_map:
        raise KeyError(f"Choice '{key}' not available")

    next_tag = str_key_map[key]
    state.setdefault("soulMap", {}).setdefault(req.soulSeedId, []).append(next_tag)
    _write_json(STATE_FILE, state)

    return _scene_to_response(next_tag, story)

# HTTP wrappers required by tests (/choice) & old front-end (/choose)
@app.post("/choice",  response_model=SceneResponse)
@app.post("/choose", response_model=SceneResponse)
def api_choose(req: ChoiceRequest = Body(...)) -> SceneResponse:        # noqa: D401
    try:
        return _choose_py(req)
    except KeyError as exc:                                             # → 400
        raise HTTPException(status_code=400, detail=str(exc)) from exc

# ─────────────────────────── trust & reset ───────────────────────────────────
@app.get("/trust")
def api_trust(soulSeedId: str) -> dict[str, float]:
    st = _read_json(STATE_FILE, {"trust": {}}).get("trust", {})
    return {"trust": float(st.get(soulSeedId, 0))}

def _reset(soul_seed_id: str) -> None:
    state = _read_json(STATE_FILE, {"soulMap": {}})
    state["soulMap"].pop(soul_seed_id, None)
    _write_json(STATE_FILE, state)

@app.post("/reset")
def api_reset(soulSeedId: str | None = Form(default=None)) -> dict[str, bool]:
    if soulSeedId is None:                                             # tests expect 404
        raise HTTPException(404, "Missing soulSeedId")
    _reset(soulSeedId)
    return {"reset": True}

# ───────────────────── tiny HTML editor (optional) ───────────────────────────
@app.get("/editor", response_class=HTMLResponse)
def story_editor() -> HTMLResponse:
    if EDITOR_FILE.exists():
        return HTMLResponse(EDITOR_FILE.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Story Editor placeholder</h1>")
