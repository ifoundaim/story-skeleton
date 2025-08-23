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
from typing import Any, Union, Dict, Optional, cast, List

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

# Import choice generator for free-text processing
try:
    from story.choice_generator import make_contextual_choice, should_enable_free_text
    from story.telemetry import log_choice_generated, log_free_text
    CHOICE_GENERATOR_AVAILABLE = True
except ImportError:
    CHOICE_GENERATOR_AVAILABLE = False
    def make_contextual_choice(*args, **kwargs):
        return None
    def should_enable_free_text(*args, **kwargs):
        return False
    def log_choice_generated(*args, **kwargs):
        pass
    def log_free_text(*args, **kwargs):
        pass

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

# ─── Simple narrative-name extractor for binding story names to NPC IDs ───────
import re as _re
_NAME_STOPWORDS = {
    "Aim", "The", "A", "An", "City", "Neonveil", "In", "Of", "On", "At", "To",
    "With", "For", "And", "But", "Or", "If", "Then", "Else", "Their", "His", "Her",
}

def _extract_candidate_names(text: str) -> list[str]:
    if not text:
        return []
    # naive proper-noun capture: words with capital first letter and >=3 letters
    words = _re.findall(r"\b[A-Z][a-z]{2,}\b", text)
    names = []
    for w in words:
        if w in _NAME_STOPWORDS:
            continue
        if w not in names:
            names.append(w)
    return names[:3]

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

# Lightweight persistent store for NPC chat state
CHAT_STATE_FILE = BASE_DIR / "npc_chat_state.json"

# Feature flag: allow very generic role-based fallback binding when no NPC is present
# Default OFF to avoid random NPCs appearing in scenes without explicit characters
ENABLE_GENERIC_ROLE_BINDING = os.getenv("ENABLE_GENERIC_ROLE_BINDING", "false").lower() in {"true", "1", "yes"}

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

    # Ensure chat state file exists
    try:
        if not CHAT_STATE_FILE.exists():
            CHAT_STATE_FILE.write_text("{}", encoding="utf-8")
    except Exception as e:
        print(f"⚠️ [main] startup: failed to init chat state file: {e}")


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

def _read_chat_state() -> dict:
    try:
        if CHAT_STATE_FILE.exists():
            return json.loads(CHAT_STATE_FILE.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(f"⚠️ [main] chat state read failed: {e}")
    return {}

def _write_chat_state(state: dict) -> None:
    try:
        CHAT_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"⚠️ [main] chat state write failed: {e}")

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

    # Normalize incoming choice field names
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

class FreeTextRequest(BaseModel):
    player_id: str = Field(..., alias="playerId")
    scene_index: int = Field(..., alias="sceneIndex")
    user_text: str = Field(..., max_length=500, alias="userText")
    model_config = ConfigDict(populate_by_name=True)

class FreeTextResponse(BaseModel):
    success: bool
    choice_text: str
    mapped_text: str | None = None
    error: str | None = None

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
    # Allow arbitrary dialogue entry shapes (may include trust: float, name, etc.)
    npc_dialogue: list[dict] = Field(default_factory=list)
    dialogue_type: str = "single"  # "single" or "group"
    npcs_present: list[str] = Field(default_factory=list)
    soulmap_delta: dict[str, float] | None = None
    # Beat information for debugging/testing
    beat_id: str | None = None
    beat_tags: list[str] = Field(default_factory=list)
    scene_phase: str | None = None

SceneResponse.model_rebuild()

# ─── NPC Chat Models ──────────────────────────────────────────────────────────
class NPCChatIn(BaseModel):
    playerId: str
    npcId: str
    sceneTag: str
    message: str


class NPCChatOut(BaseModel):
    npcId: str
    reply: str
    history: list[dict]

NPCChatIn.model_rebuild()
NPCChatOut.model_rebuild()


# ─── Flow Summary Models ──────────────────────────────────────────────────────
class ConsequenceChange(BaseModel):
    type: str  # "flag", "promise", "reputation", "resource"
    key: str
    value: Any
    npc_id: Optional[str] = None
    delta: Optional[Any] = None

class ChoiceRecord(BaseModel):
    scene_index: int
    text: str
    tags: List[str] = Field(default_factory=list)
    effects: Dict[str, Any] = Field(default_factory=dict)

class FlowSummaryResponse(BaseModel):
    scene_range: List[int]  # [start, end]
    choices: List[ChoiceRecord]
    consequences: List[ConsequenceChange]
    fogged_branches: int
    percent_stats: Dict[str, float] = Field(default_factory=dict)

ConsequenceChange.model_rebuild()
ChoiceRecord.model_rebuild()
FlowSummaryResponse.model_rebuild()


# ─────────────────────────────── NPC Chat API ────────────────────────────────
@app.post("/npc/chat", response_model=NPCChatOut)
async def npc_chat(payload: NPCChatIn) -> NPCChatOut:
    """Minimal chat endpoint for interactive NPC chat box.

    Persists chat history per (playerId, npcId) in a JSON file and generates a
    reply via existing dialogue utilities. Falls back to a safe canned line on
    failure so the UI never breaks.
    """
    state = _read_chat_state()
    key = f"{payload.playerId}:{payload.npcId}"
    history = state.get(key, [])

    history.append({
        "role": "user",
        "content": payload.message,
        "sceneTag": payload.sceneTag,
        "ts": datetime.utcnow().isoformat()
    })

    # Try to use our existing dialogue generator for consistency
    reply_text = None
    try:
        from codex.npc.npc_dialogue import generate_npc_dialogue_with_context
        # Provide short scene context from history last 3 messages
        recent_user_lines = [m["content"] for m in history if m.get("role") == "user"][-3:]
        scene_context = " \n".join(recent_user_lines)
        reply_text = generate_npc_dialogue_with_context(payload.npcId, payload.playerId, scene_context)
    except Exception as e:
        print(f"⚠️ [main] npc_chat fallback due to error: {e}")

    if not reply_text:
        reply_text = "I hear you. Let's figure this out together."

    history.append({
        "role": "assistant",
        "content": reply_text,
        "sceneTag": payload.sceneTag,
        "ts": datetime.utcnow().isoformat()
    })

    state[key] = history
    _write_chat_state(state)

    return NPCChatOut(npcId=payload.npcId, reply=reply_text, history=history)

# ─────────────────────────────── Core Endpoints ───────────────────────────────
@app.post("/ritual", response_model=RitualResponse)
@app.post("/api/ritual", response_model=RitualResponse)
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

        # Persist ritual inputs for Director world hook extraction
        try:
            ritual_dir = BASE_DIR / "ritual_cache"
            ritual_dir.mkdir(parents=True, exist_ok=True)
            ritual_file = ritual_dir / f"{payload.playerId}.json"
            _write_json(str(ritual_file), {
                "askText": payload.askText,
                "seekText": payload.seekText,
                "knockText": payload.knockText,
                "theme": str(data.get("theme", payload.theme)),
            })
        except Exception as _ritual_cache_err:
            print(f"⚠️ [main] failed to write ritual cache: {_ritual_cache_err}")

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
        initSceneTag="tag_001",  # Updated to use 30-scene framework
    )


def _scene_to_response(tag: str, story: dict, player_id: str = "", story_data: Optional[Dict[str, Any]] = None, soulmap_delta: Optional[Dict[str, float]] = None):
    print(f"DEBUG: _scene_to_response called with tag={tag}, story keys={list(story.keys())}")
    if tag not in story:
        return {
            "sceneTag": tag,
            "text": "The story ends here.",
            "choices": [],
            "media": {"images": [], "audio": []},
            "npc_text_dynamic": None,
            "npc_dialogue": [],
            "dialogue_type": "single",
            "npcs_present": [],
            "soulmap_delta": soulmap_delta or None,
        }
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
    # Default to story-declared npcs_present; will be updated if dynamic assignment occurs
    npcs_present_out: list[str] = [str(x) for x in scene.get("npcs_present", [])]
    
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

                    # Name-first override: if prose contains an explicit proper name (e.g.,
                    # "partner, Jess," or "named Jess"), prefer that single character over
                    # any auto-assigned dynamic NPCs. This prevents random companions from
                    # appearing when the scene explicitly introduces someone by name.
                    try:
                        import re as _re
                        import uuid as _uuid
                        text_for_names = str(scene.get("text", ""))
                        explicit_names: list[str] = []
                        for _pat in [
                            r"\bnamed\s+([A-Z][A-Za-z'\-]{2,})\b",
                            r"\bwho\s+calls\s+themselves\s+([A-Z][A-Za-z'\-]{2,})\b",
                            r"\bintroduces\s+(?:himself|herself|themself)\s+as\s+([A-Z][A-Za-z'\-]{2,})\b",
                            # role, Name — covers patterns like "partner, Jess," "friend, Mira," etc.
                            r"\b(?:partner|friend|lover|mentor|ally|rival|sibling|parent|colleague|boss|guide|artist|stranger|oracle|leader|traveler|merchant|companion),\s*([A-Z][A-Za-z'\-]{2,})\b",
                            # common prepositions/verbs leading a named person: with/to/about/for/meet/see/visit
                            r"\bwith\s+([A-Z][A-Za-z'\-]{2,})\b",
                            r"\bto\s+([A-Z][A-Za-z'\-]{2,})\b",
                            r"\babout\s+([A-Z][A-Za-z'\-]{2,})\b",
                            r"\bfor\s+([A-Z][A-Za-z'\-]{2,})\b",
                            r"\b(?:meet|see|visit|call|text|message)\s+([A-Z][A-Za-z'\-]{2,})\b",
                            r"\b(?:look\s+for|search\s+for|ask\s+for|seek\s+out)\s+([A-Z][A-Za-z'\-]{2,})\b",
                        ]:
                            _m = _re.search(_pat, text_for_names)
                            if _m:
                                explicit_names.append(_m.group(1))
                        if explicit_names:
                            # Mint a deterministic ID for the first named character
                            _nm = explicit_names[0]
                            stable_id = str(
                                _uuid.uuid5(_uuid.NAMESPACE_OID, f"{player_id}:name:{_nm.lower()}")
                            ) if player_id else str(
                                _uuid.uuid5(_uuid.NAMESPACE_OID, f"default:name:{_nm.lower()}")
                            )
                            npcs_present = [stable_id]
                            # Reflect override into scene and present name map
                            _pnm = scene.get("_present_name_map", {}) or {}
                            _pnm[stable_id] = _nm
                            scene["_present_name_map"] = _pnm
                            scene["npcs_present"] = [stable_id]
                            print(f"[DEBUG] Explicit name override applied: {stable_id} -> {_nm}")
                        else:
                            # Keep scene's npcs_present in sync with dynamic assignment for profile seeding
                            try:
                                scene["npcs_present"] = [str(x) for x in (npcs_present or [])]
                            except Exception:
                                pass
                    except Exception as _e:
                        print(f"[DEBUG] Name-first override skipped due to error: {_e}")
                    
                    # Ensure NPC profiles exist for all present NPCs
                    if npcs_present:
                        try:
                            from npc.profile_seed import ensure_npc_profile
                            ensure_npc_profile(scene, player_id)
                            print(f"[DEBUG] Ensured NPC profiles for scene {tag}")
                            # Build present_name_map after ensuring profiles
                            present_name_map = {}
                            try:
                                from npc.service import get_npc_by_id
                                for nid in npcs_present:
                                    npc_obj = get_npc_by_id(player_id, str(nid), db)
                                    if npc_obj and getattr(npc_obj, "name", None):
                                        present_name_map[str(nid)] = npc_obj.name
                            except Exception:
                                pass
                            if present_name_map:
                                scene.setdefault("_present_name_map", present_name_map)
                        except Exception as e:
                            print(f"[DEBUG] Failed to ensure NPC profiles: {e}")
                            
                except Exception as e:
                    print(f"[DEBUG] Failed to get dynamic NPCs, using fallback: {e}")
                    # Continue with existing npcs_present logic
                
                # If no npcs_present defined, DO NOT auto-inject companions from DB.
                # Rely strictly on beat-driven npcs_present or role/name detection from prose.
                if not npcs_present:
                    print("[DEBUG] Auto-companion injection disabled; relying on beat/role-driven NPCs")
                
                # Generate group dialogue if multiple NPCs present
                if len(npcs_present) > 1:
                    try:
                        from npc.service import get_trust_scores, get_npc_by_id
                        from emotion.service import get_emotion_vector
                        from db import SessionLocal
                        
                        db = SessionLocal()
                        trust_scores = get_trust_scores(player_id, db)
                        emotion_vector = get_emotion_vector(player_id)
                        npc_metadata = story.get("_npc_metadata", {})
                        scene_context = scene.get("text", "")
                        
                        # Generate group dialogue (simple signature)
                        dialogue_entries = generate_group_dialogue(npcs_present, player_id, scene_context)
                        
                        if dialogue_entries:
                            # Enrich names/trust from DB if missing
                            for entry in dialogue_entries:
                                try:
                                    npc = get_npc_by_id(player_id, entry.get("npc_id", ""), db)
                                    if npc:
                                        entry["name"] = npc.name or entry.get("name", "Companion")
                                        # cast to string to avoid downstream schema assumptions
                                        entry["trust"] = f"{float(npc.trust):.2f}"
                                except Exception:
                                    pass
                            # Final pass: if present_name_map exists, prefer it for display
                            try:
                                name_map = scene.get("_present_name_map", {}) or {}
                                if isinstance(name_map, dict):
                                    for entry in dialogue_entries:
                                        nid = entry.get("npc_id")
                                        if nid and name_map.get(str(nid)):
                                            entry["name"] = name_map[str(nid)]
                            except Exception:
                                pass
                            # close DB after enrichment
                            try:
                                db.close()
                            except Exception:
                                pass
                            npc_dialogue = dialogue_entries
                            dialogue_type = "group" if len(dialogue_entries) > 1 else "single"
                            # Set npc_text_dynamic to first dialogue for backward compatibility
                            npc_text_dynamic = dialogue_entries[0]["text"] if dialogue_entries else None
                            print(f"[DEBUG] Generated group dialogue with {len(dialogue_entries)} entries")
                        else:
                            # Fallback to single NPC dialogue only if we have at least one NPC
                            if npcs_present:
                                npc_id = npcs_present[0]
                                npc_text_dynamic = generate_npc_dialogue(npc_id, player_id)
                                npc_dialogue = [{"npc_id": str(npc_id), "text": npc_text_dynamic}] if npc_text_dynamic else []
                                dialogue_type = "single"
                            else:
                                npc_text_dynamic = None
                                npc_dialogue = []
                                dialogue_type = "single"
                        
                    except Exception as e:
                        print(f"[DEBUG] Failed to generate group dialogue: {e}")
                        # Fallback to single NPC dialogue only if we have NPCs present
                        if npcs_present:
                            npc_id = npcs_present[0]
                            npc_text_dynamic = generate_npc_dialogue(npc_id, player_id)
                            npc_dialogue = [{"npc_id": str(npc_id), "text": npc_text_dynamic}] if npc_text_dynamic else []
                            dialogue_type = "single"
                        else:
                            npc_text_dynamic = None
                            npc_dialogue = []
                            dialogue_type = "single"
                        
                elif len(npcs_present) == 1:
                    # Single NPC dialogue
                    npc_id = npcs_present[0]
                    npc_text_dynamic = generate_npc_dialogue(npc_id, player_id)
                    # Attach name/trust
                    try:
                        from npc.service import get_npc_by_id
                        from db import SessionLocal
                        db = SessionLocal()
                        npc = get_npc_by_id(player_id, str(npc_id), db)
                        db.close()
                        npc_name = npc.name if npc else "Companion"
                        npc_trust = float(npc.trust) if npc else trust_scores.get(str(npc_id), 0.5) if 'trust_scores' in locals() else 0.5
                    except Exception:
                        npc_name = "Companion"
                        npc_trust = 0.5
                    npc_dialogue = [{"npc_id": str(npc_id), "name": npc_name, "text": npc_text_dynamic, "trust": f"{npc_trust:.2f}"}] if npc_text_dynamic else []
                    dialogue_type = "single"
                    print(f"[DEBUG] Generated single NPC dialogue for {npc_id}")
                else:
                    # No NPCs present, no dialogue
                    npc_text_dynamic = None
                    npc_dialogue = []
                    dialogue_type = "single"
                    print(f"[DEBUG] No NPCs present in scene {tag}")
                # Track npcs_present to return with response, and attach names in a parallel map
                npcs_present_out = [str(x) for x in (npcs_present or [])]
                try:
                    # Prefer DB names if ensure_npc_profile already seeded them
                    present_name_map = scene.get("_present_name_map", {}) or {}
                    if not present_name_map:
                        from npc.profile_seed import _friendly_name_for_uuid as _fname
                        for _id in npcs_present_out:
                            import uuid as _uuid
                            try:
                                present_name_map[_id] = _fname(_uuid.UUID(str(_id)))
                            except Exception:
                                present_name_map[_id] = _id[:8]
                        scene.setdefault("_present_name_map", present_name_map)

                    # Bind first candidate narrative name to first unnamed NPC in scene
                    if present_name_map:
                        candidates = _extract_candidate_names(scene.get("text", ""))
                        if candidates:
                            from npc.service import get_npc_by_id
                            from db import SessionLocal as _SL
                            db2 = _SL()
                            try:
                                # pick the first NPC whose mapped name looks like an ID fragment
                                target_npc_id = None
                                for nid in npcs_present_out:
                                    nm = present_name_map.get(nid, "")
                                    if nm and (nm[:8].lower() in str(nid).lower() or len(nm) >= 8 and nm.replace('-', '').isalnum()):
                                        target_npc_id = nid
                                        break
                                if target_npc_id:
                                    npc_row = get_npc_by_id(player_id, target_npc_id, db2)
                                    if npc_row:
                                        # update DB and map
                                        npc_row.name = candidates[0]
                                        db2.commit()
                                        present_name_map[target_npc_id] = candidates[0]
                                        scene["_present_name_map"] = present_name_map
                            finally:
                                db2.close()
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"[DEBUG] Failed to generate NPC dialogue: {e}")
                npc_text_dynamic = None
                npc_dialogue = []
                dialogue_type = "single"
                # ensure we at least return story npcs_present
    # FINAL FALLBACK: If still no NPCs present but the prose references a mentor/elder/sage,
    # introduce a deterministic generic Mentor NPC so the UI can render identity and chat.
    try:
        if not npcs_present_out:
            text_probe = str(scene.get("text", "")).lower()
            if any(k in text_probe for k in ["elder", "mentor", "sage"]):
                import uuid as _uuid
                fallback_mentor_id = str(_uuid.uuid5(_uuid.NAMESPACE_OID, "default:mentor"))
                npcs_present_out = [fallback_mentor_id]
                try:
                    present_name_map = scene.get("_present_name_map", {}) or {}
                    if fallback_mentor_id not in present_name_map:
                        present_name_map[fallback_mentor_id] = "Mentor"
                    scene["_present_name_map"] = present_name_map
                    scene["npcs_present"] = [fallback_mentor_id]
                    try:
                        ensure_npc_profile(scene, player_id)
                    except Exception:
                        pass
                except Exception:
                    pass
    except Exception:
        pass

    # ULTRA-GENERIC BINDING: If we still have no NPCs and the flag is enabled,
    # scan prose for generic character roles like "hermit", "magician", "soldier".
    try:
        if not npcs_present_out and ENABLE_GENERIC_ROLE_BINDING:
            scene_text = str(scene.get("text", ""))
            if not scene_text:
                raise Exception("No scene text available for role binding")
            text_low = scene_text.lower()
            import re as __re
            # Common role nouns (extensible). We intentionally keep this broad but curated
            # Instead of a narrow whitelist, accept a wide range of human/role nouns.
            # Heuristic: capture head noun from determiners and filter out scene/world words.
            STOPWORDS = {
                "forest","village","town","city","river","mountain","valley","path","road","song",
                "day","night","mist","shadow","light","darkness","magic","journey","realm","world",
                "wind","rain","storm","sun","moon","stars","gate","door","hall","temple","ruins",
            }
            # Find phrases like "a/an/the <... role>" and take the head noun
            heads: list[str] = []
            # Capture 1–2 tokens after determiner to avoid swallowing verbs like "offered"
            for m in __re.finditer(r"\b(?:a|an|the)\s+([a-z][a-z\-]+(?:\s+[a-z][a-z\-]+)?)\b", text_low):
                phrase = m.group(1).strip()
                if not phrase:
                    continue
                # head noun is last token
                head = __re.sub(r"[^a-z]", "", phrase.split()[-1])
                if head and len(head) >= 3 and head not in STOPWORDS and head not in heads:
                    heads.append(head)
            # Also try to capture explicit character names from common intro patterns
            name_candidates: list[str] = []
            for pat in [
                r"\bnamed\s+([A-Z][A-Za-z'\-]{2,})\b",
                r"\bwho\s+calls\s+themselves\s+([A-Z][A-Za-z'\-]{2,})\b",
                r"\bintroduces\s+(?:himself|herself|themself)\s+as\s+([A-Z][A-Za-z'\-]{2,})\b",
                r"\bwho\s+introduces\s+(?:himself|herself|themself)\s+as\s+([A-Z][A-Za-z'\-]{2,})\b",
                # Also catch simpler references like "with Alex", "about Alex", etc.
                r"\bwith\s+([A-Z][A-Za-z'\-]{2,})\b",
                r"\bto\s+([A-Z][A-Za-z'\-]{2,})\b",
                r"\babout\s+([A-Z][A-Za-z'\-]{2,})\b",
                r"\bfor\s+([A-Z][A-Za-z'\-]{2,})\b",
                r"\b(?:meet|see|visit|call|text|message)\s+([A-Z][A-Za-z'\-]{2,})\b",
                r"\b(?:look\s+for|search\s+for|ask\s+for|seek\s+out)\s+([A-Z][A-Za-z'\-]{2,})\b",
            ]:
                n = __re.search(pat, scene_text)
                if n:
                    name = n.group(1)
                    if name and name not in name_candidates:
                        name_candidates.append(name)
            # If we have explicit names but no role heads, mint IDs and return them directly
            if not npcs_present_out and name_candidates:
                import uuid as _uuid
                present_name_map = scene.get("_present_name_map", {}) or {}
                generated_ids: list[str] = []
                for nm in name_candidates[:1]:  # only show the first detected name
                    sid = str(_uuid.uuid5(_uuid.NAMESPACE_OID, f"{player_id}:name:{nm.lower()}")) if player_id else str(_uuid.uuid5(_uuid.NAMESPACE_OID, f"default:name:{nm.lower()}"))
                    if sid not in generated_ids:
                        generated_ids.append(sid)
                        present_name_map[sid] = nm
                if generated_ids:
                    npcs_present_out = generated_ids
                    scene["_present_name_map"] = present_name_map
                    try:
                        scene["npcs_present"] = generated_ids
                    except Exception:
                        pass
                    # Ensure DB profiles for these named characters
                    try:
                        ensure_npc_profile({"npc_profile": [{"id": generated_ids[0], "name": name_candidates[0]}]}, player_id)
                    except Exception:
                        pass

            if heads and not npcs_present_out:
                import uuid as _uuid
                try:
                    from npc.profile_seed import _friendly_name_for_uuid as _fname
                except Exception:
                    _fname = None  # type: ignore
                present_name_map = scene.get("_present_name_map", {}) or {}
                generated_ids: list[str] = []
                for idx_role, role in enumerate(heads[:2]):  # limit to 2 to keep UI focused
                    stable_id = str(_uuid.uuid5(_uuid.NAMESPACE_OID, f"{player_id}:role:{role}")) if player_id else str(_uuid.uuid5(_uuid.NAMESPACE_OID, f"default:role:{role}"))
                    if stable_id not in generated_ids:
                        generated_ids.append(stable_id)
                        # Prefer explicitly mentioned name if available
                        explicit_name = name_candidates[idx_role] if idx_role < len(name_candidates) else None
                        if explicit_name:
                            present_name_map[stable_id] = explicit_name
                        elif _fname is not None:
                            try:
                                present_name_map[stable_id] = _fname(_uuid.UUID(stable_id))
                            except Exception:
                                present_name_map[stable_id] = role.title()
                        else:
                            present_name_map[stable_id] = role.title()
                if generated_ids and not npcs_present_out:
                    npcs_present_out = generated_ids
                    scene["_present_name_map"] = present_name_map
                    # Reflect into scene for downstream consumers
                    try:
                        scene["npcs_present"] = generated_ids
                    except Exception:
                        pass
                    # Ensure DB profiles exist for these NPCs
                    try:
                        # Create minimal temp scene to seed profiles with deterministic names
                        temp_scene = {"npcs_present": generated_ids}
                        ensure_npc_profile(temp_scene, player_id)
                    except Exception:
                        pass
    except Exception:
        pass
    
    # Normalize npc_dialogue trust field to string if present
    try:
        if isinstance(npc_dialogue, list):
            for entry in npc_dialogue:
                if isinstance(entry, dict) and "trust" in entry and not isinstance(entry["trust"], str):
                    try:
                        entry["trust"] = f"{float(entry.get('trust')):.2f}"
                    except Exception:
                        entry["trust"] = str(entry.get('trust'))
    except Exception:
        pass

    media_dict = {"images": getattr(media, "images", []), "audio": getattr(media, "audio", [])}
    # Keep original scene prose; do not inject trailing companion line
    base_text = scene.get("text", "")
    text_with_names = base_text

    # If we still have no NPCs, but the prose mentions a singular role noun (Traveler/Leader),
    # bind it to a deterministic NPC so the UI can show a profile and name.
    try:
        if not npcs_present_out and base_text:
            # Find capitalized nouns that look like roles
            candidates = _extract_candidate_names(base_text)
            role_aliases = {"Traveler": "traveler", "Leader": "leader", "Mentor": "mentor", "Sage": "sage"}
            matched = [w for w in candidates if w in role_aliases]
            if matched:
                import uuid as _uuid
                # Use a stable namespace-based UUID for each role
                role_key = role_aliases[matched[0]]
                stable_id = str(_uuid.uuid5(_uuid.NAMESPACE_OID, f"default:{role_key}"))
                npcs_present_out = [stable_id]
                # attach to name map; synthesize a friendly name if unknown
                present_name_map = scene.get("_present_name_map", {}) or {}
                if stable_id not in present_name_map:
                    # Prefer canonical names for some roles (generic names, not pre-defined companions)
                    canonical = {"mentor": "Mentor", "sage": "Elder", "traveler": "Traveler", "leader": "Leader", "oracle": "Oracle"}
                    present_name_map[stable_id] = canonical.get(role_key, matched[0])
                scene["_present_name_map"] = present_name_map
                # Ensure DB profile exists
                try:
                    temp_scene = {"npcs_present": [stable_id]}
                    ensure_npc_profile(temp_scene, player_id)
                except Exception:
                    pass
    except Exception:
        pass
    # Include present_name_map if available
    present_name_map = scene.get("present_name_map", scene.get("_present_name_map", {})) if isinstance(scene, dict) else {}
    
    # Extract beat information for testing/debugging
    beat_id = scene.get("beat_id") if isinstance(scene, dict) else None
    beat_tags = scene.get("narrative_purpose", []) if isinstance(scene, dict) else []
    scene_phase = scene.get("phase") if isinstance(scene, dict) else None
    # If Director beat fields are missing and story looks legacy, try to infer simple ones
    if beat_id is None and isinstance(scene, dict):
        try:
            if isinstance(scene.get("scene_index"), int):
                idx = int(scene["scene_index"]) or 0
                scene_phase = "early" if idx <= 6 else ("mid" if idx <= 21 else "late")
            beat_id = beat_id or "legacy_llm"
            if not beat_tags:
                beat_tags = ["legacy", "linear"]
        except Exception:
            pass
    
    return {
        "sceneTag": tag,
        "text": text_with_names,
        "choices": choices,
        "media": media_dict,
        "npc_text_dynamic": npc_text_dynamic,
        "npc_dialogue": npc_dialogue,
        "dialogue_type": dialogue_type,
        "npcs_present": npcs_present_out,
        "present_name_map": present_name_map,
        "soulmap_delta": soulmap_delta,
        "beat_id": beat_id,
        "beat_tags": beat_tags,
        "scene_phase": scene_phase,
    }

# ───────────────────────── ritual endpoint ─────────────────────────────────
@app.post("/start")
async def api_start(req: StartRequest):
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
    return _scene_to_response("intro_001", story, player_id="")  # Use correct first scene from static story


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


async def _choose_py(req: ChoiceRequest):
    try:
        chosen_val = req.choice_val
    except Exception as e:
        print(f"❌ [main] _choose_py could not resolve choice value: {e}", flush=True)
        raise
    print(f"🟢 [main] Entered _choose_py for soulSeedId={req.soulSeedId}, sceneTag={req.sceneTag}, choice={chosen_val}", flush=True)
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
        # Only patch if the story appears incomplete (short fallback)
        try:
            total_scenes = len(tree)
            continuing = sum(1 for s in tree.values() if isinstance(s, dict) and s.get("choices"))
            should_patch = (total_scenes < 25) or (continuing < 20) or ("tag_029" not in tree)
        except Exception:
            should_patch = True
        if should_patch:
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

    raw_choices = scene.get("choices", {}) or {}
    print(f"[main] _choose_py raw choices for {req.sceneTag}: {raw_choices}", flush=True)
    # Support both dict-of-dicts (with next) and legacy dict-of-tags
    str_key_map = {}
    for k, v in raw_choices.items():
        if isinstance(v, dict) and "next" in v:
            str_key_map[str(k)] = str(v.get("next"))
        else:
            # legacy static JSON: value is next-tag string
            try:
                str_key_map[str(k)] = str(v)
            except Exception:
                pass
    print(f"[main] _choose_py key map for {req.sceneTag}: {str_key_map}", flush=True)
    key = str(chosen_val)
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
                companion_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"default:companion")
                apply_trust(player_id, str(companion_uuid), legacy_trust_delta, db)
                print(f"[main] Applied legacy trust delta {legacy_trust_delta} to companion")
            
            # Apply multi-NPC trust deltas
            if npc_trust_deltas:
                apply_trust_to_multiple(player_id, npc_trust_deltas, db)
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
                                # Check if choice has a recruit_line (from automatic recruitment)
                                recruit_line = choice_obj.get("recruit_line")
                                
                                if recruit_line:
                                    # Use the provided recruit_line from automatic recruitment
                                    recruitment_dialogue = recruit_line
                                    print(f"🎭 [main] Using automatic recruitment line: {recruitment_dialogue}", flush=True)
                                else:
                                    # Fall back to generated recruitment dialogue
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
                                    print(f"🎭 [main] Generated recruitment dialogue: {recruitment_dialogue}", flush=True)
                                
                                # Store recruitment dialogue for scene response
                                story_data.setdefault("recruitment_dialogue", []).append({
                                    "npc_id": npc_onboard_id,
                                    "npc_name": onboarded_npc.name,
                                    "dialogue": recruitment_dialogue,
                                    "scene_tag": req.sceneTag,
                                    "is_automatic": recruit_line is not None
                                })
                                
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
                        
                        # Log recruitment telemetry
                        try:
                            from story_recruitment import evaluator
                            recruitment_telemetry = {
                                "npc_id": npc_onboard_id,
                                "npc_name": onboarded_npc.name,
                                "scene_tag": req.sceneTag,
                                "timestamp": datetime.utcnow().isoformat(),
                                "is_automatic": choice_obj.get("recruit_line") is not None,
                                "trust_level": onboarded_npc.trust,
                                "choice_text": choice_obj.get("text", "Unknown"),
                                "player_accepted": True
                            }
                            
                            # Store telemetry in story data for potential export
                            story_data.setdefault("recruitment_telemetry", []).append(recruitment_telemetry)
                            
                            print(f"📊 [main] Logged recruitment telemetry: {recruitment_telemetry}", flush=True)
                            
                        except Exception as e:
                            print(f"⚠️ [main] Failed to log recruitment telemetry: {e}", flush=True)
                        
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
@app.post("/choice")
@app.post("/choose")
async def api_choose(req: ChoiceRequest = Body(...)):
    try:
        return await _choose_py(req)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/choices/free", response_model=FreeTextResponse)
async def api_free_text(req: FreeTextRequest = Body(...)):
    """Process free-text input and transform it into a safe, validated choice."""
    try:
        # Check if free-text is enabled for this scene
        if not should_enable_free_text(req.scene_index):
            return FreeTextResponse(
                success=False,
                choice_text="",
                error="Free-text is not enabled for this scene"
            )
        
        # Sanitize input
        sanitized_text = req.user_text.strip()
        if not sanitized_text or len(sanitized_text) < 3:
            return FreeTextResponse(
                success=False,
                choice_text="",
                error="Text too short or empty"
            )
        
        # Light moderation - check for inappropriate content
        inappropriate_words = ["kill", "murder", "hate", "destroy", "attack", "fight", "hurt"]
        if any(word in sanitized_text.lower() for word in inappropriate_words):
            return FreeTextResponse(
                success=False,
                choice_text="",
                error="Content contains inappropriate language"
            )
        
        # Transform via LLM with guardrails
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            prompt = f"""
Transform this user input into a safe, contextual story choice:

User input: "{sanitized_text}"

REQUIREMENTS:
1. Must be safe and appropriate for all audiences
2. Should be 1-2 sentences maximum
3. Must feel natural in a story context
4. Should maintain the user's intent while being story-appropriate
5. Avoid violence, inappropriate content, or breaking character

Transform the input into a story choice that the player character could reasonably make.
Respond with ONLY the transformed choice text, no explanations.
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            transformed_text = response.choices[0].message.content.strip()
            
            # Validate the transformed text
            if not transformed_text or len(transformed_text) > 200:
                transformed_text = "Consider the situation carefully"
            
            # Log the free-text processing
            if CHOICE_GENERATOR_AVAILABLE:
                log_free_text(req.scene_index, sanitized_text[:50], transformed_text)
            
            return FreeTextResponse(
                success=True,
                choice_text=transformed_text,
                mapped_text=transformed_text
            )
            
        except Exception as e:
            # Fallback to safe default
            safe_choice = "Consider the situation carefully"
            
            if CHOICE_GENERATOR_AVAILABLE:
                log_free_text(req.scene_index, sanitized_text[:50], safe_choice)
            
            return FreeTextResponse(
                success=True,
                choice_text=safe_choice,
                mapped_text=safe_choice
            )
            
    except Exception as exc:
        return FreeTextResponse(
            success=False,
            choice_text="",
            error=str(exc)
        )


@app.get("/trust")
def api_trust(soulSeedId: str) -> dict[str, float]:
    """Aggregate per-NPC trust into a single UI value for the current player.
    Looks up player_id via soulSeedId, then averages NPCState.trust values.
    Falls back to prior JSON if DB not available.
    """
    print(f"🔍 [main] /trust lookup soulSeedId={soulSeedId}")
    try:
        # reverse lookup player_id
        profiles = _read_json(str(DATA_FILE), {})
        player_id = None
        for pid, prof in profiles.items():
            if prof.get("soulSeedId") == soulSeedId:
                player_id = pid
                break
        if player_id:
            from db import SessionLocal
            from npc.service import get_state
            db = SessionLocal()
            try:
                npcs = get_state(player_id, db)
                if npcs:
                    avg_trust = sum(float(n.trust or 0.0) for n in npcs) / len(npcs)
                    print(f"✅ [main] /trust (avg from {len(npcs)} NPCs) -> {avg_trust}")
                    return {"trust": round(avg_trust, 3)}
            finally:
                db.close()
    except Exception as e:
        print(f"⚠️ [main] /trust DB aggregation failed: {e}")
    # fallback to legacy state JSON
    st = _read_json(str(STATE_FILE), {"trust": {}}).get("trust", {})
    trust_val = float(st.get(soulSeedId, 0))
    print(f"✅ [main] /trust (fallback) -> {trust_val}")
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

@app.get("/flow/summary")
def api_flow_summary(player_id: str, chapter: int = 1) -> FlowSummaryResponse:
    """Get a spoiler-safe summary of choices and consequences for a chapter."""
    try:
        # Load player profile to get soulSeedId
        profiles = _read_json(str(DATA_FILE), {})
        profile = profiles.get(player_id)
        if not profile:
            raise HTTPException(404, "Player not found")
        
        soul_seed_id = profile.get("soulSeedId")
        if not soul_seed_id:
            raise HTTPException(404, "SoulSeedId not found for player")
        
        # Load story state
        state = _read_json(str(STATE_FILE), {"stories": {}})
        story_data = state["stories"].get(soul_seed_id)
        if not story_data:
            raise HTTPException(404, "No story in progress for this player")
        
        # Calculate scene range for this chapter (assuming ~10 scenes per chapter)
        scenes_per_chapter = 10
        start_scene = (chapter - 1) * scenes_per_chapter
        end_scene = min(start_scene + scenes_per_chapter - 1, 29)  # Max 30 scenes
        
        # Extract choices from story history (this is a simplified version)
        # In a real implementation, you'd track choices more granularly
        choices = []
        history = story_data.get("history", [])
        
        # For now, create placeholder choices based on scene indices
        for scene_idx in range(start_scene, min(end_scene + 1, len(history))):
            if scene_idx < len(history):
                choices.append(ChoiceRecord(
                    scene_index=scene_idx,
                    text=f"Scene {scene_idx + 1}",
                    tags=["placeholder"],
                    effects={}
                ))
        
        # Extract consequences from story state (simplified)
        consequences = []
        
        # Add world flags as consequences
        world_flags = story_data.get("world_flags", {})
        for key, value in world_flags.items():
            consequences.append(ConsequenceChange(
                type="flag",
                key=key,
                value=value
            ))
        
        # Add promises as consequences
        promises = story_data.get("promises", [])
        for promise in promises:
            if promise.get("created_at_scene", 0) >= start_scene:
                consequences.append(ConsequenceChange(
                    type="promise",
                    key=promise.get("id", ""),
                    value=promise.get("description", ""),
                    npc_id=promise.get("npc_id")
                ))
        
        # Add reputation changes
        reputation = story_data.get("reputation", {})
        for trait, value in reputation.items():
            consequences.append(ConsequenceChange(
                type="reputation",
                key=trait,
                value=value
            ))
        
        # Calculate fogged branches (simplified - in reality this would be more complex)
        fogged_branches = max(0, (end_scene - start_scene + 1) * 2 - len(choices))
        
        # Calculate percent stats (placeholder)
        percent_stats = {
            "choice_popularity": 0.75  # Placeholder
        }
        
        return FlowSummaryResponse(
            scene_range=[start_scene, end_scene],
            choices=choices,
            consequences=consequences,
            fogged_branches=fogged_branches,
            percent_stats=percent_stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating flow summary: {e}")
        raise HTTPException(500, "Failed to generate flow summary")


@app.get("/ritual")
def api_ritual_get():
    """Provide a lightweight hint for clients hitting GET /ritual.
    Returns 200 with instructions instead of a 405 so dev tools don't flag errors.
    """
    return {"message": "Use POST /ritual to perform the ritual."}





