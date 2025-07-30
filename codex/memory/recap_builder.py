import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "memory_state.json")


def _load_memory() -> dict:
    """Load memory state from JSON file."""
    if not os.path.exists(MEMORY_PATH):
        return {}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_memory(memory: dict) -> None:
    """Save memory state to JSON file."""
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


def _extract_emotion_trends(scenes: List[Dict[str, Any]]) -> str:
    """Extract emotion trends from scene history."""
    emotions = []
    for scene in scenes:
        if "emotion_delta" in scene:
            # Simple emotion trend detection
            delta = scene["emotion_delta"]
            if isinstance(delta, list) and len(delta) > 0:
                # Check for significant emotion changes
                if any(abs(val) > 0.3 for val in delta):
                    emotions.append("experienced strong emotions")
                elif any(abs(val) > 0.1 for val in delta):
                    emotions.append("felt subtle shifts in mood")
    
    if emotions:
        return f" Throughout their journey, they {', '.join(set(emotions))}."
    return ""


def _extract_npc_interactions(scenes: List[Dict[str, Any]]) -> str:
    """Extract NPC names and interactions from scenes."""
    npcs = set()
    for scene in scenes:
        npc_text = scene.get("npc_text", "")
        if npc_text:
            # Simple NPC name extraction (look for capitalized words that might be names)
            words = npc_text.split()
            for word in words:
                if word[0].isupper() and len(word) > 2 and word not in ["The", "This", "That", "They", "Their"]:
                    npcs.add(word)
    
    if npcs:
        npc_list = list(npcs)[:3]  # Limit to 3 NPCs
        if len(npc_list) == 1:
            return f" They encountered {npc_list[0]}."
        elif len(npc_list) == 2:
            return f" They met {npc_list[0]} and {npc_list[1]}."
        else:
            return f" They encountered {', '.join(npc_list[:-1])}, and {npc_list[-1]}."
    return ""


def _extract_choices(scenes: List[Dict[str, Any]]) -> str:
    """Extract key choices made by the player."""
    choices = []
    for scene in scenes:
        if "choices" in scene and isinstance(scene["choices"], list):
            # Look for choices that were made (assuming first choice is default)
            for choice in scene["choices"][:1]:  # Take first choice as example
                if isinstance(choice, dict) and "text" in choice:
                    choice_text = choice["text"]
                    # Extract key action words
                    if any(word in choice_text.lower() for word in ["help", "save", "attack", "run", "hide", "explore"]):
                        choices.append(choice_text.lower())
    
    if choices:
        return f" Their choices reflected a {choices[0]} approach."
    return ""


def build_memory(player_id: str, story: Dict[str, Any], history: List[str]) -> str:
    """
    Build a 3rd-person narrative recap of the player's journey.
    
    Args:
        player_id: The player's unique identifier
        story: The complete story tree with all scenes
        history: List of scene tags in chronological order
    
    Returns:
        A ~300-word narrative recap string
    """
    if not history:
        return f"{player_id} has not yet begun their journey."
    
    # Extract player name from player_id (remove numbers/special chars)
    player_name = ''.join(c for c in player_id if c.isalpha()).capitalize()
    if not player_name or len(player_name) < 2:
        player_name = "The adventurer"
    
    # Gather scene data
    scenes = []
    narrative_parts = []
    
    for tag in history:
        scene = story.get(tag, {})
        if scene:
            scenes.append(scene)
            text = scene.get("text", "")
            npc_text = scene.get("npc_text", "")
            
            if text:
                narrative_parts.append(text)
            if npc_text:
                narrative_parts.append(npc_text)
    
    # Build the narrative
    if not narrative_parts:
        return f"{player_name} began their journey but the path ahead remains unclear."
    
    # Combine narrative parts
    base_narrative = " ".join(narrative_parts)
    
    # Extract additional context
    emotion_trends = _extract_emotion_trends(scenes)
    npc_interactions = _extract_npc_interactions(scenes)
    choice_patterns = _extract_choices(scenes)
    
    # Compose the full recap - avoid duplicate names
    if base_narrative.lower().startswith(player_name.lower()):
        recap = base_narrative
    else:
        recap = f"{player_name} {base_narrative}"
    
    # Add context if we have it
    context_parts = [emotion_trends, npc_interactions, choice_patterns]
    context_parts = [part for part in context_parts if part]
    
    if context_parts:
        recap += "".join(context_parts)
    
    # Ensure proper sentence structure
    if not recap.endswith(('.', '!', '?')):
        recap += "."
    
    # Truncate to ~300 words
    words = recap.split()
    if len(words) > 300:
        # Try to cut at a sentence boundary
        sentences = recap.split('. ')
        truncated = ""
        for sentence in sentences:
            if len((truncated + sentence).split()) <= 300:
                truncated += sentence + ". "
            else:
                break
        recap = truncated.strip()
        if not recap.endswith('.'):
            recap += "..."
    
    return recap


def update_memory(player_id: str, story: Dict[str, Any], history: List[str]) -> str:
    """
    Update memory state with new recap and return the recap string.
    
    Args:
        player_id: The player's unique identifier
        story: The complete story tree with all scenes
        history: List of scene tags in chronological order
    
    Returns:
        The generated recap string
    """
    memory = _load_memory()
    recap = build_memory(player_id, story, history)
    
    memory[player_id] = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "recap": recap
    }
    
    _save_memory(memory)
    return recap


def get_memory(player_id: str) -> Optional[str]:
    """
    Retrieve the memory recap for a player.
    
    Args:
        player_id: The player's unique identifier
    
    Returns:
        The memory recap string or None if not found
    """
    memory = _load_memory()
    player_memory = memory.get(player_id, {})
    return player_memory.get("recap") 