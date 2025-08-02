from npc.service import get_npc_by_id, create_default_npc
from db import SessionLocal
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import uuid

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