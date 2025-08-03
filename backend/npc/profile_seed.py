from npc.service import get_npc_by_id, create_default_npc
from npc.models import NPCState
from db import SessionLocal
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import uuid
import json
import os
from settings import settings

def get_seed_npcs() -> List[Dict[str, Any]]:
    """
    Factory function to get NPC seed data.
    If USE_FALLBACK_NPCS is True, returns fallback bundle.
    Otherwise, calls generate_dynamic_npcs() (stub for NPC06).
    """
    if settings.USE_FALLBACK_NPCS:
        return _load_fallback_npcs()
    else:
        return generate_dynamic_npcs()

def _load_fallback_npcs() -> List[Dict[str, Any]]:
    """Load fallback NPC data from JSON file"""
    fallback_path = os.path.join(os.path.dirname(__file__), '..', '..', 'dev_assets', 'fallback_npcs.json')
    try:
        with open(fallback_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Fallback NPCs file not found at {fallback_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing fallback NPCs JSON: {e}")
        return []

def generate_dynamic_npcs(
    archetype: str = "Adventurer",
    theme: str = "hero's journey",
    ask: str = "",
    seek: str = "",
    knock: str = "",
    count: int = 6
) -> List[Dict[str, Any]]:
    """
    Generate dynamic NPCs via LLM call (NPC06 implementation).
    Returns empty list if LLM generation fails.
    """
    try:
        from purpose_agents.npc_seed import generate_dynamic_npcs as llm_generate_npcs
        return llm_generate_npcs(archetype, theme, ask, seek, knock, count)
    except ImportError:
        print("Warning: purpose_agents.npc_seed not available, returning empty list")
        return []
    except Exception as e:
        print(f"Error generating dynamic NPCs: {e}")
        return []

def seed_fallback_npcs(player_id: str, db: Session = None) -> None:
    """
    Seed NPCs from fallback bundle for a player.
    Only creates NPCs that don't already exist.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True
    
    try:
        npc_data = get_seed_npcs()
        for npc_info in npc_data:
            npc_id = npc_info["id"]
            # Generate the UUID for this NPC
            npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:{npc_id}")
            existing_npc = get_npc_by_id(player_id, str(npc_uuid), db)
            if existing_npc is None:
                # Create NPC with fallback metadata from the start
                npc = NPCState(
                    id=npc_uuid,
                    player_id=player_id,
                    name=npc_info["full_name"],
                    trust=npc_info["baseline_trust"],
                    summary=npc_info.get("summary", ""),
                    portrait_url=npc_info.get("portrait_url", ""),
                    baseline_trust=npc_info["baseline_trust"],
                    meta={
                        "archetype": npc_info["archetype"],
                        "created_from_fallback": True
                    }
                )
                db.add(npc)
                db.commit()
                db.refresh(npc)
                print(f"Created fallback NPC: {npc_info['full_name']} ({npc_id})")
            else:
                print(f"NPC {npc_id} already exists, skipping")
    finally:
        if should_close_db:
            db.close()


def seed_dynamic_npcs(player_id: str, npc_data: List[Dict[str, Any]], db: Session = None) -> None:
    """
    Seed NPCs from dynamic generation for a player.
    Only creates NPCs that don't already exist.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True
    
    try:
        for npc_info in npc_data:
            npc_id = npc_info["id"]
            # Generate the UUID for this NPC
            npc_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{player_id}:{npc_id}")
            existing_npc = get_npc_by_id(player_id, str(npc_uuid), db)
            if existing_npc is None:
                # Clamp trust values to valid range
                trust_value = max(0.20, min(0.45, npc_info["baseline_trust"]))
                
                # Create NPC with dynamic metadata from the start
                npc = NPCState(
                    id=npc_uuid,
                    player_id=player_id,
                    name=npc_info["full_name"],
                    trust=trust_value,
                    summary=npc_info.get("one_line_summary", ""),
                    portrait_url=npc_info.get("portrait_url", ""),
                    baseline_trust=trust_value,
                    meta={
                        "archetype": npc_info.get("archetype", ""),
                        "role": npc_info.get("role", ""),
                        "skill_tag": npc_info.get("skill_tag", ""),
                        "created_from_dynamic": True
                    }
                )
                db.add(npc)
                db.commit()
                db.refresh(npc)
                print(f"Created dynamic NPC: {npc_info['full_name']} ({npc_id})")
            else:
                print(f"NPC {npc_id} already exists, skipping")
    finally:
        if should_close_db:
            db.close()

def ensure_npc_profile(scene: dict, player_id: str) -> None:
    """
    Guarantees every NPC referenced in the scene has an entry in npc_state.
    Supports 'npc_profile' blocks OR fallback to 'npcs_present'.
    """
    db = SessionLocal()
    try:
        def _add_stub(npc_id: str, name: str = None, recruitable: bool = True,
                      default_trust: float = 0.3) -> None:
            # Check if NPC already exists
            existing_npc = get_npc_by_id(player_id, npc_id, db)
            if existing_npc is None:
                # Create new NPC with provided or default values
                npc_name = name or npc_id.title()
                create_default_npc(player_id, npc_id, npc_name, db)
                print(f"Created NPC profile for {npc_id} ({npc_name})")

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