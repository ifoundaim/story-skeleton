from __future__ import annotations

import json
import os
import random
import pathlib
import re
from typing import Any, Dict, List, Tuple

import yaml

from backend.story.state import StoryState
from backend.story.beat_dsl import evaluate_preconditions, apply_effects
from backend.story.director import select_next_beat
from backend.story.telemetry import log_scene_decision
from backend.npc.scheduler import schedule_npcs_for_beat
from backend.npc.dynamic_generator import generate_story_npcs
from backend.npc.personality import build_personality
from .scene_llm_writer import write_scene_prose


def generate_scene_text(beat: Dict[str, Any], npcs_present: List[str], state: StoryState, player_name: str) -> str:
    """Generate NPC-aware story text using templates or fallback descriptions."""
    
    # Get NPC details for present NPCs
    npc_details = []
    for nid in npcs_present:
        npc_data = state.npcs.get(nid, {})
        npc_details.append({
            "id": nid,
            "name": npc_data.get("full_name", "Unknown"),
            "role": npc_data.get("role", "Companion"),
            "trust": npc_data.get("trust", 0.3),
            "interactions": npc_data.get("interactions", 0),
        })
    
    # Check if beat has custom prose templates (future enhancement)
    templates = beat.get("prose_templates", [])
    if templates:
        # Use template-based generation (to be implemented)
        template = random.choice(templates)
        return substitute_npc_variables(template, npc_details, state, player_name)
    
    # Fallback: Generate contextual text based on beat type and NPCs
    beat_id = beat.get("id", "unknown")
    tags = beat.get("tags", [])
    
    # Generate base scene text based on beat type
    if "mentor" in tags and any(npc["role"] == "Mentor" for npc in npc_details):
        mentor = next(npc for npc in npc_details if npc["role"] == "Mentor")
        return f"{mentor['name']}, a wise mentor, steps forward with ancient knowledge gleaming in weathered eyes. '{player_name}, the path ahead requires courage and wisdom.'"
    
    elif "bond" in tags and npc_details:
        if len(npc_details) == 1:
            npc = npc_details[0]
            return f"Around the flickering campfire, {npc['name']} shares stories of distant lands. The bond between you grows stronger through shared experiences and mutual trust."
        else:
            names = [npc["name"] for npc in npc_details[:2]]
            return f"Around the flickering campfire, {' and '.join(names)} share stories of distant lands. The bonds between your group grow stronger through shared experiences."
    
    elif "action" in tags and npc_details:
        if len(npc_details) == 1:
            npc = npc_details[0]
            return f"{npc['name']} stands ready at your side, weapons gleaming in the sunlight. Together, you face the challenge ahead with determination and courage."
        else:
            names = [npc["name"] for npc in npc_details[:2]]
            return f"{' and '.join(names)} stand ready at your side, weapons gleaming in the sunlight. Together, you face the challenge ahead as a united force."
    
    elif "reveal" in tags and npc_details:
        npc = npc_details[0] if npc_details else None
        if npc:
            return f"{npc['name']} reveals ancient secrets hidden for generations. The knowledge shared changes your understanding of the world and your place within it."
        else:
            return f"Ancient secrets are revealed, changing your understanding of the world and your place within it."
    
    elif "conflict" in tags and any(npc["role"] == "Rival" for npc in npc_details):
        rival = next((npc for npc in npc_details if npc["role"] == "Rival"), npc_details[0] if npc_details else None)
        if rival:
            return f"{rival['name']} emerges from the shadows, challenge burning in their eyes. 'You think yourself worthy, {player_name}? Prove it.'"
    
    elif "recruit" in tags and npc_details:
        npc = npc_details[0]
        trust_level = npc["trust"]
        if trust_level >= 0.7:
            return f"{npc['name']} looks at you with deep respect and loyalty. 'I've seen your courage and wisdom, {player_name}. I would be honored to join your quest.'"
        else:
            return f"{npc['name']} considers your offer carefully. There's still uncertainty in their eyes, but they nod slowly. 'Perhaps our paths should align.'"
    
    # Generic fallback with NPC names if present
    if npc_details:
        if len(npc_details) == 1:
            npc = npc_details[0]
            return f"Your journey continues with {npc['name']} at your side. Each step forward brings new challenges and opportunities for growth."
        else:
            names = [npc["name"] for npc in npc_details[:2]]
            return f"Your journey continues with {' and '.join(names)} at your side. Each step forward brings new challenges and opportunities for growth."
    
    # Ultimate fallback - no NPCs present
    return f"Your solitary journey continues, {player_name}. Each step forward brings new challenges and opportunities for growth and self-discovery."


def substitute_npc_variables(template: str, npc_details: List[Dict], state: StoryState, player_name: str) -> str:
    """Substitute NPC variables in template strings (future enhancement)."""
    # This will be implemented when we add prose_templates to beat JSONs
    text = template.replace("{{player_name}}", player_name)
    
    if npc_details:
        primary_npc = npc_details[0]
        text = text.replace("{{npc_name}}", primary_npc["name"])
        text = text.replace("{{npc_role}}", primary_npc["role"].lower())
        
        if primary_npc["role"] == "Mentor":
            text = text.replace("{{mentor_name}}", primary_npc["name"])
    
    return text


async def generate_story_directed(
    player_id: str,
    player_name: str,
    theme: str,
    intent_vector: List[float],
) -> tuple[str, Dict[str, Any]]:
    # Load director config and beats
    config_path = pathlib.Path("config/story_director.yaml")
    with config_path.open("r", encoding="utf-8") as f:
        director_cfg = yaml.safe_load(f)

    beats_dir = pathlib.Path("assets/beats")
    beats: List[dict] = []
    for p in beats_dir.glob("*.json"):
        with p.open("r", encoding="utf-8") as bf:
            try:
                beats.append(json.load(bf))
            except Exception:
                continue

    # Deterministic RNG from STORY_SEED (or fallback to player-context)
    story_seed = os.getenv("STORY_SEED") or f"{player_id}:{player_name}:{theme}"
    rng = random.Random(story_seed)

    # Initialize state
    # Derive player archetype from saved profile if available
    player_profile_path = pathlib.Path("backend/player_profile.json")
    player_archetype = "Hero"
    if player_profile_path.exists():
        try:
            with player_profile_path.open("r", encoding="utf-8") as pf:
                profiles = json.load(pf)
                prof = profiles.get(player_id) or {}
                if isinstance(prof, dict):
                    player_archetype = str(prof.get("archetype") or player_archetype)
        except Exception:
            pass

    # Extract simple world hooks from the ritual text inputs where possible
    # Hooks are lowercased keywords from theme and obvious tokens
    def _extract_hooks(text: str) -> List[str]:
        if not text:
            return []
        tokens = re.findall(r"[A-Za-z]+", text.lower())
        # keep unique, short stoplist
        stop = {"and", "the", "of", "to", "a", "in", "on", "for", "with", "by", "at"}
        hooks = [t for t in tokens if t not in stop and len(t) >= 3]
        # limit size
        unique: List[str] = []
        for t in hooks:
            if t not in unique:
                unique.append(t)
            if len(unique) >= 12:
                break
        return unique

    # Start with theme-derived hooks
    world_hooks = set(_extract_hooks(theme))
    # Merge ritual cache hooks if available
    try:
        ritual_cache = pathlib.Path("backend") / "ritual_cache" / f"{player_id}.json"
        if ritual_cache.exists():
            with ritual_cache.open("r", encoding="utf-8") as rf:
                cached = json.load(rf)
                world_hooks.update(_extract_hooks(str(cached.get("askText", ""))))
                world_hooks.update(_extract_hooks(str(cached.get("seekText", ""))))
                world_hooks.update(_extract_hooks(str(cached.get("knockText", ""))))
                world_hooks.update(_extract_hooks(str(cached.get("theme", ""))))
    except Exception:
        pass
    world_hooks = list(world_hooks)
    tension_curve = director_cfg.get("tension_curve", [0.2] * 30)
    state = StoryState(
        scene_index=0,
        phase="early",
        tension=float(tension_curve[0]),
        target_curve=tension_curve,
        player={"name": player_name, "theme": theme, "archetype": player_archetype},
        npcs={},
        party=[],
        flags={"config": director_cfg, "world_hooks": world_hooks},
    )

    # Generate story NPCs and seed state
    npcs = await generate_story_npcs(player_id, player_name, player_archetype, theme, num_npcs=5)
    for npc in npcs:
        nid = str(npc.id)
        state.npcs[nid] = {
            "full_name": npc.full_name,
            "role": npc.role,
            "trust": float(getattr(npc, "trust", 0.3) or 0.3),
            "arc_state": "intro",
            "interactions": 0,
            "last_invite_scene": None,
            "narrative_hooks": list(getattr(npc, "narrative_hooks", []) or []),
        }

    # Build 30 scenes
    TOTAL_SCENES = 30
    story_dict: Dict[str, Any] = {}
    for si in range(TOTAL_SCENES):
        state.scene_index = si
        state.update_phase_from_curve()

        # Candidate beats by DSL
        viable = []
        for beat in beats:
            npcs_allowed = beat.get("npcs_allowed", "any")
            if npcs_allowed in ("one", "group"):
                if not any(evaluate_preconditions(beat, state, npc=nid) for nid in state.npcs.keys()):
                    continue
            else:
                if not evaluate_preconditions(beat, state, npc=None):
                    continue
            viable.append(beat)

        if not viable:
            viable = beats[:]

        picked = select_next_beat(state, viable, director_cfg.get("weights", {}), rng)
        npcs_present = schedule_npcs_for_beat(picked, state)

        tension_before = state.tension
        before_trust = {nid: state.npcs[nid]["trust"] for nid in npcs_present}
        apply_effects(picked, state, npcs_present)
        after_trust = {nid: state.npcs[nid]["trust"] for nid in npcs_present}
        trust_changes = {nid: round(after_trust[nid] - before_trust[nid], 3) for nid in npcs_present}

        for nid in npcs_present:
            state.bump_interactions(nid)

        if picked.get("id") == "recruitment_offer":
            for nid in npcs_present:
                state.set_last_invite_scene(nid, si)

        state.record_recent_tags(picked.get("tags", []))

        tag = f"tag_{si + 1:03d}"
        next_tag = f"tag_{si + 2:03d}" if si < TOTAL_SCENES - 1 else None
        choices = {}
        if next_tag:
            choices = {
                "1": {"text": "Continue", "next": next_tag, "next_scene_index": si + 1},
                "2": {"text": "Press on", "next": next_tag, "next_scene_index": si + 1},
            }

            # Ensure planned character encounters are present at anchor indices
            try:
                from .generate_story import _compute_anchor_indices, _pick_name_for_role, _mint_id_for_name, _inject_intro_sentence
                anchors = _compute_anchor_indices(TOTAL_SCENES)
                role_at_this_scene = None
                for role, idx in anchors.items():
                    if idx == si:
                        role_at_this_scene = role
                        break
                if role_at_this_scene:
                    seed = sum(ord(c) for c in player_name) + si
                    name = _pick_name_for_role(role_at_this_scene, seed)
                    npc_id = _mint_id_for_name(state.player_id if hasattr(state, 'player_id') else None, name)
                    # Ensure presence and prose mention
                    picked.setdefault('npcs_present', [])
                    if npc_id not in picked['npcs_present']:
                        picked['npcs_present'].append(npc_id)
                    picked['text'] = _inject_intro_sentence(picked.get('text', ''), role_at_this_scene.replace('_', ' '), name)
                    # Persist lightweight metadata
                    state.__dict__.setdefault('_npc_metadata', {})[npc_id] = {"full_name": name, "role": role_at_this_scene}
            except Exception:
                pass
            
            # Generate 3rd contextual choice
            try:
                from backend.story.choice_generator import make_contextual_choice, should_enable_free_text
                from backend.story.telemetry import log_choice_generated
                
                existing_choice_texts = [ch.get("text", "") for ch in choices.values()]
                contextual_choice = await make_contextual_choice(
                    state=state.__dict__,
                    beat=picked,
                    npcs_present=npcs_present,
                    existing_choices=existing_choice_texts
                )
                
                if contextual_choice:
                    choices["3"] = {
                        "text": contextual_choice.text,
                        "next": next_tag,
                        "next_scene_index": si + 1,
                        **contextual_choice.effects
                    }
                    
                    # Log the generated choice
                    log_choice_generated(
                        scene_index=si,
                        beat_id=picked.get("id", "unknown"),
                        text=contextual_choice.text,
                        source="auto3"
                    )
                    
                    # Add free-text flag if enabled
                    if should_enable_free_text(si):
                        choices["free_text_enabled"] = True
                        
            except Exception as e:
                print(f"⚠️ Choice generation failed for scene {si}: {e}")
                # Continue without 3rd choice

        # Build name map for present NPCs so the UI can render names immediately
        present_name_map = {nid: state.npcs.get(nid, {}).get("full_name", nid[:8]) for nid in npcs_present}

        # Generate NPC-aware story text; prefer LLM-constrained prose if available
        scene_text = None
        try:
            scene_text = await write_scene_prose(
                beat=picked,
                phase=state.phase,
                npcs_present=npcs_present,
                present_name_map=present_name_map,
                npc_meta_lookup=state.npcs,
                player_name=player_name,
            )
        except Exception:
            scene_text = None
        if not scene_text:
            scene_text = generate_scene_text(picked, npcs_present, state, player_name)
        # If the prose mentions an elder/mentor but none were scheduled, force a mentor presence
        try:
            if not npcs_present and re.search(r"\b(elder|mentor|sage)\b", scene_text.lower()):
                import uuid as _uuid
                fallback_mentor_id = str(_uuid.uuid5(_uuid.NAMESPACE_OID, "default:orin"))
                npcs_present = [fallback_mentor_id]
                present_name_map[fallback_mentor_id] = present_name_map.get(fallback_mentor_id, "Orin")
        except Exception:
            pass
        # Ultra-generic role binding in Director path as well
        try:
            if not npcs_present and scene_text:
                text_low = scene_text.lower()
                role_words = [
                    "hermit","magician","mage","wizard","soldier","warrior","singer","dancer",
                    "traveler","wanderer","leader","scout","healer","monk","sage","mentor","rival",
                ]
                for role in role_words:
                    if role in text_low:
                        import uuid as _uuid
                        stable_id = str(_uuid.uuid5(_uuid.NAMESPACE_OID, f"default:role:{role}"))
                        npcs_present = [stable_id]
                        present_name_map[stable_id] = present_name_map.get(stable_id, role.title())
                        break
        except Exception:
            pass
        if npcs_present:
            personalities = [build_personality(state.npcs[n]) for n in npcs_present]
            # Add one atmospheric line for flavor in early scenes
            if si <= 2:
                try:
                    line = personalities[0].get_description()
                    if line and line not in scene_text:
                        scene_text = scene_text + "\n\n" + line
                except Exception:
                    pass

        story_dict[tag] = {
            "text": scene_text,
            "choices": choices,
            "media": {"images": [], "audio": []},
            "npc_text": "",
            "scene_index": si,
            "phase": state.phase,
            "beat_id": picked.get("id"),
            "narrative_purpose": picked.get("tags", []),
            "npcs_present": npcs_present,
            "present_name_map": present_name_map,
        }

        log_scene_decision(
            scene_index=si,
            selected_beat_id=picked.get("id"),
            top_candidates=state.flags.get("last_top_candidates", []),
            npcs_present=npcs_present,
            trust_changes=trust_changes,
            tension_before_after=(tension_before, state.tension),
        )

    # Recruitment choices for recruitment_offer scenes
    try:
        from backend.story_recruitment import evaluator
        for scene_tag, scene in story_dict.items():
            if scene.get("beat_id") == "recruitment_offer" and scene.get("npcs_present"):
                recruitment_choices = evaluator.evaluate_scene_for_recruitment(
                    scene_tag=scene_tag,
                    npcs_present=scene["npcs_present"],
                    player_id=player_id,
                    player_name=player_name,
                    theme=theme,
                    intent_vector=intent_vector,
                )
                if recruitment_choices:
                    scene.setdefault("choices", {})
                    for key, data in recruitment_choices.items():
                        scene["choices"][key] = {**scene["choices"].get(key, {}), **data}
    except Exception:
        # Default invite/decline
        for scene_tag, scene in story_dict.items():
            if scene.get("beat_id") == "recruitment_offer" and scene.get("npcs_present"):
                idx = int(scene.get("scene_index", 0))
                next_tag = f"tag_{idx + 2:03d}" if idx < TOTAL_SCENES - 1 else None
                scene.setdefault("choices", {})
                scene["choices"]["invite"] = {
                    "text": "Invite them to join the party",
                    "next": next_tag,
                    "recruit_line": f"'{player_name}, I've seen your resolve. I will walk beside you.'",
                }
                scene["choices"]["decline"] = {
                    "text": "Let the moment pass",
                    "next": next_tag,
                }

    first_tag = "tag_001"
    return first_tag, story_dict

