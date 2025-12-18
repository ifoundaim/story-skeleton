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
import uuid
from typing import Any, Union, Dict, Optional, cast, List, Set

# 4️⃣ Third-party libs
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
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
from mock_souls import seed_mock_souls
from helix_sync import helix_sync_service
from helix_client import get_helix_client
from backend.story_history.db import create_tables as create_story_history_tables, SessionLocal as StorySessionLocal
from backend.story_history.service import (
    upsert_user_by_email,
    get_active_story,
    create_story as create_story_row,
    append_event,
    get_last_event,
    list_events,
)
from backend.story.runtime_generator import (
    _load_cfg_and_beats,
    embed_text,
    generate_next_scene,
    init_state_for_new_story,
    state_from_dict,
    state_to_dict,
)
from backend.soulmap.db import SessionLocal as SoulSessionLocal
from backend.soulmap.service import apply_delta, get_soulmap_dict

# ─── Simple narrative-name extractor for binding story names to NPC IDs ───────
import re as _re
_NAME_STOPWORDS = {
    "Aim", "The", "A", "An", "City", "Neonveil", "In", "Of", "On", "At", "To",
    "With", "For", "And", "But", "Or", "If", "Then", "Else", "Their", "His", "Her",
    "Realm", "World", "Legend", "Moment", "Destiny", "Magic", "Possibilities", "Choice",
    "Journey", "Adventure", "Path", "Way", "Place", "Land", "Kingdom", "Forest",
    "Mountain", "River", "Cave", "Castle", "Village", "Town", "City", "Road",
    "Bridge", "Gate", "Door", "Window", "Tree", "Stone", "Water", "Fire", "Earth",
    "Wind", "Light", "Dark", "Shadow", "Sun", "Moon", "Star", "Sky", "Cloud",
    "Rain", "Snow", "Storm", "Thunder", "Lightning", "Time", "Day", "Night",
    "Morning", "Evening", "Dawn", "Dusk", "Hour", "Minute", "Second", "Year",
    "Month", "Week", "Season", "Spring", "Summer", "Autumn", "Winter",
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

# ─── Animal/creature mention detection for NPC binding ─────────────────────────
_ANIMAL_PHRASES = [
    # two-word specific phrases first (checked in order)
    "white wolf", "black wolf", "grey wolf", "wise owl", "snow owl",
    # single nouns
    "owl", "wolf", "fox", "raven", "eagle", "hawk", "dove", "bear",
    "lion", "tiger", "deer", "stag", "horse", "hound", "dog", "cat",
    "serpent", "dragon"
]

def _slugify(s: str) -> str:
    import re as __re
    return __re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def _detect_animal_phrase(text: str) -> str | None:
    """Detect an animal mention in free prose. Returns the matched phrase (as it
    appears) or None. Matching is case-insensitive and prefers longer phrases.
    Example: "white wolf" → "white wolf"; "owl" → "owl".
    """
    if not text:
        return None
    lowered = text.lower()
    for phrase in _ANIMAL_PHRASES:
        if phrase in lowered:
            # return phrase in original casing if possible
            try:
                import re as __re
                m = __re.search(rf"\b{phrase}\b", text, flags=__re.IGNORECASE)
                if m:
                    return m.group(0)
            except Exception:
                pass
            return phrase
    return None


# ─── File paths ───────────────────────────────────────────────────────────────
DATA_FILE   = str(BASE_DIR / "player_profile.json")
EDITOR_FILE = BASE_DIR / "editor.html"
UPLOADS_DIR = BASE_DIR.parent / "uploads"

app = FastAPI(title="SoulSeed API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import WebSocket manager
try:
    from websocket_manager import websocket_manager
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    websocket_manager = None

app.include_router(soulmap_router, prefix="/v1")
# Backward-compatible alias (tests and older clients expect /soulmap/*)
app.include_router(soulmap_router, prefix="")
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

        try:
            create_story_history_tables()
            print("✅ [main] startup: story history tables created/verified")
        except Exception as e:
            print(f"⚠️ [main] startup: failed to create story history tables: {e}")

        try:
            await helix_sync_service.start()
            print("✅ [main] startup: Helix sync service started")
        except Exception as e:
            print(f"⚠️ [main] startup: Helix sync service failed to start: {e}")

        try:
            seed_mock_souls()
            print("✅ [main] startup: mock souls seeded")
        except Exception as e:
            print(f"⚠️ [main] startup: failed to seed mock souls: {e}")

    # Ensure chat state file exists
    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await helix_sync_service.stop()

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
    # Testing-only auth wiring (optional for backward compatibility)
    userId: str | None = None
    selectedPalettes: list[str] | None = None

class SoulSeedResponse(BaseModel):
    playerId: str
    soulSeedId: str
    initSceneTag: str
    userId: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)


class LoginResponse(BaseModel):
    userId: str
    email: str

class RitualRequest(BaseModel):
    playerId: str
    askText: str = Field(..., max_length=280)
    seekText: str = Field(..., max_length=280)
    knockText: str = Field(..., max_length=280)
    theme: str
    fresh: bool = Field(default=False, description="Reset story state before regeneration")

class RitualResponse(BaseModel):
    theme: str
    intentVector: list[float]
    nextSceneTag: str

class StartRequest(BaseModel):
    soulSeedId: str
    sceneTag: Optional[str] = None

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
    soul_seed_id: str = Field(..., alias="soulSeedId")
    scene_tag: str = Field(..., alias="sceneTag")
    model_config = ConfigDict(populate_by_name=True)

class FreeTextResponse(BaseModel):
    success: bool
    choice_text: str
    mapped_text: str | None = None
    choice_tag: str | None = None
    next_scene_tag: str | None = None
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
    scene_index: int | None = None
    free_text_enabled: bool = False
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


# ─── Scene serialization helpers ───────────────────────────────────────────────
def _event_to_response(event, *, free_text_enabled: bool = True) -> SceneResponse:
    """Serialize a DB StoryEvent into the API response shape expected by the frontend."""
    # event.choices are stored as [{tag,label}]
    choices = []
    for c in (event.choices or []):
        if isinstance(c, dict):
            choices.append({"tag": str(c.get("tag", "")), "label": str(c.get("label", ""))})
    return SceneResponse(
        sceneTag=str(event.scene_tag),
        text=str(event.scene_text),
        choices=choices,
        media=MediaAssets(images=[], audio=[]),
        scene_index=int(event.idx),
        free_text_enabled=bool(free_text_enabled),
        npcs_present=list(event.npcs_present or []),
        beat_id=event.beat_id,
        beat_tags=list(event.beat_tags or []),
        scene_phase=None,
        soulmap_delta=event.soulmap_delta,
    )


def _normalize_soulmap_delta(raw: Any) -> dict[str, float] | None:
    """Normalize various soulmap delta shapes into a trait->float dict."""
    if isinstance(raw, dict):
        return {k: float(v) for k, v in raw.items() if isinstance(v, (int, float))}
    if isinstance(raw, list) and len(raw) == 64:
        from soulmap.mapping import SoulTrait

        delta_dict: dict[str, float] = {}
        for trait in SoulTrait:
            if trait.value < len(raw):
                delta_dict[trait.name] = float(raw[trait.value])
        return delta_dict
    return None


async def _infer_and_apply_soulmap_delta(
    player_id: str,
    choice_text: str,
    scene_text: str,
) -> dict[str, float] | None:
    """Infer soulmap delta from context and persist it; returns the applied delta dict."""
    if not player_id:
        return None

    soulmap_delta: dict[str, float] | None = None

    # Collect context (best-effort; keep failures non-fatal)
    emotion_state = {}
    try:
        from emotion.models import get_emotion_state

        emotion_state = get_emotion_state(player_id)
    except Exception as e:  # pragma: no cover - defensive
        print(f"⚠️ [main] Could not get emotion state: {e}", flush=True)

    trust_levels = {}
    try:
        from npc.service import get_npc_states

        npc_states = get_npc_states(player_id)
        trust_levels = {npc.name: npc.trust for npc in npc_states if hasattr(npc, "trust")}
    except Exception as e:  # pragma: no cover - defensive
        print(f"⚠️ [main] Could not get NPC trust levels: {e}", flush=True)

    memory_recap = ""
    try:
        from codex.memory import get_memory_recap

        memory_recap = get_memory_recap(player_id)
    except Exception as e:  # pragma: no cover - defensive
        print(f"⚠️ [main] Could not get memory recap: {e}", flush=True)

    # Enqueue inference and wait briefly for a result
    try:
        task_id = await codex_router.enqueue_soulmap_inference(
            player_id=player_id,
            choice_text=choice_text,
            scene_text=scene_text,
            emotion_state=emotion_state,
            trust_levels=trust_levels,
            memory_recap=memory_recap,
        )
        print(f"🧠 [main] Enqueued soulmap inference task {task_id} for player={player_id}", flush=True)

        import asyncio

        max_wait = 10.0
        wait_time = 0.0
        while wait_time < max_wait:
            result = codex_router.get_soulmap_task_result(task_id)
            if result:
                soulmap_delta = _normalize_soulmap_delta(result)
                if soulmap_delta:
                    print(f"✅ [main] Got soulmap delta from inference: {soulmap_delta}", flush=True)
                    break
            await asyncio.sleep(0.5)
            wait_time += 0.5
            print(f"🧠 [main] Waiting for soulmap inference... ({wait_time}s)", flush=True)
        if wait_time >= max_wait and soulmap_delta is None:
            print(f"⚠️ [main] Soulmap inference timeout for player={player_id}", flush=True)
    except Exception as e:  # pragma: no cover - defensive
        print(f"❌ [main] Failed to enqueue/resolve soulmap inference: {e}", flush=True)

    if soulmap_delta:
        db = SoulSessionLocal()
        try:
            apply_delta(db, player_id, soulmap_delta)
        except Exception as e:  # pragma: no cover - defensive
            print(f"⚠️ [main] Applying soulmap delta failed: {e}", flush=True)
        finally:
            db.close()

    return soulmap_delta

def normalize_choices(choices: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize choices to ensure they all have proper 'text' fields."""
    if not isinstance(choices, dict):
        return {}
    
    normalized = {}
    choice_templates = [
        "Continue forward",
        "Take a different path", 
        "Seek more information",
        "Reflect on your choices",
        "Press onward",
        "Explore further"
    ]
    
    for idx, (key, value) in enumerate(choices.items()):
        # Skip special keys
        if key in ("free_text_enabled", "_meta"):
            normalized[key] = value
            continue
        
        if isinstance(value, dict):
            # Ensure dict has "text" field
            if "text" not in value or not str(value.get("text", "")).strip():
                template_idx = idx % len(choice_templates)
                value["text"] = choice_templates[template_idx]
            normalized[key] = value
        elif isinstance(value, str):
            # Convert string choice to dict format
            template_idx = idx % len(choice_templates)
            normalized[key] = {
                "text": choice_templates[template_idx],
                "next": value
            }
        else:
            # Fallback: create dict with template text
            template_idx = idx % len(choice_templates)
            normalized[key] = {
                "text": choice_templates[template_idx],
                "next": str(value) if value else ""
            }
    
    return normalized


def scene_to_response(
    scene_tag: str,
    tree: Dict[str, Any],
    player_id: str = "",
    story_data: Optional[Dict[str, Any]] = None,
    soulmap_delta: Optional[Dict[str, float]] = None,
) -> SceneResponse:
    """Serialize a scene dictionary into the API response model."""
    if not tree or scene_tag not in tree:
        raise HTTPException(404, f"Scene '{scene_tag}' not found")

    scene = tree.get(scene_tag) or {}
    media_data = scene.get("media") or {}
    media = MediaAssets(
        images=list(media_data.get("images", [])),
        audio=list(media_data.get("audio", [])),
    )

    # Normalize choices before serialization
    raw_choices = scene.get("choices") or {}
    normalized_choices = normalize_choices(raw_choices)
    
    # Update scene with normalized choices (for persistence)
    scene["choices"] = normalized_choices
    
    # Default to allowing free-text unless explicitly disabled
    free_text_enabled_raw = normalized_choices.get("free_text_enabled")
    free_text_enabled = False if free_text_enabled_raw is False else True

    # Serialize to response format
    choices: list[dict[str, str]] = []
    for raw_key, raw_val in normalized_choices.items():
        # Skip special keys
        if raw_key in ("free_text_enabled", "_meta"):
            continue
        
        if isinstance(raw_val, dict):
            label = str(raw_val.get("text", f"Choice {raw_key}")).strip()
        else:
            label = str(raw_val) if raw_val else f"Choice {raw_key}"
        
        if not label:
            label = f"Choice {raw_key}"
        
        choices.append({"tag": str(raw_key), "text": label})

    response = SceneResponse(
        sceneTag=scene_tag,
        text=scene.get("text", ""),
        choices=choices,
        media=media,
        scene_index=scene.get("scene_index"),
        free_text_enabled=free_text_enabled,
        npc_text_dynamic=scene.get("npc_text_dynamic"),
        npc_dialogue=list(scene.get("npc_dialogue", [])),
        dialogue_type=scene.get("dialogue_type", "single"),
        npcs_present=list(scene.get("npcs_present", [])),
        soulmap_delta=soulmap_delta,
        beat_id=scene.get("beat_id"),
        beat_tags=list(scene.get("beat_tags", [])),
        scene_phase=scene.get("scene_phase"),
    )

    if story_data is not None:
        story_data["last_scene_tag"] = scene_tag
        story_data["last_response_at"] = datetime.utcnow().isoformat()

    return response


def _scene_to_response(*args, **kwargs) -> SceneResponse:
    """Backward-compatible alias for existing imports/tests."""
    return scene_to_response(*args, **kwargs)


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
@app.post("/auth/login", response_model=LoginResponse)
async def api_login(payload: LoginRequest) -> LoginResponse:
    """Testing-only login: enter email, get userId (no verification)."""
    email = (payload.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")
    db = StorySessionLocal()
    try:
        user = upsert_user_by_email(db, email)
        return LoginResponse(userId=str(user.id), email=user.email)
    except Exception as exc:
        # Convert DB connection failures into a clear, actionable error.
        try:
            from sqlalchemy.exc import OperationalError
            if isinstance(exc, OperationalError):
                raise HTTPException(
                    status_code=503,
                    detail="Database unavailable. Start Postgres with `docker-compose up -d db` (or ensure POSTGRES_URL points to a running Postgres).",
                )
        except HTTPException:
            raise
        raise
    finally:
        db.close()

@app.post("/soulseed", response_model=SoulSeedResponse)
async def create_player_profile(request: PlayerProfileIn) -> SoulSeedResponse:
    """Create a new player profile and return soul seed information."""
    try:
        print(f"📥 [main] /soulseed request received: playerName={request.playerName}, preset={request.archetypePreset}, custom={request.archetypeCustom}")
        player_id = slugify(request.playerName)
        archetype = request.archetypeCustom or request.archetypePreset
        soul_seed_id = make_soul_seed_id(request.playerName, archetype)

        profiles = _read_json(str(DATA_FILE), {})
        profiles[player_id] = {
            "playerName": request.playerName,
            "archetype": archetype,
            "soulSeedId": soul_seed_id,
            "userId": request.userId,
            "selectedPalettes": request.selectedPalettes or [],
        }
        _write_json(str(DATA_FILE), profiles)

        print(f"✅ [main] Created profile for player_id={player_id}, soulSeedId={soul_seed_id}")

        return SoulSeedResponse(
            playerId=player_id,
            soulSeedId=soul_seed_id,
            initSceneTag="tag_001",  # Updated to use new 30-scene framework
            userId=request.userId,
        )
    except Exception as e:
        print(f"❌ [main] Failed to create player profile: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")

@app.post("/avatar/upload")
async def avatar_upload(playerId: str = Form(...), file: UploadFile = File(...)) -> dict[str, str]:
    """Upload an avatar image for a player."""
    try:
        dest_dir = UPLOADS_DIR / playerId
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Get file extension
        file_ext = Path(file.filename).suffix if file.filename else ".jpg"
        dest = dest_dir / f"orig_001{file_ext}"
        
        # Read and write file
        content = await file.read()
        dest.write_bytes(content)
        
        # Return URL that matches the static mount
        url = f"/static/{playerId}/{dest.name}"
        print(f"✅ [main] Uploaded avatar for playerId={playerId} to {dest}")
        
        return {"url": url}
    except Exception as e:
        print(f"❌ [main] Failed to upload avatar: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")

@app.post("/ritual", response_model=RitualResponse)
@app.post("/api/ritual", response_model=RitualResponse)
async def api_ritual(payload: RitualRequest) -> RitualResponse:
    print(f"🔮 [main] /ritual payload={payload.json()}")

    profiles = _read_json(str(DATA_FILE), {})
    profile = profiles.get(payload.playerId)
    if not profile:
        raise HTTPException(status_code=404, detail="Player profile not found. Please create an avatar first.")

    soul_seed_id = profile.get("soulSeedId")
    if not soul_seed_id:
        raise HTTPException(status_code=400, detail="Player is missing a soul seed. Please recreate the avatar.")

    player_name = profile.get("playerName", payload.playerId)

    # --- standard ritual flow ---
    try:
        ritual_result = await ritual.record(
            payload.playerId,
            payload.askText,
            payload.seekText,
            payload.knockText,
            payload.theme,
        )
        ritual_theme = ritual_result.get("theme", payload.theme) if isinstance(ritual_result, dict) else payload.theme
        raw_vector = ritual_result.get("intentVector", []) if isinstance(ritual_result, dict) else []
        intent_vector = [float(v) for v in raw_vector if isinstance(v, (int, float))]
    except Exception as exc:
        print(f"⚠️ [main] ritual.record failed: {exc}")
        ritual_theme = payload.theme
        intent_vector = []

    # Create / restart a dynamic story (Postgres-backed)
    cfg, _ = _load_cfg_and_beats()

    def _extract_hooks(text: str) -> list[str]:
        import re as _re
        tokens = _re.findall(r"[A-Za-z]+", (text or "").lower())
        stop = {"and", "the", "of", "to", "a", "in", "on", "for", "with", "by", "at"}
        out: list[str] = []
        for t in tokens:
            if t in stop or len(t) < 3:
                continue
            if t not in out:
                out.append(t)
            if len(out) >= 12:
                break
        return out

    world_hooks = list(
        {
            *_extract_hooks(ritual_theme),
            *_extract_hooks(payload.askText),
            *_extract_hooks(payload.seekText),
            *_extract_hooks(payload.knockText),
        }
    )

    # Bootstrap NPC roster for state
    try:
        from backend.npc.dynamic_generator import generate_story_npcs
        npcs = await generate_story_npcs(
            player_id=payload.playerId,
            player_name=player_name,
            player_archetype=str(profile.get("archetype") or "Hero"),
            story_theme=ritual_theme,
            num_npcs=5,
        )
        npc_state = {}
        for npc in npcs:
            npc_state[str(npc.id)] = {
                "full_name": npc.full_name,
                "role": npc.role,
                "trust": float(getattr(npc, "trust", 0.3) or 0.3),
                "arc_state": "intro",
                "interactions": 0,
                "last_invite_scene": None,
            }
    except Exception as exc:
        print(f"⚠️ [main] NPC bootstrap failed: {exc}")
        npc_state = {}

    state_obj = init_state_for_new_story(
        cfg=cfg,
        player_name=player_name,
        theme=ritual_theme,
        archetype=str(profile.get("archetype") or "Hero"),
        world_hooks=world_hooks,
        npcs=npc_state,
    )

    user_id = profile.get("userId")
    if not user_id:
        # Backward-compatible fallback for sessions that didn't go through login yet
        tmp = StorySessionLocal()
        try:
            user_id = str(upsert_user_by_email(tmp, f"{payload.playerId}@local.test").id)
        finally:
            tmp.close()
        profile["userId"] = user_id
        profiles[payload.playerId] = profile
        _write_json(str(DATA_FILE), profiles)

    selected_palettes = list(profile.get("selectedPalettes") or [])

    db = StorySessionLocal()
    try:
        story_row = create_story_row(
            db,
            user_id=uuid.UUID(user_id),
            player_id=payload.playerId,
            soul_seed_id=soul_seed_id,
            selected_palettes=selected_palettes,
            ritual_inputs={
                "askText": payload.askText,
                "seekText": payload.seekText,
                "knockText": payload.knockText,
                "theme": ritual_theme,
            },
            runtime_state=state_to_dict(state_obj),
        )

        # Generate first scene
        soul_db = SoulSessionLocal()
        try:
            soul_traits = get_soulmap_dict(soul_db, payload.playerId)
        finally:
            soul_db.close()

        rng_seed = f"{payload.playerId}:{soul_seed_id}:{ritual_theme}"
        next_state, scene_payload = await generate_next_scene(
            state=state_obj,
            player_id=payload.playerId,
            player_name=player_name,
            selected_palettes=selected_palettes,
            continuity_snippets=[],
            npc_memory_snippets=[],
            rng_seed=rng_seed,
            soul_traits=soul_traits,
        )

        # Persist updated runtime state
        story_row.runtime_state = state_to_dict(next_state)
        story_row.updated_at = datetime.utcnow()
        db.add(story_row)
        db.commit()
        db.refresh(story_row)

        moment = f"SCENE: {scene_payload['scene_text']}"
        moment_vec = await embed_text(moment)

        event = append_event(
            db,
            story=story_row,
            idx=int(scene_payload.get("idx", 0)),
            scene_tag=scene_payload["scene_tag"],
            scene_text=scene_payload["scene_text"],
            choices=scene_payload["choices"],
            beat_id=scene_payload["beat_id"],
            beat_tags=scene_payload["beat_tags"],
            npcs_present=scene_payload["npcs_present"],
            selected_choice_text=None,
            selected_choice_tag=None,
            soulmap_delta=None,
            moment_vec=moment_vec,
        )

        return RitualResponse(theme=ritual_theme, intentVector=intent_vector, nextSceneTag=str(event.scene_tag))
    finally:
        db.close()


@app.post("/start")
async def api_start(req: StartRequest) -> SceneResponse:
    """Return the current scene for the given soul seed (dynamic runtime story)."""
    db = StorySessionLocal()
    try:
        story = get_active_story(db, req.soulSeedId)
        if not story:
            raise HTTPException(status_code=404, detail="No story found for this soulSeedId. Perform the ritual first.")
        event = get_last_event(db, story)
        if not event:
            raise HTTPException(status_code=404, detail="Story has no scenes yet. Perform the ritual again.")
        return _event_to_response(event, free_text_enabled=True)
    finally:
        db.close()


def _legacy_patch_story_tree(story_dict, player_name: str = "Adventurer"):
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


async def _legacy_choose_py(req: ChoiceRequest):
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
            tree = _legacy_patch_story_tree(tree, player_name)
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
    if USE_HELIX_FOR_SCENE_SELECTION and player_id:
        allowed_tags = set(str_key_map.values())
        helix_tag = _suggest_next_scene_with_helix(player_id, allowed_tags, profiles, state)
        if helix_tag and helix_tag in allowed_tags:
            print(f"✨ [helix] Overriding next_tag {next_tag} -> {helix_tag} for player {player_id}")
            next_tag = helix_tag
    print(f"✅ [main] next sceneTag={next_tag}", flush=True)
    # Defensive patch again in case new tags are referenced
    tree = _legacy_patch_story_tree(tree, player_name)
    
    # Normalize choices in the story tree
    for scene_tag, scene_data in tree.items():
        if isinstance(scene_data, dict) and "choices" in scene_data:
            scene_data["choices"] = normalize_choices(scene_data["choices"])
    
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
    
    # Apply trust deltas and emit toasts (fallback path integration)
    if legacy_trust_delta != 0.0 or npc_trust_deltas:
        try:
            from npc.service import apply_trust, apply_trust_to_multiple, get_npc_by_id
            from backend.db import SessionLocal
            from story.telemetry import log_toast_emitted
            import asyncio as _asyncio
            import uuid as _uuid
            db = SessionLocal()
            
            # Apply legacy trust delta to default companion
            if legacy_trust_delta != 0.0:
                companion_uuid = _uuid.uuid5(_uuid.NAMESPACE_OID, f"default:companion")
                apply_trust(player_id, str(companion_uuid), legacy_trust_delta, db)
                print(f"[main] Applied legacy trust delta {legacy_trust_delta} to companion")
                # Emit toast for legacy trust delta
                if WEBSOCKET_AVAILABLE and websocket_manager is not None:
                    label = "Companion trust"
                    try:
                        npc_obj = get_npc_by_id(player_id, str(companion_uuid), db)
                        if npc_obj and getattr(npc_obj, "name", None):
                            label = f"Trust with {npc_obj.name}"
                    except Exception:
                        pass
                    try:
                        current_scene = tree.get(req.sceneTag, {}) or {}
                        scene_index = int(current_scene.get("scene_index", 0))
                    except Exception:
                        scene_index = 0
                    _asyncio.create_task(websocket_manager.emit_consequence_toast(
                        kind="reputation_shift", label=label, delta=float(legacy_trust_delta), npc_id=str(companion_uuid)
                    ))
                    try:
                        log_toast_emitted(scene_index=scene_index, kind="reputation_shift", label=label, npc_id=str(companion_uuid), delta=float(legacy_trust_delta))
                    except Exception:
                        pass
            
            # Apply multi-NPC trust deltas
            if npc_trust_deltas:
                apply_trust_to_multiple(player_id, npc_trust_deltas, db)
                print(f"[main] Applied multi-NPC trust deltas: {npc_trust_deltas}")
                # Emit a toast per NPC
                for nid, d in npc_trust_deltas.items():
                    label = "Trust changed"
                    try:
                        npc_obj = get_npc_by_id(player_id, str(nid), db)
                        if npc_obj and getattr(npc_obj, "name", None):
                            label = f"Trust with {npc_obj.name}"
                    except Exception:
                        pass
                    try:
                        current_scene = tree.get(req.sceneTag, {}) or {}
                        scene_index = int(current_scene.get("scene_index", 0))
                    except Exception:
                        scene_index = 0
                    if WEBSOCKET_AVAILABLE and websocket_manager is not None:
                        _asyncio.create_task(websocket_manager.emit_consequence_toast(
                            kind="reputation_shift", label=label, delta=float(d), npc_id=str(nid)
                        ))
                    try:
                        log_toast_emitted(scene_index=scene_index, kind="reputation_shift", label=label, npc_id=str(nid), delta=float(d))
                    except Exception:
                        pass
            
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
                from backend.db import SessionLocal
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
            from backend.db import SessionLocal
            
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

    state["stories"][req.soulSeedId] = story_data
    _write_json(str(STATE_FILE), state)
    print(f"🟢 [main] Returning response for soulSeedId={req.soulSeedId}, nextTag={next_tag}", flush=True)
    return scene_to_response(next_tag, tree, player_id=player_id, story_data=story_data, soulmap_delta=soulmap_delta)


# ─── Legacy story-tree stubs (dynamic runtime generation) ─────────────────────
def patch_story_tree(story_dict, player_name: str = "Adventurer"):
    """No-op: static story-tree patching has been retired."""
    return story_dict


async def _choose_py(req: ChoiceRequest):
    """Hard-fail if an old codepath tries to call the tree-based chooser."""
    raise HTTPException(status_code=410, detail="Legacy tree-based choose path removed; use dynamic runtime /choose.")

# ────────────────────────────── choice endpoint ──────────────────────────────
@app.post("/choice")
@app.post("/choose")
async def api_choose(req: ChoiceRequest = Body(...)):
    """Advance the dynamic runtime story and return the next scene."""
    try:
        chosen_val = str(req.choice_val)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db = StorySessionLocal()
    try:
        story = get_active_story(db, req.soulSeedId)
        if not story:
            raise HTTPException(status_code=404, detail="No story found for this soulSeedId. Perform the ritual first.")

        last_event = get_last_event(db, story)
        if not last_event:
            raise HTTPException(status_code=404, detail="Story has no scenes yet. Perform the ritual again.")

        # Map choice tag -> choice label text
        selected_choice_text = chosen_val
        for c in (last_event.choices or []):
            if isinstance(c, dict) and str(c.get("tag")) == chosen_val:
                selected_choice_text = str(c.get("label") or chosen_val)
                break

        # Load runtime state
        state_obj = state_from_dict(story.runtime_state or {})
        player_name = str((state_obj.player or {}).get("name") or story.player_id)
        state_obj.flags["last_choice_text"] = selected_choice_text

        # Simple continuity: last few scenes + their chosen actions
        recent = list_events(db, story, limit=6)
        continuity_snippets = []
        for ev in reversed(recent):
            snippet = (ev.scene_text or "").strip().replace("\n", " ")
            if snippet:
                continuity_snippets.append(snippet[:160])
        continuity_snippets.append(f"Player chose: {selected_choice_text}")

        # NPC memory grounding: most recent mention of any NPC
        npc_memory_snippets = []
        for ev in recent:
            if ev.npcs_present:
                npc_memory_snippets.append((ev.scene_text or "").strip().replace("\n", " ")[:160])
                break

        # Soulmap traits drive beat/choice weighting
        soul_db = SoulSessionLocal()
        try:
            soul_traits = get_soulmap_dict(soul_db, story.player_id)
        finally:
            soul_db.close()

        rng_seed = f"{story.id}:{state_obj.scene_index}:{selected_choice_text}"
        next_state, scene_payload = await generate_next_scene(
            state=state_obj,
            player_id=story.player_id,
            player_name=player_name,
            selected_palettes=list(story.selected_palettes or []),
            continuity_snippets=continuity_snippets,
            npc_memory_snippets=npc_memory_snippets,
            rng_seed=rng_seed,
            soul_traits=soul_traits,
        )

        story.runtime_state = state_to_dict(next_state)
        story.updated_at = datetime.utcnow()
        db.add(story)
        db.commit()
        db.refresh(story)

        scene_text = str(last_event.scene_text or "")
        moment = f"SCENE: {scene_payload['scene_text']}\nCHOICE: {selected_choice_text}"
        moment_vec = await embed_text(moment)

        soulmap_delta: dict[str, float] | None = None
        try:
            raw_delta = scene_payload.get("soulmap_delta")
            if raw_delta is not None:
                soulmap_delta = _normalize_soulmap_delta(raw_delta)
                if soulmap_delta:
                    db_soul = SoulSessionLocal()
                    try:
                        apply_delta(db_soul, story.player_id, soulmap_delta)
                    finally:
                        db_soul.close()
                    print(f"✅ [main] Applied provided soulmap delta for player={story.player_id}", flush=True)
            if soulmap_delta is None:
                soulmap_delta = await _infer_and_apply_soulmap_delta(
                    player_id=story.player_id,
                    choice_text=selected_choice_text,
                    scene_text=scene_text,
                )
        except Exception as e:  # pragma: no cover - defensive
            print(f"⚠️ [main] Soulmap integration failed for player={story.player_id}: {e}", flush=True)

        event = append_event(
            db,
            story=story,
            idx=int(scene_payload.get("idx", 0)),
            scene_tag=scene_payload["scene_tag"],
            scene_text=scene_payload["scene_text"],
            choices=scene_payload["choices"],
            beat_id=scene_payload.get("beat_id"),
            beat_tags=scene_payload.get("beat_tags") or [],
            npcs_present=scene_payload.get("npcs_present") or [],
            selected_choice_text=selected_choice_text,
            selected_choice_tag=chosen_val,
            soulmap_delta=soulmap_delta,
            moment_vec=moment_vec,
        )

        return _event_to_response(event, free_text_enabled=True)
    finally:
        db.close()


@app.post("/choices/free", response_model=SceneResponse)
async def api_free_text(req: FreeTextRequest = Body(...)) -> SceneResponse:
    """Process free-text input and advance the dynamic runtime story."""
    flag_enabled = should_enable_free_text(req.scene_index)
    if not flag_enabled:
        raise HTTPException(status_code=400, detail="Free-text is not enabled for this scene")

    sanitized_text = (req.user_text or "").strip()
    if not sanitized_text or len(sanitized_text) < 3:
        raise HTTPException(status_code=400, detail="Text too short or empty")

    inappropriate_words = ["kill", "murder", "hate", "destroy", "attack", "fight", "hurt"]
    if any(word in sanitized_text.lower() for word in inappropriate_words):
        raise HTTPException(status_code=400, detail="Content contains inappropriate language")

    transformed_text = sanitized_text
    if os.getenv("OPENAI_API_KEY"):
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            prompt = f"""Transform this user input into a safe, contextual story action (1 sentence).\nUser input: \"{sanitized_text}\"\nReturn only the transformed text."""
            response = await client.chat.completions.create(
                model=os.getenv("STORY_SCENE_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=80,
            )
            transformed_text = (response.choices[0].message.content or "").strip() or sanitized_text
            if len(transformed_text) > 220:
                transformed_text = transformed_text[:220]
        except Exception:
            transformed_text = sanitized_text

    db = StorySessionLocal()
    try:
        story = get_active_story(db, req.soul_seed_id)
        if not story:
            raise HTTPException(status_code=404, detail="No story found for this soulSeedId. Perform the ritual first.")
        last_event = get_last_event(db, story)
        if not last_event:
            raise HTTPException(status_code=404, detail="Story has no scenes yet. Perform the ritual again.")

        state_obj = state_from_dict(story.runtime_state or {})
        player_name = str((state_obj.player or {}).get("name") or story.player_id)
        state_obj.flags["last_choice_text"] = transformed_text

        recent = list_events(db, story, limit=6)
        continuity_snippets = []
        for ev in reversed(recent):
            snippet = (ev.scene_text or "").strip().replace("\n", " ")
            if snippet:
                continuity_snippets.append(snippet[:160])
        continuity_snippets.append(f"Player chose: {transformed_text}")

        npc_memory_snippets = []
        for ev in recent:
            if ev.npcs_present:
                npc_memory_snippets.append((ev.scene_text or "").strip().replace("\n", " ")[:160])
                break

        soul_db = SoulSessionLocal()
        try:
            soul_traits = get_soulmap_dict(soul_db, story.player_id)
        finally:
            soul_db.close()

        rng_seed = f"{story.id}:{state_obj.scene_index}:{transformed_text}"
        next_state, scene_payload = await generate_next_scene(
            state=state_obj,
            player_id=story.player_id,
            player_name=player_name,
            selected_palettes=list(story.selected_palettes or []),
            continuity_snippets=continuity_snippets,
            npc_memory_snippets=npc_memory_snippets,
            rng_seed=rng_seed,
            soul_traits=soul_traits,
        )

        story.runtime_state = state_to_dict(next_state)
        story.updated_at = datetime.utcnow()
        db.add(story)
        db.commit()
        db.refresh(story)

        scene_text = str(last_event.scene_text or "")
        moment = f"SCENE: {scene_payload['scene_text']}\nCHOICE: {transformed_text}"
        moment_vec = await embed_text(moment)

        soulmap_delta: dict[str, float] | None = None
        try:
            raw_delta = scene_payload.get("soulmap_delta")
            if raw_delta is not None:
                soulmap_delta = _normalize_soulmap_delta(raw_delta)
                if soulmap_delta:
                    db_soul = SoulSessionLocal()
                    try:
                        apply_delta(db_soul, story.player_id, soulmap_delta)
                    finally:
                        db_soul.close()
                    print(f"✅ [main] Applied provided soulmap delta for player={story.player_id}", flush=True)
            if soulmap_delta is None:
                soulmap_delta = await _infer_and_apply_soulmap_delta(
                    player_id=story.player_id,
                    choice_text=transformed_text,
                    scene_text=scene_text,
                )
        except Exception as e:  # pragma: no cover - defensive
            print(f"⚠️ [main] Soulmap integration failed for player={story.player_id}: {e}", flush=True)

        event = append_event(
            db,
            story=story,
            idx=int(scene_payload.get("idx", 0)),
            scene_tag=scene_payload["scene_tag"],
            scene_text=scene_payload["scene_text"],
            choices=scene_payload["choices"],
            beat_id=scene_payload.get("beat_id"),
            beat_tags=scene_payload.get("beat_tags") or [],
            npcs_present=scene_payload.get("npcs_present") or [],
            selected_choice_text=transformed_text,
            selected_choice_tag="free_text",
            soulmap_delta=soulmap_delta,
            moment_vec=moment_vec,
        )

        return _event_to_response(event, free_text_enabled=True)
    finally:
        db.close()


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
            from backend.db import SessionLocal
            from backend.npc.service import get_state
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
    # No legacy fallback: default to 0.0 if trust cannot be resolved
    print("✅ [main] /trust (default) -> 0.0")
    return {"trust": 0.0}


@app.post("/reset")
def api_reset(soulSeedId: str | None = Form(default=None)) -> dict[str, bool]:
    # Legacy endpoint kept for backwards compatibility with older clients.
    # The dynamic runtime story engine no longer uses a local "player_state.json".
    if soulSeedId is None:
        raise HTTPException(status_code=400, detail="Missing soulSeedId")
    raise HTTPException(status_code=410, detail="Legacy /reset removed; use /restart + ritual to start a new story.")


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
    raise HTTPException(status_code=410, detail="Legacy /resume removed; use /start to load the current story scene.")

class RestartRequest(BaseModel):
    soulSeedId: str

@app.post("/restart")
def api_restart(req: RestartRequest):
    db = StorySessionLocal()
    try:
        from backend.story_history.models import Story
        story = (
            db.query(Story)
            .filter(Story.soul_seed_id == req.soulSeedId)
            .filter(Story.status == "active")
            .order_by(Story.updated_at.desc())
            .first()
        )
        if story:
            story.status = "archived"
            story.updated_at = datetime.utcnow()
            db.commit()
        return {"restarted": True}
    finally:
        db.close()

@app.get("/memory/{player_id}")
def api_memory(player_id: str):
    db = StorySessionLocal()
    try:
        from backend.story_history.models import Story
        story = (
            db.query(Story)
            .filter(Story.player_id == player_id)
            .order_by(Story.updated_at.desc())
            .first()
        )
        if not story:
            return {"recap": "No memory recap available for this player yet."}

        events = list_events(db, story, limit=10)
        if not events:
            return {"recap": "No memory recap available for this player yet."}

        # Simple recap from recent events (new runtime generator already embeds events for richer retrieval)
        lines: list[str] = []
        for ev in events:
            if ev.scene_text:
                lines.append((ev.scene_text or "").strip())
            if ev.selected_choice_text:
                lines.append(f"You chose: {ev.selected_choice_text}")
        recap = "\n\n".join(lines[-12:]).strip()
        return {"recap": recap or "No memory recap available for this player yet."}
    finally:
        db.close()

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
        from backend.story_history.models import Story, StoryEvent

        # Calculate scene range for this chapter (assuming ~10 scenes per chapter)
        scenes_per_chapter = 10
        start_scene = max(0, (int(chapter) - 1) * scenes_per_chapter)
        end_scene = start_scene + scenes_per_chapter - 1

        db = StorySessionLocal()
        try:
            story = (
                db.query(Story)
                .filter(Story.player_id == player_id)
                .order_by(Story.updated_at.desc())
                .first()
            )
            if not story:
                raise HTTPException(404, "No story found for this player")

            events_in_range = (
                db.query(StoryEvent)
                .filter(StoryEvent.story_id == story.id)
                .filter(StoryEvent.idx >= start_scene)
                .filter(StoryEvent.idx <= end_scene)
                .order_by(StoryEvent.idx.asc())
                .all()
            )

            choices: list[ChoiceRecord] = []
            consequences: list[ConsequenceChange] = []

            for ev in events_in_range:
                if ev.selected_choice_text:
                    choices.append(
                        ChoiceRecord(
                            scene_index=int(ev.idx),
                            text=str(ev.selected_choice_text),
                            tags=list(ev.beat_tags or []),
                            effects={},
                        )
                    )

                if isinstance(ev.soulmap_delta, dict) and ev.soulmap_delta:
                    for k, v in ev.soulmap_delta.items():
                        consequences.append(
                            ConsequenceChange(
                                type="soulmap",
                                key=str(k),
                                value=float(v),
                                delta=float(v),
                            )
                        )
        finally:
            db.close()
        
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


@app.post("/admin/reset_story")
def api_reset_story(player_id: str):
    """Reset story state for a player (clears session-tree + player_state cache).
    Safe for testing - only clears cache, doesn't affect persistent data.
    """
    try:
        db = StorySessionLocal()
        try:
            from backend.story_history.models import Story
            story = (
                db.query(Story)
                .filter(Story.player_id == player_id)
                .filter(Story.status == "active")
                .order_by(Story.updated_at.desc())
                .first()
            )
            if not story:
                raise HTTPException(404, "No active story found for player")
            story.status = "archived"
            story.updated_at = datetime.utcnow()
            db.commit()
            return {"message": f"Story archived for player {player_id}", "soul_seed_id": story.soul_seed_id}
        finally:
            db.close()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resetting story state: {e}")
        raise HTTPException(500, "Failed to reset story state")


@app.get("/ritual")
def api_ritual_get():
    """Provide a lightweight hint for clients hitting GET /ritual.
    Returns 200 with instructions instead of a 405 so dev tools don't flag errors.
    """
    return {"message": "Use POST /ritual to perform the ritual."}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time consequence feedback."""
    if not WEBSOCKET_AVAILABLE:
        await websocket.close(code=1008, reason="WebSocket not available")
        return
    
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # For now, just echo back - could be extended for player-specific features
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)





