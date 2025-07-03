# backend/main.py
"""
central FastAPI app for SoulSeed
"""

# 1️⃣ Future import must come first
from __future__ import annotations

# 2️⃣ Load env vars from both `.env.cursor` (committed) and `.env` (secret)
from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env.cursor", override=False)  # safe dummy values for Cursor
load_dotenv(BASE_DIR / ".env", override=True)           # your actual local secrets

# 3️⃣ Standard lib
import hashlib
import json
import re
import sys
from typing import Any, Union, Dict

# 4️⃣ Third-party libs
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, constr

# ─── Path patching for internal modules ────────────────────────────────────────
REPO_ROOT = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(REPO_ROOT))

import ritual
from purpose_agents.generate_story import generate_story
from purpose_agents.codex_router import codex_router
print(f"[DEBUG] codex_router id at import: {id(codex_router)}")
import soulmap
from backend.npc import router as npc_router
from backend.repository_router import router as repository_router
from backend.media.models import MediaAssets

# ─── File paths ───────────────────────────────────────────────────────────────
DATA_FILE   = BASE_DIR / "player_profile.json"
STORY_FILE  = BASE_DIR / "story.json"
STATE_FILE  = BASE_DIR / "player_state.json"
EDITOR_FILE = BASE_DIR / "editor.html"
UPLOADS_DIR = BASE_DIR.parent / "uploads"

app = FastAPI(title="SoulSeed API")
app.include_router(soulmap.router, prefix='/soulmap')
app.include_router(npc_router, prefix='/npc')
app.include_router(repository_router, prefix='/repository')
app.mount("/static", StaticFiles(directory=UPLOADS_DIR, check_dir=False), name="static")

if not os.environ.get("TESTING"):
    @app.on_event("startup")
    async def _init() -> None:
        print("🔧 [main] startup: initializing ritual subsystem")
        await ritual.setup()


JSONDict = Dict[str, Any]

def _read_json(path: Union[str, Path], fallback: JSONDict) -> JSONDict:
    if not path:
        return fallback
    path_str = str(path) if path is not None else ""
    if not path_str:
        return fallback
    p = Path(path_str)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")) or fallback
        except json.JSONDecodeError:
            print(f"⚠️ [main] JSON decode failed for {path}, using fallback")
            return fallback
    return fallback


def _write_json(path: Union[str, Path], data: JSONDict) -> None:
    if not path:
        return
    path_str = str(path) if path is not None else ""
    if not path_str:
        return
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

_slug_re = re.compile(r"[^a-z0-9]+")

def slugify(value: str) -> str:
    return _slug_re.sub("-", value.lower()).strip("-")

def make_soul_seed_id(player_name: str, archetype: str) -> str:
    raw = f"{player_name}|{archetype}"
    sid = hashlib.sha256(raw.encode()).hexdigest()[:12]
    print(f"🆔 [main] generated soulSeedId={sid} from {raw}")
    return sid


# ─── Models ────────────────────────────────────────────────────────────────────
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
    choiceTag:  Union[str, int] | None = Field(default=None, alias="choiceTag")
    tag:        Union[str, int] | None = Field(default=None, alias="tag")
    choice:     Union[str, int] | None = Field(default=None, alias="choice")
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @property
    def choice_val(self) -> Union[str, int]:
        val = (
            self.choiceTag
            if self.choiceTag is not None
            else (self.tag if self.tag is not None else self.choice)
        )
        if val is None:
            raise ValueError("No choice value provided")
        return val

# Move model_rebuild() calls here, after all model classes are defined
PlayerProfileIn.model_rebuild()
SoulSeedResponse.model_rebuild()
RitualRequest.model_rebuild()
RitualResponse.model_rebuild()
StartRequest.model_rebuild()
ChoiceRequest.model_rebuild()



class SceneResponse(BaseModel):
    sceneTag: str
    text: str
    choices: list[dict[str, str]]
    media: MediaAssets = Field(default_factory=MediaAssets)

# ────────────────────────────── Core Endpoints ──────────────────────────────
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
        # Ensure intentVector is a list of floats
        intent_vector = [float(x) for x in data["intentVector"]]
        first_tag, tree = await generate_story(
            payload.playerId,
            str(data["theme"]),
            intent_vector,
        )
    except Exception as e:
        print(f"⚠️ [main] story generation failed: {e}")
        raise HTTPException(500, "Failed to generate story tree")

    # Load player profile to get soulSeedId
    profiles = _read_json(DATA_FILE, {})
    soul_seed_id = None
    for pid, profile in profiles.items():
        if pid == payload.playerId:
            soul_seed_id = profile.get("soulSeedId")
            break
    if not soul_seed_id:
        print(f"⚠️ [main] soulSeedId not found for playerId={payload.playerId}")
        raise HTTPException(500, "Failed to find soulSeedId for player")

    state = _read_json(STATE_FILE, {"stories": {}})
    if "stories" not in state:
        state["stories"] = {}
    state["stories"][soul_seed_id] = {"tree": tree, "current": first_tag}
    _write_json(STATE_FILE, state)

    # Enqueue media generation for the first scene
    print(f"[DEBUG] codex_router id in /ritual endpoint: {id(codex_router)}")
    try:
        first_scene = tree.get(first_tag, {})
        scene_text = first_scene.get("text", "")
        await codex_router.enqueue_media_generation(
            scene_tag=first_tag,
            scene_text=scene_text,
            theme=str(data["theme"]),
            player_id=payload.playerId
        )
    except Exception as e:
        print(f"⚠️ [main] Media generation enqueue failed: {e}")

    print(f"✅ [main] /ritual returning nextSceneTag={first_tag}")
    return RitualResponse(
        theme=str(data["theme"]),
        intentVector=[float(x) for x in data["intentVector"]],
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


def _scene_to_response(tag: str, story: dict, player_id: str = "") -> SceneResponse:
    print(f"DEBUG: _scene_to_response called with tag={tag}, story keys={list(story.keys())}")
    if tag not in story:
        return SceneResponse(
            sceneTag=tag,
            text="The story ends here.",
            choices=[],
            media=MediaAssets()
        )
    scene = story[tag]
    choices = [
        {"tag": str(k), "label": v.get("text", "").replace("_", " ").title() if isinstance(v, dict) else str(v)}
        for k, v in scene.get("choices", {}).items()
    ]
    
    # Always ensure media field is present
    media = MediaAssets()
    
    # Try to get generated media from CodexRouter first
    if player_id:
        print(f"[DEBUG] Checking codex_router for scene {tag} with player_id {player_id}")
        result = codex_router.check_scene_media(tag, player_id)
        if result and result.success:
            print(f"[DEBUG] Found generated media for scene {tag}: {result.media}")
            media = result.media
        else:
            print(f"[DEBUG] No generated media found, checking scene data for {tag}")
            # Fall back to scene media data if available
            media_data = scene.get("media")
            if media_data and isinstance(media_data, dict):
                media = MediaAssets(
                    images=media_data.get("images", []),
                    audio=media_data.get("audio", [])
                )
                print(f"[DEBUG] Using scene media data: {media}")
    else:
        print(f"[DEBUG] No player_id, using static story media for {tag}")
        # For static story, try to get media data from scene
        media_data = scene.get("media")
        if media_data and isinstance(media_data, dict):
            media = MediaAssets(
                images=media_data.get("images", []),
                audio=media_data.get("audio", [])
            )
            print(f"[DEBUG] Using static story media: {media}")
    
    print(f"[DEBUG] Final media for scene {tag}: {media}")
    
    return SceneResponse(sceneTag=tag, text=scene.get("text", ""), choices=choices, media=media)

# ───────────────────────── ritual endpoint ─────────────────────────────────
@app.post("/start", response_model=SceneResponse)
async def api_start(req: StartRequest) -> SceneResponse:
    print(f"▶️ [main] /start called with soulSeedId={req.soulSeedId}")
    state = _read_json(str(STATE_FILE), {"stories": {}})
    st = state["stories"].get(req.soulSeedId)

    if st:
        print("✅ [main] using dynamic story tree")
        # Get player_id from soulSeedId (reverse lookup)
        profiles = _read_json(str(DATA_FILE), {})
        player_id = ""
        for pid, profile in profiles.items():
            if profile.get("soulSeedId") == req.soulSeedId:
                player_id = pid
                break
        current_tag = st["current"]
        current_scene = st["tree"].get(current_tag, {})
        media_data = current_scene.get("media", {})
        generate_images = not media_data.get("images")
        generate_audio = not media_data.get("audio")
        if generate_images or generate_audio:
            try:
                scene_text = current_scene.get("text", "")
                # --- DEV ONLY: Await media generation so response includes image URL ---
                # NOTE: For production, revert to async background task and use polling or websockets for updates.
                await codex_router.enqueue_media_generation(
                    scene_tag=current_tag,
                    scene_text=scene_text,
                    theme="hero's journey",  # Or fetch from state if available
                    player_id=player_id,
                    generate_images=generate_images,
                    generate_audio=generate_audio
                )
                print(f"[main] Synchronously generated media for /start scene {current_tag}")
            except Exception as e:
                print(f"[main] Failed to synchronously generate media in /start: {e}")
        return _scene_to_response(current_tag, st["tree"], player_id=player_id)

    print("⚠️ [main] falling back to static story.json")
    story = _read_json(str(STORY_FILE), {})
    return _scene_to_response("intro_001", story, player_id="")


def patch_story_tree(story_dict):
    """
    Recursively add all referenced tags as default nodes until all are present.
    """
    added = True
    iteration = 0
    while added:
        iteration += 1
        referenced = set()
        for node in story_dict.values():
            for ch in node.get("choices", {}).values():
                if isinstance(ch, dict) and "next" in ch:
                    referenced.add(ch["next"])
        missing = referenced - set(story_dict.keys())
        if missing:
            print(f"[patch_story_tree] Iter {iteration}: Adding missing tags: {missing}")
            for tag in missing:
                story_dict[tag] = {"text": "The story ends here.", "choices": {}, "media": {"images": [], "audio": []}}
        else:
            added = False
    print(f"[patch_story_tree] Final story keys: {list(story_dict.keys())}")
    return story_dict


async def _choose_py(req: ChoiceRequest) -> SceneResponse:
    print(f"▶️ [main] choose({req.soulSeedId}, {req.sceneTag}, choice={req.choice_val})")
    state = _read_json(str(STATE_FILE), {"stories": {}})
    story_data = state["stories"].get(req.soulSeedId)

    if story_data is None:
        raise HTTPException(404, "No story tree found for this player")

    tree = story_data["tree"]
    if tree and isinstance(tree, dict):
        tree = patch_story_tree(tree)
        story_data["tree"] = tree
    scene = tree.get(req.sceneTag)
    if scene is None:
        raise HTTPException(404, f"Scene '{req.sceneTag}' not found")

    str_key_map = {str(k): v["next"] for k, v in scene.get("choices", {}).items()}
    key = str(req.choice_val)
    if key not in str_key_map:
        raise HTTPException(400, f"Choice '{key}' not found in scene choices")
    next_tag = str_key_map[key]
    print(f"✅ [main] next sceneTag={next_tag}")
    # Defensive patch again in case new tags are referenced
    tree = patch_story_tree(tree)
    story_data["tree"] = tree
    # Update state
    story_data["current"] = next_tag
    # --- NPC trust delta integration ---
    choice_obj = scene.get("choices", {}).get(key, {})
    trust_delta = 0.0
    if isinstance(choice_obj, dict):
        trust_delta = float(choice_obj.get("trust_delta", 0.0))
    if trust_delta != 0.0:
        try:
            from backend.npc.service import apply_trust
            from backend.db import SessionLocal
            db = SessionLocal()
            apply_trust(req.soulSeedId, npc_id="companion", delta=trust_delta, db=db)
            db.close()
        except Exception as e:
            print(f"[main] NPC trust update failed: {e}")
    # --- END NPC trust delta integration ---
    _write_json(str(STATE_FILE), state)
    
    # Enqueue media generation for the next scene
    print(f"[DEBUG] codex_router id in /choose endpoint: {id(codex_router)}")
    try:
        next_scene = tree.get(next_tag, {})
        scene_text = next_scene.get("text", "")
        # Get player_id from soulSeedId (reverse lookup)
        profiles = _read_json(str(DATA_FILE), {})
        player_id = ""
        for pid, profile in profiles.items():
            if profile.get("soulSeedId") == req.soulSeedId:
                player_id = pid
                break
        await codex_router.enqueue_media_generation(
            scene_tag=next_tag,
            scene_text=scene_text,
            theme="hero's journey",  # Simplified - would need to store theme
            player_id=player_id
        )
    except Exception as e:
        print(f"⚠️ [main] Media generation enqueue failed: {e}")
    
    return _scene_to_response(next_tag, tree, player_id=player_id)

# ────────────────────────────── choice endpoint ──────────────────────────────
@app.post("/choice", response_model=SceneResponse)
@app.post("/choose", response_model=SceneResponse)
async def api_choose(req: ChoiceRequest = Body(...)) -> SceneResponse:
    try:
        return await _choose_py(req)
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
    state = _read_json(STATE_FILE, {"stories": {}})
    state["stories"].pop(soulSeedId, None)
    _write_json(STATE_FILE, state)
    return {"reset": True}


@app.get("/editor", response_class=HTMLResponse)
def story_editor() -> HTMLResponse:
    if EDITOR_FILE.exists():
        return HTMLResponse(EDITOR_FILE.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Story Editor placeholder</h1>")


# ─── Media Endpoints ────────────────────────────────────────────────────────────
@app.get("/media/status/{task_id}")
def get_media_status(task_id: str) -> dict[str, str]:
    """Get the status of a media generation task"""
    status = codex_router.get_task_status(task_id)
    return {"task_id": task_id, "status": status.value if status else "not_found"}


@app.get("/media/result/{task_id}")
def get_media_result(task_id: str) -> dict[str, Any]:
    """Get the result of a completed media generation task"""
    result = codex_router.get_task_result(task_id)
    if result:
        return result.dict()
    else:
        raise HTTPException(404, "Task not found or not completed")
