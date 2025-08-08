from npc.service import get_npc_by_id, create_default_npc, ensure_npc_profile as ensure_npc_profile_service
from db import SessionLocal
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import uuid

# Helper to map known default UUIDs to stable names
_DEF_UUID_TO_NAME_CACHE: Dict[str, str] = {}

_ADJECTIVES = [
    "brave", "quiet", "fierce", "luminous", "cunning", "steadfast", "noble", "wild",
    "clever", "valiant", "bold", "serene", "arcane", "scarlet", "silver", "golden"
]
_NOUNS = [
    "sparrow", "wolf", "warden", "sage", "ranger", "seeker", "fox", "keeper",
    "blade", "harbor", "ember", "shadow", "sun", "moon", "river", "stone"
]

def _deterministic_name_for_uuid(npc_uuid: uuid.UUID) -> str:
    """Generate a stable, human-friendly name for any UUID.
    Combines adjective + noun using the UUID's integer to keep it deterministic.
    """
    # Use the UUID int as a stable source of indices
    value = npc_uuid.int
    adj = _ADJECTIVES[value % len(_ADJECTIVES)]
    noun = _NOUNS[(value // len(_ADJECTIVES)) % len(_NOUNS)]
    # Title case nicely
    return f"{adj.capitalize()} {noun.capitalize()}"

def _friendly_name_for_uuid(npc_uuid: uuid.UUID) -> str:
    sid = str(npc_uuid)
    if sid in _DEF_UUID_TO_NAME_CACHE:
        return _DEF_UUID_TO_NAME_CACHE[sid]
    mapping = {
        str(uuid.uuid5(uuid.NAMESPACE_OID, "default:lyra")): "Lyra",
        str(uuid.uuid5(uuid.NAMESPACE_OID, "default:orin")): "Orin",
        str(uuid.uuid5(uuid.NAMESPACE_OID, "default:companion")): "Companion",
        str(uuid.uuid5(uuid.NAMESPACE_OID, "default:sage")): "Sage",
        str(uuid.uuid5(uuid.NAMESPACE_OID, "default:warrior")): "Warrior",
        str(uuid.uuid5(uuid.NAMESPACE_OID, "default:creature")): "Creature",
    }
    # Prefer mapped friendly names; otherwise deterministically synthesize one
    name = mapping.get(sid)
    if not name:
        try:
            name = _deterministic_name_for_uuid(npc_uuid)
        except Exception:
            name = sid[:8]
    _DEF_UUID_TO_NAME_CACHE[sid] = name
    return name

def ensure_npc_profile(scene: dict, player_id: str) -> None:
    """
    Guarantees every NPC referenced in the scene has an entry in npc_state.
    Supports 'npc_profile' blocks OR fallback to 'npcs_present'.
    Idempotent per player and NPC UUID.
    """
    db = SessionLocal()
    try:
        def _add_stub(npc_id: str, name: str = None, recruitable: bool = True,
                      default_trust: float = 0.3) -> None:
            # Normalize to UUID
            if isinstance(npc_id, str):
                try:
                    npc_uuid = uuid.UUID(npc_id)
                except ValueError:
                    npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:{npc_id}")
            else:
                npc_uuid = npc_id
            # Idempotent check per player_id + id
            existing_npc = get_npc_by_id(player_id, str(npc_uuid), db)
            if existing_npc is not None:
                # Upgrade legacy names that look like raw UUIDs
                try:
                    current_name = existing_npc.name or ""
                    looks_like_uuid = False
                    try:
                        looks_like_uuid = str(uuid.UUID(current_name)).lower() == current_name.lower()
                    except Exception:
                        looks_like_uuid = False
                    if looks_like_uuid:
                        existing_npc.name = _friendly_name_for_uuid(npc_uuid)
                        db.commit()
                except Exception:
                    pass
                return
            # Friendly name for known defaults
            npc_name = name or _friendly_name_for_uuid(npc_uuid)
            create_default_npc(player_id, str(npc_uuid), npc_name, db)

        # 1) explicit profile blocks
        prof_block = scene.get("npc_profile")
        profiles = prof_block if isinstance(prof_block, list) else ([prof_block] if prof_block else [])
        for prof in profiles:
            if isinstance(prof, dict) and "id" in prof:
                _add_stub(
                    prof["id"],
                    name=prof.get("name"),
                    recruitable=prof.get("recruitable", True),
                    default_trust=prof.get("default_trust", 0.3)
                )

        # 2) fallback: npcs_present array
        for npc_id in scene.get("npcs_present", []):
            if isinstance(npc_id, str):
                _add_stub(npc_id)

    finally:
        db.close()

# New-table helper left as-is
def ensure_npc_profile_new(npc_id: str, full_name: str, baseline_trust: float = 0.0) -> None:
    ensure_npc_profile_service(npc_id, full_name, baseline_trust) 