from __future__ import annotations

"""
Open-World Role Induction

induce_role(npc, scene_text, dialogue_snippets, world_hooks, player_archetype, seed) -> dict

LLM path (if OPENAI_API_KEY configured) else deterministic heuristic fallback.
The output schema provides soft functions, stance and capability vectors used by
the property-based beat DSL and scheduler.
"""

import os
import re
import json
import math
import hashlib
from typing import Any, Dict, List, Optional


def _stable_rand(seed: int, key: str) -> float:
    h = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()
    # map to [0,1)
    return int.from_bytes(h[:8], "big") / 2**64


def _norm(v: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, x) for x in v.values()) or 1.0
    return {k: max(0.0, x) / total for k, x in v.items()}


def _heuristics(scene_text: str, dialogue: str, hooks: List[str], seed: int) -> Dict[str, Any]:
    text = (scene_text or "") + "\n" + (dialogue or "")
    tl = text.lower()
    role_label = None
    species = None
    social_position = None
    faction = None
    role_aliases_add: List[str] = []

    # simple species detector
    for sp, keys in {
        "animal": ["wolf", "owl", "bear", "fox", "raven", "eagle", "cat", "dog"],
        "human": ["hermit", "dockmaster", "queen", "merchant", "healer", "hunter"],
        "spirit": ["spirit", "phantom", "ghost"],
    }.items():
        if any(k in tl for k in keys):
            species = sp
            break

    # role induction by keywords (open world-ish but extensible)
    role_candidates = {
        "hermit": ["hermit", "recluse", "sage in the wild"],
        "dockmaster": ["dockmaster", "harbor", "port authority"],
        "queen": ["queen", "monarch", "throne"],
        "guide": ["guide", "lead you", "shows the way"],
        "protector": ["guards", "protect", "ward"],
        "informant": ["tells", "reveals", "rumor", "whispers"],
        "healer": ["healer", "salve", "wound", "herb"],
        "trickster": ["trick", "riddle", "mischief"],
        "gatekeeper": ["gate", "passage", "checkpoint"],
        "hunter": ["track", "hunt", "prey"],
    }
    scores: Dict[str, int] = {}
    for label, keys in role_candidates.items():
        scores[label] = sum(1 for k in keys if k in tl)
    role_label = max(scores, key=scores.get) if scores and max(scores.values()) > 0 else None

    # function probabilities
    base_func = {
        "advisor": 0.1,
        "opponent": 0.1,
        "guide": 0.1,
        "healer": 0.1,
        "trickster": 0.1,
        "protector": 0.1,
        "informant": 0.1,
        "gatekeeper": 0.1,
    }
    # boost by evidence
    evidence_map = {
        "advisor": ["advice", "counsel", "suggest"],
        "guide": ["guide", "leads", "path"],
        "healer": ["heal", "salve", "herb"],
        "trickster": ["trick", "riddle", "jest"],
        "protector": ["guard", "shield", "protect"],
        "informant": ["tell", "reveal", "rumor", "whisper"],
        "gatekeeper": ["gate", "checkpoint", "passage"],
        "opponent": ["threat", "attack", "block"],
    }
    for f, keys in evidence_map.items():
        base_func[f] += 0.2 * sum(1 for k in keys if k in tl)

    # stance probabilities
    stance_probs = {
        "ally": 0.33,
        "neutral": 0.34,
        "rival": 0.33,
    }
    if any(k in tl for k in ["helps", "rescues", "supports", "smiles"]):
        stance_probs["ally"] += 0.3
    if any(k in tl for k in ["blocks", "threat", "taunts", "refuses"]):
        stance_probs["rival"] += 0.3

    # capabilities
    capabilities = {
        "guidance": 0.2,
        "combat": 0.2,
        "stealth": 0.2,
        "social": 0.2,
        "mystical": 0.2,
        "survival": 0.2,
    }
    if any(k in tl for k in ["path", "direction", "map", "route"]):
        capabilities["guidance"] += 0.3
    if any(k in tl for k in ["fight", "blade", "claw", "battle"]):
        capabilities["combat"] += 0.3
    if any(k in tl for k in ["whisper", "barter", "persuade", "charm"]):
        capabilities["social"] += 0.3
    if any(k in tl for k in ["ritual", "spirit", "mystic", "arcane"]):
        capabilities["mystical"] += 0.3
    if any(k in tl for k in ["track", "hunt", "forage", "wilds"]):
        capabilities["survival"] += 0.3

    # add small deterministic noise for variety
    for k in list(base_func.keys()):
        base_func[k] += 0.05 * _stable_rand(seed, f"func:{k}")
    for k in list(stance_probs.keys()):
        stance_probs[k] += 0.05 * _stable_rand(seed, f"stance:{k}")
    for k in list(capabilities.keys()):
        capabilities[k] += 0.05 * _stable_rand(seed, f"cap:{k}")

    function_probs = _norm(base_func)
    stance_probs = _norm(stance_probs)
    capabilities = _norm(capabilities)

    hooks = list({*(hooks or []), *(re.findall(r"[A-Za-z]{4,}", scene_text or "")[:8])})[:10]
    confidence = 0.5 + 0.4 * max(function_probs.values())

    return {
        "role_label": role_label or "emergent",
        "role_aliases_add": role_aliases_add,
        "function_probs": function_probs,
        "stance_probs": stance_probs,
        "capabilities": capabilities,
        "species": species,
        "social_position": social_position,
        "faction": faction,
        "hooks": hooks,
        "confidence": min(0.99, max(0.0, confidence)),
    }


def induce_role(npc: Dict[str, Any] | None,
                scene_text: str,
                dialogue_snippets: List[str] | None,
                world_hooks: List[str] | None,
                player_archetype: str | None,
                seed: int) -> Dict[str, Any]:
    """Public API. Uses LLM when available; otherwise heuristics.
    Deterministic via seed.
    """
    # LLM optional path: off by default if no key; keep deterministic prompt seed in future
    use_llm = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("LLM_ROLE_INDUCTION", "false").lower() in {"true","1","yes"}
    dialogue = "\n".join(dialogue_snippets or [])

    if not use_llm:
        return _heuristics(scene_text, dialogue, world_hooks or [], seed)

    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = {
            "scene": scene_text,
            "dialogue": dialogue,
            "hooks": world_hooks or [],
            "player_archetype": player_archetype or "Hero",
        }
        resp = client.chat.completions.create(
            model=os.getenv("LLM_ROLE_MODEL", "gpt-4o-mini"),
            messages=[
                {"role":"system","content":"Extract an open-world NPC role and soft property vectors. Respond only JSON."},
                {"role":"user","content":json.dumps(prompt)}
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        # sanity: normalize vectors
        for key in ("function_probs","stance_probs","capabilities"):
            if isinstance(data.get(key), dict):
                data[key] = _norm({k: float(v) for k,v in data[key].items()})
        data.setdefault("role_label", "emergent")
        data.setdefault("confidence", 0.7)
        return data
    except Exception:
        return _heuristics(scene_text, dialogue, world_hooks or [], seed)


