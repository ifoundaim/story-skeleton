from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .state import StoryState

# Import WebSocket manager and telemetry
try:
    from ..websocket_manager import websocket_manager
    from .telemetry import log_toast_emitted
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    websocket_manager = None
    def log_toast_emitted(*args, **kwargs):
        pass


def _parse_range(value: str) -> Optional[List[float]]:
    # format: in[low,high]
    if not value.startswith("in[") or not value.endswith("]"):
        return None
    try:
        body = value[3:-1]
        low_str, high_str = [s.strip() for s in body.split(",", 1)]
        return [float(low_str), float(high_str)]
    except Exception:
        return None


def _parse_set(value: str) -> Optional[List[str]]:
    # format: in{a,b,c}
    if not value.startswith("in{") or not value.endswith("}"):
        return None
    body = value[3:-1]
    return [s.strip() for s in body.split(",") if s.strip()]


def _compare_numeric(lhs: float, op_value: str) -> bool:
    # op_value examples: "<=0.6", ">=0.5", "+0.05", "-0.10"
    try:
        op = op_value[:2] if op_value[:2] in {"<=", ">="} else op_value[0]
        num = float(op_value[len(op):])
        if op == "<=":
            return lhs <= num
        if op == ">=":
            return lhs >= num
        if op == "==":
            return abs(lhs - num) < 1e-9
        # not a comparison (could be "+0.1"); for preconditions, treat unknown as False
        return False
    except Exception:
        return False


def _check_world_flag_precondition(key: str, expected: Any, state: StoryState) -> bool:
    """Check if a world flag meets the precondition."""
    current_value = state.world_flags.get(key)
    
    if isinstance(expected, str):
        # String comparison
        if expected.startswith("in{"):
            options = _parse_set(expected)
            return options is not None and str(current_value) in options
        elif expected.startswith("in["):
            rng = _parse_range(expected)
            if rng is not None and isinstance(current_value, (int, float)):
                return rng[0] <= float(current_value) <= rng[1]
        else:
            # Check if it's a numeric comparison like ">=3"
            if isinstance(current_value, (int, float)):
                return _compare_numeric(float(current_value), expected)
            # Direct equality for strings
            return str(current_value) == expected
    elif isinstance(expected, bool):
        return current_value == expected
    elif isinstance(expected, (int, float)):
        return current_value == expected
    
    return False

# ─── Property DSL predicates ─────────────────────────────────────────────────
def _prop_ge(npc_props: dict, path: str, threshold: float) -> bool:
    cur = npc_props
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    try:
        return float(cur) >= float(threshold)
    except Exception:
        return False

def _prop_eq(npc_props: dict, path: str, value: str) -> bool:
    cur = npc_props
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return str(cur) == value

def _evaluate_property_predicate(predicate: str, npc_props: dict) -> bool:
    # Examples: "function.advisor >= 0.4", "capability.guidance >= 0.5",
    #           "stance.ally >= 0.5", "species == animal", "species != human"
    try:
        if '>=' in predicate:
            left, right = [s.strip() for s in predicate.split('>=', 1)]
            return _prop_ge(npc_props, left, float(right))
        if '==' in predicate:
            left, right = [s.strip() for s in predicate.split('==', 1)]
            return _prop_eq(npc_props, left, right.strip('"\''))
        if '!=' in predicate:
            left, right = [s.strip() for s in predicate.split('!=', 1)]
            return not _prop_eq(npc_props, left, right.strip('"\''))
    except Exception:
        return False
    return False



def _check_promise_precondition(promise_spec: str, expected: bool, state: StoryState) -> bool:
    """Check promise-related preconditions."""
    if promise_spec.startswith("contains(") and promise_spec.endswith(")"):
        # format: contains(promise_id) or contains(npc_id)
        target = promise_spec[9:-1]  # Remove "contains(" and ")"
        
        # Check if it's a promise ID or NPC ID
        for promise in state.promises:
            if promise.id == target or promise.npc_id == target:
                if not promise.fulfilled and not promise.breached:
                    return expected
        return not expected  # Promise not found or already resolved
    
    return False


def _check_reputation_precondition(trait: str, threshold: str, state: StoryState) -> bool:
    """Check reputation trait against threshold."""
    if not hasattr(state.reputation, trait):
        return False
    
    current_value = getattr(state.reputation, trait)
    return _compare_numeric(current_value, threshold)


def _check_resource_precondition(resource: str, threshold: str, state: StoryState) -> bool:
    """Check resource value against threshold."""
    if not hasattr(state.resources, resource):
        return False
    
    current_value = getattr(state.resources, resource)
    return _compare_numeric(float(current_value), threshold)


def evaluate_preconditions(beat: Dict[str, Any], state: StoryState, npc: Optional[str] = None) -> bool:
    conds: Dict[str, Any] = beat.get("preconditions", {}) or {}

    for key, expected in conds.items():
        # special keys which may depend on npc
        if key == "tension":
            if isinstance(expected, str):
                if expected.startswith("in["):
                    rng = _parse_range(expected)
                    if rng is None or not (rng[0] <= state.tension <= rng[1]):
                        return False
                else:
                    if not _compare_numeric(state.tension, expected):
                        return False
            else:
                return False
        elif key == "phase":
            options = _parse_set(expected) if isinstance(expected, str) else None
            if not options or state.phase not in options:
                return False
        elif key == "scene_mood":
            options = _parse_set(expected) if isinstance(expected, str) else None
            mood = str(state.flags.get("scene_mood", "")).strip() or ""
            if not options or mood not in options:
                return False
        elif key == "party_not_full":
            # Use capacity from config if present
            recruitment_cfg = (state.flags.get("config") or {}).get("recruitment") or {}
            capacity = int(recruitment_cfg.get("party_capacity", 3))
            if len(state.party) >= capacity:
                return False
        elif key.startswith("interactions[") and key.endswith("]"):
            if npc is None:
                return False
            interactions = int(state.npcs.get(npc, {}).get("interactions", 0))
            if not _compare_numeric(float(interactions), str(expected)):
                return False
        elif key.startswith("trust[") and key.endswith("]"):
            if npc is None:
                return False
            trust = float(state.npcs.get(npc, {}).get("trust", 0.0))
            if not _compare_numeric(trust, str(expected)):
                return False
        elif key.startswith("arc_state[") and key.endswith("]"):
            if npc is None:
                return False
            options = _parse_set(str(expected))
            arc_state = str(state.npcs.get(npc, {}).get("arc_state", ""))
            if not options or arc_state not in options:
                return False
        elif key.startswith("cooldown_ok[") and key.endswith("]"):
            # expected is True/False
            if npc is None:
                return False
            last_invite = state.npcs.get(npc, {}).get("last_invite_scene")
            if last_invite is None:
                continue  # never invited, okay
            cooldown_cfg = (state.flags.get("config") or {}).get("recruitment") or {}
            cooldown = int(cooldown_cfg.get("cooldown_scenes", 2))
            if (state.scene_index - int(last_invite)) < cooldown:
                return False
        # Consequence Fabric preconditions
        elif key.startswith("world_flags["):
            # format: world_flags[flag_key]
            flag_key = key[12:-1]  # Remove "world_flags[" and "]"
            if not _check_world_flag_precondition(flag_key, expected, state):
                return False
        elif key.startswith("promises."):
            # format: promises.contains(promise_id) or promises.contains(npc_id)
            if not _check_promise_precondition(key[9:], expected, state):
                return False
        elif key.startswith("reputation."):
            # format: reputation.trait_name
            trait = key[11:]  # Remove "reputation."
            if not _check_reputation_precondition(trait, str(expected), state):
                return False
        elif key.startswith("resources."):
            # format: resources.resource_name
            resource = key[10:]  # Remove "resources."
            if not _check_resource_precondition(resource, str(expected), state):
                return False
        else:
            # Unknown key, ignore for now (treat as pass)
            continue

    return True


def _apply_numeric_change(current: float, delta_expr: str) -> float:
    # delta_expr like "+0.05" or "-0.10"
    try:
        if delta_expr.startswith("+") or delta_expr.startswith("-"):
            new_val = current + float(delta_expr)
            return max(0.0, min(1.0, new_val))
        return current
    except Exception:
        return current


def apply_effects(beat: Dict[str, Any], state: StoryState, npc_list: List[str], player_id: Optional[str] = None) -> None:
    effects: Dict[str, Any] = beat.get("effects", {}) or {}

    # Tension adjustments
    if "tension" in effects and isinstance(effects["tension"], str):
        state.tension = max(0.0, min(1.0, _apply_numeric_change(state.tension, effects["tension"])))

    # Set flags (one-off)
    set_flag = effects.get("set_flag")
    if isinstance(set_flag, dict):
        state.flags.update(set_flag)
        # Emit flag_set toast for each flag
        for key, value in set_flag.items():
            if WEBSOCKET_AVAILABLE:
                asyncio.create_task(websocket_manager.emit_consequence_toast(
                    kind="flag_set",
                    label=f"Flag set: {key}",
                    player_id=player_id
                ))
                log_toast_emitted(state.scene_index, "flag_set", f"Flag set: {key}")

    # Per-NPC adjustments
    for npc_id in npc_list:
        if "trust[npc]" in effects and isinstance(effects["trust[npc]"], str):
            delta = float(effects["trust[npc]"])
            state.apply_trust_delta(npc_id, delta)
            # Emit reputation_shift toast
            if WEBSOCKET_AVAILABLE:
                npc_name = state.npcs.get(npc_id, {}).get("full_name", "Unknown")
                direction = "↑" if delta > 0 else "↓"
                asyncio.create_task(websocket_manager.emit_consequence_toast(
                    kind="reputation_shift",
                    label=f"{npc_name} trust {direction}",
                    player_id=player_id,
                    delta=delta,
                    npc_id=npc_id
                ))
                log_toast_emitted(state.scene_index, "reputation_shift", f"{npc_name} trust {direction}", npc_id, delta)

        if "arc_transition[npc]" in effects:
            new_arc = str(effects["arc_transition[npc]"])
            state.set_arc(npc_id, new_arc)

    # Consequence Fabric effects
    # World flags
    set_world_flag = effects.get("set_world_flag")
    if isinstance(set_world_flag, dict):
        for key, value in set_world_flag.items():
            state.set_world_flag(key, value)
            # Emit flag_set toast
            if WEBSOCKET_AVAILABLE:
                asyncio.create_task(websocket_manager.emit_consequence_toast(
                    kind="flag_set",
                    label=f"World flag set: {key}",
                    player_id=player_id
                ))
                log_toast_emitted(state.scene_index, "flag_set", f"World flag set: {key}")
    
    clear_world_flag = effects.get("clear_world_flag")
    if isinstance(clear_world_flag, list):
        for key in clear_world_flag:
            state.clear_world_flag(key)
            # Emit flag_cleared toast
            if WEBSOCKET_AVAILABLE:
                asyncio.create_task(websocket_manager.emit_consequence_toast(
                    kind="flag_cleared",
                    label=f"World flag cleared: {key}",
                    player_id=player_id
                ))
                log_toast_emitted(state.scene_index, "flag_cleared", f"World flag cleared: {key}")
    
    # Promises
    add_promise = effects.get("add_promise")
    if isinstance(add_promise, dict):
        state.add_promise(
            promise_id=add_promise["id"],
            description=add_promise["description"],
            npc_id=add_promise.get("npc_id"),
            due_by_scene=add_promise.get("due_by_scene")
        )
        # Emit promise_set toast
        if WEBSOCKET_AVAILABLE:
            npc_id = add_promise.get("npc_id")
            npc_name = state.npcs.get(npc_id, {}).get("full_name", "Unknown") if npc_id else "Unknown"
            asyncio.create_task(websocket_manager.emit_consequence_toast(
                kind="promise_set",
                label=f"Promise made to {npc_name}",
                player_id=player_id,
                npc_id=npc_id
            ))
            log_toast_emitted(state.scene_index, "promise_set", f"Promise made to {npc_name}", npc_id)
    
    fulfill_promise = effects.get("fulfill_promise")
    if isinstance(fulfill_promise, str):
        state.fulfill_promise(fulfill_promise)
        # Emit promise_fulfilled toast
        if WEBSOCKET_AVAILABLE:
            asyncio.create_task(websocket_manager.emit_consequence_toast(
                kind="promise_fulfilled",
                label="Promise fulfilled",
                player_id=player_id
            ))
            log_toast_emitted(state.scene_index, "promise_fulfilled", "Promise fulfilled")
    
    breach_promise = effects.get("breach_promise")
    if isinstance(breach_promise, str):
        state.breach_promise(breach_promise)
        # Emit promise_breached toast
        if WEBSOCKET_AVAILABLE:
            asyncio.create_task(websocket_manager.emit_consequence_toast(
                kind="promise_breached",
                label="Promise breached",
                player_id=player_id
            ))
            log_toast_emitted(state.scene_index, "promise_breached", "Promise breached")
    
    # Reputation
    reputation_delta = effects.get("reputation_delta")
    if isinstance(reputation_delta, dict):
        state.apply_reputation_delta(reputation_delta)
        # Emit reputation_shift toast for each trait
        for trait, delta in reputation_delta.items():
            if WEBSOCKET_AVAILABLE:
                direction = "↑" if delta > 0 else "↓"
                asyncio.create_task(websocket_manager.emit_consequence_toast(
                    kind="reputation_shift",
                    label=f"{trait} reputation {direction}",
                    player_id=player_id,
                    delta=delta
                ))
                log_toast_emitted(state.scene_index, "reputation_shift", f"{trait} reputation {direction}", delta=delta)
    
    # Resources
    resource_delta = effects.get("resource_delta")
    if isinstance(resource_delta, dict):
        state.apply_resource_delta(resource_delta)
        # Emit resource_change toast for each resource
        for resource, delta in resource_delta.items():
            if WEBSOCKET_AVAILABLE:
                direction = "↑" if delta > 0 else "↓"
                asyncio.create_task(websocket_manager.emit_consequence_toast(
                    kind="resource_change",
                    label=f"{resource} {direction}",
                    player_id=player_id,
                    delta=delta
                ))
                log_toast_emitted(state.scene_index, "resource_change", f"{resource} {direction}", delta=delta)


def promise_window(scene: int, due_by: Optional[int]) -> bool:
    """Helper function to check if a promise is within its window."""
    if due_by is None:
        return True  # No deadline, always in window
    return scene <= due_by

