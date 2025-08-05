# backend/main.py
"""
central FastAPI app for SoulSeed
"""

# 1️⃣ Future import must come first
from __future__ import annotations

# 2️⃣ Load settings from Pydantic BaseSettings
from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

# Import settings after setting up paths
sys.path.insert(0, str(BASE_DIR))
from settings import settings

# 3️⃣ Standard lib
from datetime import datetime
import hashlib
import json
import re
import sys
from typing import Any, Union, Dict, Optional, cast

# 4️⃣ Third-party libs
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, constr, ConfigDict

# ─── Path patching for internal modules ────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(REPO_ROOT))

import ritual
from purpose_agents.generate_story import generate_story
from purpose_agents.codex_router import codex_router
print(f"[DEBUG] codex_router id at import: {id(codex_router)}")
from npc import router as npc_router

# Import story validator
try:
    from codex.validate import validate, auto_heal
except ImportError:
    # Fallback for when validation module is not available
    def validate(tree):
        return []
    def auto_heal(tree, aggressive=False):
        return tree
from npc.profile_seed import ensure_npc_profile
from repository_router import router as repository_router
from media.models import MediaAssets
from emotion.router import router as emotion_router
from emotion.models import EMOTION_DIM, zero_emotion_vector, clip_emotion_vector
from purpose_agents.tasks import recap_builder
from codex.memory import update_memory as codex_update_memory
from codex.npc import generate_npc_dialogue
from codex.npc.npc_group_dialogue import generate_group_dialogue
from soulmap import router as soulmap_router

# ─── File paths ───────────────────────────────────────────────────────────────
DATA_FILE   = str(BASE_DIR / "player_profile.json")
STORY_FILE  = str(BASE_DIR / "story.json")
STATE_FILE  = str(BASE_DIR / "player_state.json")
EDITOR_FILE = BASE_DIR / "editor.html"
UPLOADS_DIR = BASE_DIR.parent / "uploads"

app = FastAPI(title="SoulSeed API")


app.include_router(soulmap_router, prefix="/v1")
app.include_router(npc_router, prefix='/npc')
app.include_router(repository_router, prefix='/repository')
app.include_router(emotion_router, prefix='')
app.mount("/static", StaticFiles(directory=UPLOADS_DIR, check_dir=False), name="static")

if not settings.testing:
    @app.on_event("startup")
    async def _init() -> None:
        print("🔧 [main] startup: initializing ritual subsystem")
        await ritual.setup()
        
        # Ensure soul map tables exist
        try:
            from soulmap.db import create_tables
            create_tables()
            print("✅ [main] startup: soul map tables created/verified")
        except Exception as e:
            print(f"⚠️ [main] startup: failed to create soul map tables: {e}")


JSONDict = Dict[str, Any]

def _read_json(path: str, fallback: JSONDict) -> JSONDict:
    if not path:
        return fallback
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")) or fallback
        except json.JSONDecodeError:
            print(f"⚠️ [main] JSON decode failed for {path}, using fallback")
            return fallback
    return fallback


def _write_json(path: str, data: JSONDict) -> None:
    if not path:
        return
    p = Path(path)
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
    playerName: str = Field(..., min_length=1)
    archetypePreset: str
    archetypeCustom: str | None = None

class SoulSeedResponse(BaseModel):
    playerId: str
    soulSeedId: str
    initSceneTag: str

class RitualRequest(BaseModel):
    playerId: str
    askText: str = Field(..., max_length=280)
    seekText: str = Field(..., max_length=280)
    knockText: str = Field(..., max_length=280)
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
    npc_text_dynamic: str | None = None
    npc_dialogue: list[dict[str, str]] = Field(default_factory=list)
    dialogue_type: str = "single"  # "single" or "group"
    soulmap_delta: dict[str, float] | None = None

SceneResponse.model_rebuild()

# ─────────────────────────────── Core Endpoints ───────────────────────────────
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

    # Load player profile to get player name and soulSeedId
    profiles = _read_json(str(DATA_FILE), {})
    player_name = None
    soul_seed_id = None
    for pid, profile in profiles.items():
        if pid == payload.playerId:
            player_name = profile.get("playerName", "Adventurer")  # Fallback name
            soul_seed_id = profile.get("soulSeedId")
            break
    
    if not soul_seed_id:
        print(f"⚠️ [main] soulSeedId not found for playerId={payload.playerId}")
        raise HTTPException(500, "Failed to find soulSeedId for player")

    try:
        # Ensure intentVector is a list of floats
        intent_vector = [float(x) for x in data["intentVector"]]
        first_tag, tree = await generate_story(
            payload.playerId,
            player_name,  # Pass the actual player name
            str(data["theme"]),
            intent_vector,
        )
    except Exception as e:
        print(f"⚠️ [main] story generation failed: {e}")
        raise HTTPException(500, "Failed to generate story tree")

    state = _read_json(str(STATE_FILE), {"stories": {}})
    if "stories" not in state:
        state["stories"] = {}
    state["stories"][soul_seed_id] = {"tree": tree, "current": first_tag, "history": [first_tag]}
    _write_json(str(STATE_FILE), state)

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

    profiles = _read_json(str(DATA_FILE), {})
    profiles[player_id] = {
        "playerName": payload.playerName,
        "archetype": archetype,
        "soulSeedId": soul_seed_id,
    }
    _write_json(str(DATA_FILE), profiles)
    print(f"✅ [main] saved profile for player={player_id}")

    # Auto-create a zero-vector soul map for the new player
# #     try:
#         # from soulmap.models import SoulMap
#         from db import SessionLocal
#         db = SessionLocal()
#         # Check if a soul map already exists for this player
#         existing = db.query(SoulMap).filter_by(player_id=player_id).first()
#         if not existing:
#             zero_vec = [0.0] * 64
#             new_row = SoulMap(player_id=player_id, vector=zero_vec)
#             db.add(new_row)
#             db.commit()
#         db.close()
#         print(f"✅ [main] created zero-vector soul map for player={player_id}")
#     except Exception as e:
#        print(f"⚠️ [main] failed to create soul map for player={player_id}: {e}")

    return SoulSeedResponse(
        playerId=player_id,
        soulSeedId=soul_seed_id,
        initSceneTag="intro_001",
    )


def _scene_to_response(tag: str, story: dict, player_id: str = "", story_data: Optional[Dict[str, Any]] = None, soulmap_delta: Optional[Dict[str, float]] = None) -> SceneResponse:
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
    
    # Generate dynamic NPC dialogue if player_id is available
    npc_text_dynamic = None
    npc_dialogue = []
    dialogue_type = "single"
    
    if player_id:
        # Check for recruitment dialogue first (priority over regular dialogue)
        recruitment_dialogue = None
        if story_data:
            recruitment_dialogues = story_data.get("recruitment_dialogue", [])
            # Find recruitment dialogue for this scene
            for dialogue_entry in recruitment_dialogues:
                if dialogue_entry.get("scene_tag") == tag:
                    recruitment_dialogue = dialogue_entry.get("dialogue")
                    print(f"[DEBUG] Found recruitment dialogue for scene {tag}: {recruitment_dialogue}")
                    break
        
        if recruitment_dialogue:
            npc_text_dynamic = recruitment_dialogue
            npc_dialogue = [{"npc_id": "recruitment", "text": recruitment_dialogue}]
            dialogue_type = "single"
        else:
            try:
                # Get NPCs present in scene
                npcs_present = scene.get("npcs_present", [])
                
                # INTEGRATION: Use dynamic NPC scene integration
                try:
                    from npc.scene_integration import get_scene_npcs
                    
                    # Get dynamically assigned NPCs for this scene
                    dynamic_npcs = get_scene_npcs(player_id, tag)
                    
                    # Use dynamic NPCs if available, otherwise fall back to story NPCs
                    if dynamic_npcs:
                        npcs_present = dynamic_npcs
                        print(f"[DEBUG] Using dynamic NPCs for scene {tag}: {npcs_present}")
                    else:
                        print(f"[DEBUG] Using story NPCs for scene {tag}: {npcs_present}")
                    
                    # Ensure NPC profiles exist for all present NPCs
                    if npcs_present:
                        try:
                            from npc.profile_seed import ensure_npc_profile
                            ensure_npc_profile(scene, player_id)
                            print(f"[DEBUG] Ensured NPC profiles for scene {tag}")
                        except Exception as e:
                            print(f"[DEBUG] Failed to ensure NPC profiles: {e}")
                            
                except Exception as e:
                    print(f"[DEBUG] Failed to get dynamic NPCs, using fallback: {e}")
                    # Continue with existing npcs_present logic
                
                # If no npcs_present defined, check if there are active companions
                if not npcs_present:
                    try:
                        from npc.service import get_companions
                        from db import SessionLocal
                        db = SessionLocal()
                        companions = get_companions(player_id, db)
                        npcs_present = [comp.id for comp in companions[:3]]  # Limit to 3
                        db.close()
                        print(f"[DEBUG] Found active companions for scene: {npcs_present}")
                    except Exception as e:
                        print(f"[DEBUG] Failed to get active companions: {e}")
                        npcs_present = []
                
                # Generate group dialogue if multiple NPCs present
                if len(npcs_present) > 1:
                    try:
                        from npc.service import get_trust_scores
                        from emotion.service import get_emotion_vector
                        from db import SessionLocal
                        
                        db = SessionLocal()
                        trust_scores = get_trust_scores(player_id, db)
                        emotion_vector = get_emotion_vector(player_id)
                        npc_metadata = story.get("_npc_metadata", {})
                        scene_context = scene.get("text", "")
                        
                        # Generate group dialogue
                        dialogue_entries = generate_group_dialogue(
                            npcs_present=npcs_present,
                            player_id=player_id,
                            scene_context=scene_context,
                            trust_scores=trust_scores,
                            emotion_vector=emotion_vector,
                            npc_metadata=npc_metadata
                        )
                        
                        db.close()
                        
                        if dialogue_entries:
                            npc_dialogue = dialogue_entries
                            dialogue_type = "group" if len(dialogue_entries) > 1 else "single"
                            # Set npc_text_dynamic to first dialogue for backward compatibility
                            npc_text_dynamic = dialogue_entries[0]["text"] if dialogue_entries else None
                            print(f"[DEBUG] Generated group dialogue with {len(dialogue_entries)} entries")
                        else:
                            # Fallback to single NPC dialogue
                            npc_id = npcs_present[0] if npcs_present else "companion-001"
                            npc_text_dynamic = generate_npc_dialogue(npc_id, player_id)
                            npc_dialogue = [{"npc_id": npc_id, "text": npc_text_dynamic}] if npc_text_dynamic else []
                            dialogue_type = "single"
                        
                    except Exception as e:
                        print(f"[DEBUG] Failed to generate group dialogue: {e}")
                        # Fallback to single NPC dialogue
                        npc_id = npcs_present[0] if npcs_present else "companion-001"
                        npc_text_dynamic = generate_npc_dialogue(npc_id, player_id)
                        npc_dialogue = [{"npc_id": npc_id, "text": npc_text_dynamic}] if npc_text_dynamic else []
                        dialogue_type = "single"
                        
                elif len(npcs_present) == 1:
                    # Single NPC dialogue
                    npc_id = npcs_present[0]
                    npc_text_dynamic = generate_npc_dialogue(npc_id, player_id)
                    npc_dialogue = [{"npc_id": npc_id, "text": npc_text_dynamic}] if npc_text_dynamic else []
                    dialogue_type = "single"
                    print(f"[DEBUG] Generated single NPC dialogue for {npc_id}")
                else:
                    # No NPCs present, no dialogue
                    npc_text_dynamic = None
                    npc_dialogue = []
                    dialogue_type = "single"
                    print(f"[DEBUG] No NPCs present in scene {tag}")
                    
            except Exception as e:
                print(f"[DEBUG] Failed to generate NPC dialogue: {e}")
                npc_text_dynamic = None
                npc_dialogue = []
                dialogue_type = "single"
    
    return SceneResponse(
        sceneTag=tag, 
        text=scene.get("text", ""), 
        choices=choices, 
        media=media,
        npc_text_dynamic=npc_text_dynamic,
        npc_dialogue=npc_dialogue,
        dialogue_type=dialogue_type,
        soulmap_delta=soulmap_delta
    )

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
                task_id = await codex_router.enqueue_media_generation(
                    scene_tag=current_tag,
                    scene_text=scene_text,
                    theme="hero's journey",  # Or fetch from state if available
                    player_id=player_id,
                    generate_images=generate_images,
                    generate_audio=generate_audio
                )
                print(f"[main] Synchronously generated media for /start scene {current_tag}, task_id={task_id}")
                
                # Wait for the task to complete and get the result
                import asyncio
                max_wait = 30  # Maximum wait time in seconds
                wait_time = 0
                while wait_time < max_wait:
                    result = codex_router.get_task_result(task_id)
                    if result and result.success:
                        print(f"[main] Media generation completed for scene {current_tag}: {result.media}")
                        break
                    await asyncio.sleep(0.5)
                    wait_time += 0.5
                    print(f"[main] Waiting for media generation... ({wait_time}s)")
                
                if wait_time >= max_wait:
                    print(f"[main] Media generation timeout for scene {current_tag}")
                    
            except Exception as e:
                print(f"[main] Failed to synchronously generate media in /start: {e}")
        
        # Ensure NPC profiles exist for all NPCs in the scene
        if player_id and current_scene:
            try:
                ensure_npc_profile(current_scene, player_id)
            except Exception as e:
                print(f"[main] Failed to ensure NPC profiles in /start: {e}")
        
        return _scene_to_response(current_tag, st["tree"], player_id=player_id)

    print("⚠️ [main] falling back to static story.json")
    story = _read_json(str(STORY_FILE), {})
    return _scene_to_response("intro_001", story, player_id="")


def patch_story_tree(story_dict, player_name: str = "Adventurer"):
    """
    Recursively add all referenced tags as meaningful continuing nodes until all are present.
    This ensures stories continue for ~8 scenes before reaching conclusions.
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
                # Extract tag number for intelligent patching
                tag_num = 0
                if '_' in tag:
                    try:
                        tag_num = int(tag.split('_')[1])
                    except (IndexError, ValueError):
                        tag_num = len(story_dict) + 1
                else:
                    tag_num = len(story_dict) + 1
                
                # Create meaningful continuing scenes for the first 6-7 nodes
                if tag_num <= 7:
                    # Generate next progression tags
                    next_tag = f"tag_{tag_num + 1:03d}" if tag_num < 8 else None
                    alt_tag = f"tag_{tag_num + 2:03d}" if tag_num < 7 else None
                    
                    # Create choices that continue the adventure
                    choices = {}
                    if next_tag and tag_num < 6:
                        choices["1"] = {
                            "text": "Continue deeper into the adventure",
                            "next": next_tag,
                            "trust_delta": 0.1
                        }
                    if alt_tag and tag_num < 6:
                        choices["2"] = {
                            "text": "Take a different approach to the challenge",
                            "next": alt_tag,
                            "trust_delta": 0.1
                        }
                    elif tag_num >= 6:
                        # For later nodes, create choices leading to conclusions
                        choices["1"] = {
                            "text": "Face the final challenge with courage",
                            "next": f"tag_{8:03d}",
                            "trust_delta": 0.2
                        }
                        choices["2"] = {
                            "text": "Seek wisdom before the final confrontation", 
                            "next": f"tag_{9:03d}",
                            "trust_delta": 0.15
                        }
                    
                    story_dict[tag] = {
                        "text": f"{player_name}, your journey continues as new challenges and discoveries await. Each step forward brings you closer to your ultimate destiny, testing your resolve and revealing hidden strengths.",
                        "choices": choices,
                        "media": {"images": [], "audio": []},
                        "npcs_present": []
                    }
                else:
                    # Create conclusion nodes for tag_008 and beyond
                    story_dict[tag] = {
                        "text": f"{player_name}, your epic adventure reaches its triumphant conclusion. Through courage, wisdom, and determination, you have overcome all obstacles and achieved your goal. Your heroic deeds will be remembered for generations to come. The End.",
                        "choices": {},
                        "media": {"images": [], "audio": []},
                        "npcs_present": []
                    }
        else:
            added = False
    print(f"[patch_story_tree] Final story keys: {list(story_dict.keys())}")
    return story_dict


async def _choose_py(req: ChoiceRequest) -> SceneResponse:
    print(f"🟢 [main] Entered _choose_py for soulSeedId={req.soulSeedId}, sceneTag={req.sceneTag}, choice={req.choice_val}", flush=True)
    state = _read_json(str(STATE_FILE), {"stories": {}})
    story_data = state["stories"].get(req.soulSeedId)

    if story_data is None:
        raise HTTPException(404, "No story tree found for this player")

    # Get player_id and player_name from soulSeedId for NPC profile creation
    profiles = _read_json(str(DATA_FILE), {})
    player_id = ""
    player_name = "Adventurer"  # Default fallback
    for pid, profile in profiles.items():
        if profile.get("soulSeedId") == req.soulSeedId:
            player_id = pid
            player_name = profile.get("playerName", "Adventurer")
            break
    
    tree = story_data["tree"]
    if tree and isinstance(tree, dict):
        tree = patch_story_tree(tree, player_name)
        story_data["tree"] = tree
    scene = tree.get(req.sceneTag)
    if scene is None:
        raise HTTPException(404, f"Scene '{req.sceneTag}' not found")
    
    # Ensure NPC profiles exist for all NPCs in the scene
    if player_id and scene:
        try:
            ensure_npc_profile(scene, player_id)
        except Exception as e:
            print(f"[main] Failed to ensure NPC profiles in _choose_py: {e}")

    str_key_map = {str(k): v["next"] for k, v in scene.get("choices", {}).items()}
    key = str(req.choice_val)
    if key not in str_key_map:
        raise HTTPException(400, f"Choice '{key}' not found in scene choices")
    next_tag = str_key_map[key]
    print(f"✅ [main] next sceneTag={next_tag}", flush=True)
    # Defensive patch again in case new tags are referenced
    tree = patch_story_tree(tree, player_name)
    story_data["tree"] = tree
    # Update state
    story_data["current"] = next_tag
    # Update history
    if "history" not in story_data or not isinstance(story_data["history"], list):
        story_data["history"] = []
    story_data["history"].append(next_tag)
    # --- NPC trust delta integration (Multi-NPC Support) ---
    choice_obj = scene.get("choices", {}).get(key, {})
    
    # Handle legacy single trust_delta (backward compatibility)
    legacy_trust_delta = 0.0
    if isinstance(choice_obj, dict):
        legacy_trust_delta = float(choice_obj.get("trust_delta", 0.0))
    
    # Handle new multi-NPC trust deltas
    npc_trust_deltas = {}
    if isinstance(choice_obj, dict) and "npc_trust_deltas" in choice_obj:
        npc_trust_deltas = choice_obj.get("npc_trust_deltas", {})
    
    # Apply trust deltas
    if legacy_trust_delta != 0.0 or npc_trust_deltas:
        try:
            from npc.service import apply_trust, apply_trust_to_multiple
            from db import SessionLocal
            db = SessionLocal()
            
            # Apply legacy trust delta to default companion
            if legacy_trust_delta != 0.0:
                # Generate consistent UUID for default companion
                import uuid
                companion_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{req.soulSeedId}:companion")
                apply_trust(req.soulSeedId, str(companion_uuid), legacy_trust_delta, db)
                print(f"[main] Applied legacy trust delta {legacy_trust_delta} to companion")
            
            # Apply multi-NPC trust deltas
            if npc_trust_deltas:
                apply_trust_to_multiple(req.soulSeedId, npc_trust_deltas, db)
                print(f"[main] Applied multi-NPC trust deltas: {npc_trust_deltas}")
            
            db.close()
        except Exception as e:
            print(f"[main] NPC trust update failed: {e}")
    # --- END NPC trust delta integration ---

    # --- NPC Onboarding integration with Conditions ---
    print(f"🔍 [main] Starting NPC onboarding integration for soulSeedId={req.soulSeedId}", flush=True)
    try:
        # Check if npc_onboard is present in choice
        if isinstance(choice_obj, dict) and "npc_onboard" in choice_obj:
            npc_onboard_id = choice_obj.get("npc_onboard")
            if npc_onboard_id and player_id:
                print(f"🟢 [main] Attempting to onboard NPC: {npc_onboard_id} for player: {player_id}", flush=True)
                
                # Import here to avoid circular imports
                from npc.service import onboard_npc
                from db import SessionLocal
                from story_conditions import validate_choice_conditions
                
                db = SessionLocal()
                try:
                    # Check if choice has conditions that must be validated
                    conditions = choice_obj.get("conditions", {})
                    
                    # Always add anti-duplicate condition for onboarding
                    if "not_companion" not in conditions:
                        conditions["not_companion"] = True
                    
                    if conditions:
                        print(f"🔍 [main] Validating onboarding conditions: {conditions}", flush=True)
                        is_valid, reason = validate_choice_conditions(conditions, player_id, npc_onboard_id, db)
                        
                        if not is_valid:
                            print(f"❌ [main] Onboarding conditions not met: {reason}", flush=True)
                            # Store condition failure for potential UI feedback
                            story_data["last_condition_failure"] = {
                                "npc_id": npc_onboard_id,
                                "reason": reason,
                                "scene_tag": req.sceneTag
                            }
                            # Continue without onboarding, but don't fail the choice
                        else:
                            print(f"✅ [main] Onboarding conditions validated: {reason}", flush=True)
                            onboarded_npc = onboard_npc(player_id, npc_onboard_id, db)
                            print(f"✅ [main] Successfully onboarded {onboarded_npc.name} (ID: {onboarded_npc.id}) as companion", flush=True)
                            
                            # Generate recruitment dialogue
                            try:
                                from codex.npc.recruitment_dialogue import generate_recruitment_dialogue
                                from npc.service import get_trust_scores
                                
                                trust_scores = get_trust_scores(player_id, db)
                                npc_trust = trust_scores.get(npc_onboard_id, 0.5)
                                context = "emergency" if conditions.get("trust", 1.0) < 0.4 else None
                                
                                # Try to get NPC personality from story metadata
                                npc_personality = None
                                npc_metadata = tree.get("_npc_metadata", {})
                                for npc_data in npc_metadata.values():
                                    if npc_data.get("uuid") == npc_onboard_id:
                                        npc_personality = npc_data.get("personality")
                                        break
                                
                                recruitment_dialogue = generate_recruitment_dialogue(
                                    npc_onboard_id, 
                                    onboarded_npc.name, 
                                    npc_trust, 
                                    context,
                                    npc_personality
                                )
                                
                                # Store recruitment dialogue for scene response
                                story_data.setdefault("recruitment_dialogue", []).append({
                                    "npc_id": npc_onboard_id,
                                    "npc_name": onboarded_npc.name,
                                    "dialogue": recruitment_dialogue,
                                    "scene_tag": req.sceneTag
                                })
                                
                                print(f"🎭 [main] Generated recruitment dialogue: {recruitment_dialogue}", flush=True)
                                
                            except Exception as e:
                                print(f"⚠️ [main] Failed to generate recruitment dialogue: {e}", flush=True)
                            
                            # Log onboarding event for memory recap
                            story_data.setdefault("onboarding_events", []).append({
                                "npc_id": npc_onboard_id,
                                "npc_name": onboarded_npc.name,
                                "scene_tag": req.sceneTag,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                    else:
                        # No conditions to validate, proceed with onboarding
                        onboarded_npc = onboard_npc(player_id, npc_onboard_id, db)
                        print(f"✅ [main] Successfully onboarded {onboarded_npc.name} (ID: {onboarded_npc.id}) as companion", flush=True)
                        
                        # Generate recruitment dialogue
                        try:
                            from codex.npc.recruitment_dialogue import generate_recruitment_dialogue
                            from npc.service import get_trust_scores
                            
                            trust_scores = get_trust_scores(player_id, db)
                            npc_trust = trust_scores.get(npc_onboard_id, 0.5)
                            
                            # Try to get NPC personality from story metadata
                            npc_personality = None
                            npc_metadata = tree.get("_npc_metadata", {})
                            for npc_data in npc_metadata.values():
                                if npc_data.get("uuid") == npc_onboard_id:
                                    npc_personality = npc_data.get("personality")
                                    break
                            
                            recruitment_dialogue = generate_recruitment_dialogue(
                                npc_onboard_id, 
                                onboarded_npc.name, 
                                npc_trust,
                                None,  # No emergency context
                                npc_personality
                            )
                            
                            # Store recruitment dialogue for scene response
                            story_data.setdefault("recruitment_dialogue", []).append({
                                "npc_id": npc_onboard_id,
                                "npc_name": onboarded_npc.name,
                                "dialogue": recruitment_dialogue,
                                "scene_tag": req.sceneTag
                            })
                            
                            print(f"🎭 [main] Generated recruitment dialogue: {recruitment_dialogue}", flush=True)
                            
                        except Exception as e:
                            print(f"⚠️ [main] Failed to generate recruitment dialogue: {e}", flush=True)
                        
                        # Log onboarding event for memory recap
                        story_data.setdefault("onboarding_events", []).append({
                            "npc_id": npc_onboard_id,
                            "npc_name": onboarded_npc.name,
                            "scene_tag": req.sceneTag,
                            "timestamp": datetime.utcnow().isoformat() 
                        })
                        
                finally:
                    db.close()
            elif not player_id:
                print(f"⚠️ [main] Cannot onboard NPC {npc_onboard_id}: no player_id found", flush=True)
    except Exception as e:
        print(f"⚠️ [main] NPC onboarding failed: {e}", flush=True)
        import traceback
        print(f"⚠️ [main] NPC onboarding traceback: {traceback.format_exc()}", flush=True)
    # --- END NPC Onboarding integration ---

    # --- Emotion delta integration ---
    print(f"🔍 [main] Starting emotion integration for soulSeedId={req.soulSeedId}", flush=True)
    try:
        # Find player_id from soulSeedId
        profiles = _read_json(str(DATA_FILE), {})
        print(f"🔍 [main] Looking for player_id with soulSeedId={req.soulSeedId}", flush=True)
        print(f"🔍 [main] Available profiles: {list(profiles.keys())}", flush=True)
        player_id = ""
        for pid, profile in profiles.items():
            print(f"🔍 [main] Checking profile {pid}: soulSeedId={profile.get('soulSeedId')}", flush=True)
            if profile.get("soulSeedId") == req.soulSeedId:
                player_id = pid
                print(f"✅ [main] Found player_id={player_id} for soulSeedId={req.soulSeedId}", flush=True)
                break
        if not player_id:
            print(f"⚠️ [main] No player_id found for soulSeedId={req.soulSeedId}", flush=True)
        if player_id:
            print(f"🔍 [main] Processing emotion for player_id={player_id}", flush=True)
            # Load emotion state
            emotion_path = os.path.join(os.path.dirname(__file__), "emotion_state.json")
            if os.path.exists(emotion_path):
                with open(emotion_path, "r") as f:
                    emotion_states = json.load(f)
            else:
                emotion_states = {}
            state_data = emotion_states.get(player_id, {"vector": zero_emotion_vector(), "log": []})
            vector = state_data.get("vector", zero_emotion_vector())
            log = state_data.get("log", [])
            # Get emotion_delta from choice_obj
            emotion_delta = zero_emotion_vector()
            if isinstance(choice_obj, dict) and "emotion_delta" in choice_obj:
                raw_delta = choice_obj["emotion_delta"]
                if isinstance(raw_delta, list) and len(raw_delta) == EMOTION_DIM:
                    emotion_delta = [float(x) for x in raw_delta]
            # Apply delta and clip
            new_vector = clip_emotion_vector([v + d for v, d in zip(vector, emotion_delta)])
            log.append({"sceneTag": req.sceneTag, "delta": emotion_delta})
            if len(log) > 50:
                log = log[-50:]
            # Save updated state
            emotion_states[player_id] = {"vector": new_vector, "log": log}
            with open(emotion_path, "w") as f:
                json.dump(emotion_states, f)
            print(f"✅ [main] Emotion integration completed for player_id={player_id}", flush=True)
    except Exception as e:
        print(f"⚠️ [main] Emotion integration failed: {e}", flush=True)
        import traceback
        print(f"⚠️ [main] Emotion integration traceback: {traceback.format_exc()}", flush=True)
        player_id = ""  # Reset player_id if emotion integration fails
    # --- END Emotion delta integration ---

    # --- Soulmap delta integration ---
    soulmap_delta = None
    if player_id and isinstance(choice_obj, dict):
        try:
            from soulmap.service import apply_delta
            from db import SessionLocal
            
            # Check if soulmap_delta is provided
            if "soulmap_delta" in choice_obj:
                db = SessionLocal()
                try:
                    # Convert list delta to dict format for new service
                    raw_delta = choice_obj["soulmap_delta"]
                    if isinstance(raw_delta, list) and len(raw_delta) == 64:
                        # Convert to trait dictionary format
                        from soulmap.mapping import SoulTrait
                        delta_dict = {}
                        for trait in SoulTrait:
                            if trait.value < len(raw_delta):
                                delta_dict[trait.name] = float(raw_delta[trait.value])
                        
                        # Store delta for response
                        soulmap_delta = delta_dict
                        
                        # Apply delta using new service
                        apply_delta(db, player_id, delta_dict)
                        print(f"✅ [main] Updated soulmap for player={player_id} with provided delta", flush=True)
                    else:
                        print(f"⚠️ [main] soulmap_delta wrong format: {type(raw_delta)}, length: {len(raw_delta) if isinstance(raw_delta, list) else 'N/A'}", flush=True)
                finally:
                    db.close()
            else:
                # No soulmap_delta provided, trigger inference
                print(f"🧠 [main] No soulmap_delta provided, triggering inference for player={player_id}", flush=True)
                
                # Get choice text
                choice_text = choice_obj.get("text", "")
                
                # Get scene text from current scene
                scene_text = ""
                if req.sceneTag in tree:
                    scene_data = tree[req.sceneTag]
                    scene_text = scene_data.get("text", "")
                
                # Get current emotion state
                emotion_state = {}
                try:
                    from emotion.models import get_emotion_state
                    emotion_state = get_emotion_state(player_id)
                except Exception as e:
                    print(f"⚠️ [main] Could not get emotion state: {e}", flush=True)
                
                # Get NPC trust levels
                trust_levels = {}
                try:
                    from npc.service import get_npc_states
                    npc_states = get_npc_states(player_id)
                    trust_levels = {npc.name: npc.trust for npc in npc_states if hasattr(npc, 'trust')}
                except Exception as e:
                    print(f"⚠️ [main] Could not get NPC trust levels: {e}", flush=True)
                
                # Get memory recap
                memory_recap = ""
                try:
                    from codex.memory import get_memory_recap
                    memory_recap = get_memory_recap(player_id)
                except Exception as e:
                    print(f"⚠️ [main] Could not get memory recap: {e}", flush=True)
                
                # Enqueue soulmap inference task and wait for result
                try:
                    from purpose_agents.codex_router import codex_router
                    task_id = await codex_router.enqueue_soulmap_inference(
                        player_id=player_id,
                        choice_text=choice_text,
                        scene_text=scene_text,
                        emotion_state=emotion_state,
                        trust_levels=trust_levels,
                        memory_recap=memory_recap
                    )
                    print(f"🧠 [main] Enqueued soulmap inference task {task_id} for player={player_id}", flush=True)
                    # Wait for the inference to complete and get the result
                    import asyncio
                    max_wait = 10  # Maximum wait time in seconds
                    wait_time = 0
                    while wait_time < max_wait:
                        result = codex_router.get_soulmap_task_result(task_id)
                        if result and isinstance(result, dict):
                            soulmap_delta = result
                            print(f"✅ [main] Got soulmap delta from inference: {soulmap_delta}", flush=True)
                            break
                        await asyncio.sleep(0.5)
                        wait_time += 0.5
                        print(f"🧠 [main] Waiting for soulmap inference... ({wait_time}s)", flush=True)
                    if wait_time >= max_wait:
                        print(f"⚠️ [main] Soulmap inference timeout for player={player_id}", flush=True)
                except Exception as e:
                    print(f"❌ [main] Failed to enqueue soulmap inference: {e}", flush=True)
                    
        except Exception as e:
            print(f"⚠️ [main] Soulmap integration failed for player={player_id}: {e}", flush=True)
    # --- END Soulmap delta integration ---

    print(f"🟢 [main] Returning response for soulSeedId={req.soulSeedId}, nextTag={next_tag}", flush=True)
    return _scene_to_response(next_tag, tree, player_id=player_id, story_data=story_data, soulmap_delta=soulmap_delta)

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
    st = _read_json(str(STATE_FILE), {"trust": {}}).get("trust", {})
    trust_val = float(st.get(soulSeedId, 0))
    print(f"✅ [main] /trust -> {trust_val}")
    return {"trust": trust_val}


@app.post("/reset")
def api_reset(soulSeedId: str | None = Form(default=None)) -> dict[str, bool]:
    if soulSeedId is None:
        raise HTTPException(404, "Missing soulSeedId")
    state = _read_json(str(STATE_FILE), {"stories": {}})
    state["stories"].pop(soulSeedId, None)
    _write_json(str(STATE_FILE), state)
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


@app.get("/soulmap/inference/status/{task_id}")
def get_soulmap_inference_status(task_id: str) -> dict[str, str]:
    """Get the status of a soulmap inference task"""
    status = codex_router.get_task_status(task_id)
    return {"task_id": task_id, "status": status.value if status else "not_found"}


@app.get("/soulmap/inference/result/{task_id}")
def get_soulmap_inference_result(task_id: str) -> dict[str, Any]:
    """Get the result of a completed soulmap inference task"""
    result = codex_router.get_soulmap_task_result(task_id)
    if result:
        return {"task_id": task_id, "delta": result}
    else:
        raise HTTPException(404, "Task not found or not completed")


# --- Resume/Restart Endpoints ---
@app.get("/resume/{player_id}")
def api_resume(player_id: str):
    profiles = _read_json(str(DATA_FILE), {})
    profile = profiles.get(player_id)
    if not profile:
        raise HTTPException(404, "Player not found")
    soul_seed_id = profile.get("soulSeedId")
    if not soul_seed_id:
        raise HTTPException(404, "SoulSeedId not found for player")
    state = _read_json(str(STATE_FILE), {"stories": {}})
    story = state["stories"].get(soul_seed_id)
    if not story:
        raise HTTPException(404, "No story in progress for this player")
    return {
        "current": story.get("current"),
        "history": story.get("history", []),
        "tree": story.get("tree", {})
    }

class RestartRequest(BaseModel):
    soulSeedId: str

@app.post("/restart")
def api_restart(req: RestartRequest):
    state = _read_json(str(STATE_FILE), {"stories": {}})
    if req.soulSeedId in state["stories"]:
        del state["stories"][req.soulSeedId]
        _write_json(str(STATE_FILE), state)
    return {"restarted": True}

@app.get("/memory/{player_id}")
def api_memory(player_id: str):
    profiles = _read_json(str(DATA_FILE), {})
    profile = profiles.get(player_id)
    if not profile:
        return {"recap": "No memory recap available for this player yet."}
    soul_seed_id = profile.get("soulSeedId")
    if not soul_seed_id:
        return {"recap": "No memory recap available for this player yet."}
    state = _read_json(str(STATE_FILE), {"stories": {}})
    story_data = state["stories"].get(soul_seed_id)
    if not story_data:
        return {"recap": "No memory recap available for this player yet."}
    story = story_data.get("tree", {})
    history = story_data.get("history", [])
    # Use the enhanced codex memory system with story_data for onboarding events
    recap = codex_update_memory(player_id, story, history, story_data)
    if not recap:
        recap = "No memory recap available for this player yet."
    return {"recap": recap}

@app.get("/test/npc-dialogue/{player_id}")
def test_npc_dialogue(player_id: str):
    """Test endpoint to generate NPC dialogue for a player"""
    try:
        npc_id = "companion-001"
        dialogue = generate_npc_dialogue(npc_id, player_id)
        return {
            "npc_id": npc_id,
            "player_id": player_id,
            "dialogue": dialogue,
            "message": "NPC dialogue generated successfully"
        }
    except Exception as e:
        print(f"Error generating NPC dialogue: {e}")
        return {
            "error": str(e),
            "message": "Failed to generate NPC dialogue"
        }


@app.get("/test-simple")
def test_simple():
    return {"message": "Test endpoint working"}

@app.get("/health")
def health_check():
    """
    Health check endpoint for SPR-BOOT01
    Returns basic system status and configuration info
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "running",
            "database": "configured",
            "pgvector": settings.pgvector_extension
        },
        "config": {
            "postgres_url": settings.postgres_url.split("@")[-1] if "@" in settings.postgres_url else "configured",
            "s3_endpoint": settings.s3_endpoint,
            "use_cpu_stubs": settings.use_cpu_stubs
        }
    }

# ─────────────────────────────── Validation Endpoint ───────────────────────────────
@app.post("/validate")
def api_validate(tree: dict) -> dict[str, list[str]]:
    """
    Validate a story tree and return any issues found.
    This is a development-only endpoint for testing story validation.
    """
    issues = validate(tree)
    return {"issues": issues}

@app.get("/ritual")
def api_ritual_get():
    """
    Handle GET requests to /ritual endpoint.
    This should not be accessed directly - use POST instead.
    """
    raise HTTPException(
        status_code=405,
        detail="Method Not Allowed. Use POST to perform the ritual."
    )





