# purpose_agents/generate_story.py

import openai
import os
import random
import json
import re
import logging
try:
    from .codex_router import TASK_QUEUE, Task
except ImportError:
    # Fallback for when codex module is not available
    TASK_QUEUE = None
    Task = None

# Import story validator
try:
    from codex.validate import validate, auto_heal
except ImportError:
    # Fallback for when validation module is not available
    def validate(tree):
        return []
    def auto_heal(tree, aggressive=False):
        return tree

# Import new constants for 30-scene framework
try:
    from .constants import (
        TOTAL_SCENES, ACT_SCENES, ACT_PURPOSES, 
        get_scene_tag, get_linear_choice_structure,
        LLM_STORY_DISABLED
    )
except ImportError:
    # Fallback constants if import fails
    TOTAL_SCENES = 30
    ACT_SCENES = {
        "ACT_I": (0, 6),
        "ACT_II": (7, 15),
        "ACT_III": (16, 23),
        "ACT_IV": (24, 29)
    }
    ACT_PURPOSES = {
        "ACT_I": {"name": "Setup and Introduction"},
        "ACT_II": {"name": "Rising Action and Development"},
        "ACT_III": {"name": "Climax and Crisis"},
        "ACT_IV": {"name": "Resolution and Conclusion"}
    }
    
    def get_scene_tag(scene_index: int) -> str:
        return f"tag_{scene_index + 1:03d}"
    
    def get_linear_choice_structure(scene_index: int) -> dict:
        if scene_index >= TOTAL_SCENES - 1:
            return {}
        next_scene = scene_index + 1
        return {
            "1": {
                "text": "Continue your journey",
                "next": get_scene_tag(next_scene)
            }
        }
    
    LLM_STORY_DISABLED = "LLM_STORY_DISABLED"

# Import recruitment evaluator
try:
    from backend.story_recruitment import evaluator
    RECRUITMENT_AVAILABLE = True
except ImportError:
    # Fallback for when recruitment module is not available
    RECRUITMENT_AVAILABLE = False
    evaluator = None

logger = logging.getLogger(__name__)

try:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    # Fallback for when OpenAI is not configured
    client = None

def strip_code_fences(text):
    # Remove leading ``` or ```json (with optional whitespace/newline)
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text.strip())
    # Remove trailing ``` (with optional whitespace/newline)
    text = re.sub(r"```\s*$", "", text.strip())
    return text

def create_fallback_30_scene_story(theme: str, intent_vector: list[float], player_name: str = "Adventurer") -> dict:
    """Create a guaranteed 30-scene linear story structure as fallback for offline testing."""
    
    story_dict = {}
    
    for scene_index in range(TOTAL_SCENES):
        scene_tag = get_scene_tag(scene_index)
        
        # Determine which act this scene belongs to
        act_name = None
        for act, (start, end) in ACT_SCENES.items():
            if start <= scene_index <= end:
                act_name = act
                break
        
        act_info = ACT_PURPOSES.get(act_name, {})
        act_description = act_info.get("name", "Story progression")
        
        # Generate scene text based on act and position
        if scene_index == 0:
            # Opening scene
            scene_text = f"Welcome, {player_name}. Your epic journey through the realm of {theme} begins here. The world around you pulses with ancient magic and untold possibilities. Your destiny awaits, and every choice you make will shape the legend you become."
        elif scene_index == ACT_SCENES["ACT_I"][1]:  # End of Act I
            scene_text = f"{player_name}, you've taken your first steps into this world of {theme}. The initial challenges have revealed your strengths and introduced you to allies who will walk beside you. The true adventure is about to begin."
        elif scene_index == ACT_SCENES["ACT_II"][1]:  # End of Act II
            scene_text = f"{player_name}, your journey has deepened. Relationships have formed, challenges have tested you, and the stakes have grown higher. The path ahead leads to even greater trials and revelations."
        elif scene_index == ACT_SCENES["ACT_III"][1]:  # End of Act III
            scene_text = f"{player_name}, you've faced the darkest moments of your quest. The ultimate challenge lies before you, and the choices you make now will determine the fate of all you hold dear."
        elif scene_index == TOTAL_SCENES - 1:
            # Final scene
            scene_text = f"{player_name}, your epic journey reaches its triumphant conclusion. Through courage, wisdom, and the bonds you've forged, you have not only achieved your goal but also discovered the true hero within yourself. Your legend in the realm of {theme} will inspire generations to come. The End."
        else:
            # Intermediate scenes
            progress = (scene_index + 1) / TOTAL_SCENES
            if progress < 0.25:
                scene_text = f"{player_name}, you continue your journey through the {theme} realm. Each step brings new discoveries and challenges that test your resolve and shape your character."
            elif progress < 0.5:
                scene_text = f"{player_name}, the adventure deepens as you encounter new allies and face escalating challenges. Your understanding of this world and your place within it grows stronger."
            elif progress < 0.75:
                scene_text = f"{player_name}, the stakes have never been higher. Every decision carries weight, and the consequences of your choices ripple through the fabric of this {theme} world."
            else:
                scene_text = f"{player_name}, you approach the final chapters of your quest. The culmination of all your experiences, relationships, and choices draws near."
        
        # Generate choices (linear progression)
        choices = get_linear_choice_structure(scene_index)
        
        # Create scene structure
        # Include minimal beat fields so the debug panel can render in fallback mode
        phase = (
            "early" if scene_index <= 6 else ("mid" if scene_index <= 21 else "late")
        )
        story_dict[scene_tag] = {
            "text": scene_text,
            "choices": choices,
            "media": {"images": [], "audio": []},
            "npc_text": "",
            "act": act_name,
            "act_purpose": act_description,
            "scene_index": scene_index,
            "npcs_present": [],  # Will be populated by NPC integration
            "beat_id": "fallback_path",
            "narrative_purpose": ["fallback", "linear"],
            "phase": phase,
        }
    
    # Add NPC assignment logic to fallback story
    import uuid
    
    # Generate consistent UUIDs for default NPCs
    lyra_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:lyra"))
    orin_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:orin"))
    companion_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:companion"))
    sage_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:sage"))
    warrior_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "default:warrior"))
    
    for scene_index, scene in enumerate(story_dict.values()):
        # Determine act for NPC placement based on scene index
        if scene_index <= 6:
            act_name = "ACT_I"
        elif scene_index <= 15:
            act_name = "ACT_II"
        elif scene_index <= 23:
            act_name = "ACT_III"
        else:
            act_name = "ACT_IV"
        
        # Set the act field on the scene for consistency
        scene["act"] = act_name
        
        # Add NPC presence based on act and scene position
        if act_name == "ACT_I":
            if scene_index in [0, 1]:
                scene["npcs_present"] = [lyra_uuid, orin_uuid]
            elif scene_index in [2, 3]:
                scene["npcs_present"] = [lyra_uuid]
            elif scene_index in [4, 5]:
                scene["npcs_present"] = [orin_uuid]
            else:  # scene_index == 6 (end of Act I)
                scene["npcs_present"] = [lyra_uuid, orin_uuid]
            # Ensure a generic 'creature' appears during early mysterious scenes
            # Add a stable UUID for the creature so UI can show it
            import uuid as _uuid
            creature_uuid = str(_uuid.uuid5(_uuid.NAMESPACE_OID, "default:creature"))
            if creature_uuid not in scene["npcs_present"]:
                scene["npcs_present"].append(creature_uuid)
        elif act_name == "ACT_II":
            if scene_index in [7, 8, 9]:
                scene["npcs_present"] = [lyra_uuid, orin_uuid, companion_uuid]
            elif scene_index in [10, 11, 12]:
                scene["npcs_present"] = [companion_uuid, sage_uuid]
            else:  # scene_index in [13, 14, 15]
                scene["npcs_present"] = [lyra_uuid, orin_uuid, sage_uuid]
        elif act_name == "ACT_III":
            if scene_index in [16, 17, 18]:
                scene["npcs_present"] = [warrior_uuid, sage_uuid]
            elif scene_index in [19, 20, 21]:
                scene["npcs_present"] = [lyra_uuid, orin_uuid, warrior_uuid]
            else:  # scene_index in [22, 23]
                scene["npcs_present"] = [warrior_uuid, companion_uuid]
        else:  # ACT_IV
            if scene_index in [24, 25]:
                scene["npcs_present"] = [companion_uuid, lyra_uuid]
            elif scene_index in [26, 27]:
                scene["npcs_present"] = [orin_uuid, sage_uuid]
            else:  # scene_index == 28 (final scene)
                scene["npcs_present"] = [lyra_uuid, orin_uuid, companion_uuid]
        
        # Add basic trust deltas and emotion deltas for NPCs
        choices = scene.get("choices", {})
        for ch in choices.values():
            if isinstance(ch, dict):
                ch.setdefault("trust_delta", 0.0)
                ch.setdefault("emotion_delta", [0.1, 0, 0, 0, 0.1, 0, 0, 0])
                
                # Add NPC-specific trust deltas if NPCs are present
                npc_ids = scene.get("npcs_present", [])
                if npc_ids:
                    ch["npc_trust_deltas"] = {}
                    for npc_id in npc_ids:
                        ch["npc_trust_deltas"][npc_id] = 0.1
    
    return story_dict

async def generate_story(player_id: str, player_name: str, theme: str, intent_vector: list[float]) -> tuple[str, dict]:
    # Check for feature flag to disable LLM story generation
    story_dict = None
    if os.getenv(LLM_STORY_DISABLED, "").lower() in ["true", "1", "yes"]:
        print(f"⚠️ LLM story generation disabled via {LLM_STORY_DISABLED}, using linear fallback for {player_name}")
        story_dict = create_fallback_30_scene_story(theme, intent_vector, player_name)
    
    # Director path if client is None and flag not set
    if story_dict is None and client is None:
        print(f"⚠️ OpenAI client not available, using Director beat planner for {player_name}")
        try:
            from .beat_generator import generate_story_directed
            first_tag, story_dict = await generate_story_directed(player_id, player_name, theme, intent_vector)
            return first_tag, story_dict
        except Exception as e:
            print(f"⚠️ Director path failed: {e}. Falling back to linear path.")
            story_dict = create_fallback_30_scene_story(theme, intent_vector, player_name)
    
    if story_dict is None:
        # Prefer Director-driven beat planner (default path)
        try:
            from .beat_generator import generate_story_directed
            first_tag, story_dict = await generate_story_directed(player_id, player_name, theme, intent_vector)
            return first_tag, story_dict
        except Exception as e:
            print(f"⚠️ Director path failed: {e}. Falling back to legacy LLM path.")
        # Legacy LLM path
        prompt = f"""
You are a mythic storyteller AI.
Generate a complete 30-scene branching story based on:

- Player Name: {player_name}
- Theme: {theme}
- Intent: {intent_vector[:10]}... (truncated)
- Audience: {player_name} on a hero's journey

CRITICAL: You must create exactly 30 complete story scenes following a four-act structure:

**ACT I (Scenes 0-6): Setup and Introduction**
- tag_001: Opening scene with 2 choices leading to tag_002 and tag_003
- tag_002-tag_006: Early development scenes with 2 choices each
- tag_007: End of Act I with 2 choices leading to Act II

**ACT II (Scenes 7-15): Rising Action and Development**
- tag_008-tag_015: Mid-story scenes with 2 choices each
- tag_016: End of Act II with 2 choices leading to Act III

**ACT III (Scenes 16-23): Climax and Crisis**
- tag_017-tag_023: Climax scenes with 2 choices each
- tag_024: End of Act III with 2 choices leading to Act IV

**ACT IV (Scenes 24-29): Resolution and Conclusion**
- tag_025-tag_028: Resolution scenes with 2 choices each
- tag_029: Final scene - no choices (story ending)

REQUIREMENTS:
- Generate ALL 30 scenes with complete text and proper structure
- Scenes tag_001 through tag_028 MUST have 2 choices each
- Only tag_029 should be an ending scene without choices
- Each scene must advance the story meaningfully within its act
- Make the story engaging with meaningful choices that impact the narrative
- IMPORTANT: Use {player_name}'s actual name in the story text where appropriate
- Include act information in each scene: "act": "ACT_I", "act_purpose": "Setup and Introduction"
- Include scene_index: 0-29 for each scene

Example structure:
{{
  "tag_001": {{
    "text": "[Opening scene description mentioning {player_name}]",
    "choices": {{
      "1": {{"text": "[Choice 1 description]", "next": "tag_002"}},
      "2": {{"text": "[Choice 2 description]", "next": "tag_003"}}
    }},
    "media": {{"images": [], "audio": []}},
    "act": "ACT_I",
    "act_purpose": "Setup and Introduction",
    "scene_index": 0
  }},
  ... [continue for all 30 scenes]
}}

Respond ONLY with valid JSON containing exactly these 30 scenes: tag_001 through tag_030.
"""
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )

        story_json = response.choices[0].message.content
        print(f"DEBUG: raw story_json: {story_json!r}")
        if story_json is not None:
            cleaned = strip_code_fences(story_json)
            try:
                story_dict = json.loads(cleaned)
            except Exception as e:
                print(f"Failed to parse story JSON: {e}\nRaw output: {story_json}")
                story_dict = {}
        else:
            story_dict = {}

    # --- PATCH: Ensure all referenced tags exist with meaningful content ---
    referenced = set()
    for node in story_dict.values():
        for ch in node.get("choices", {}).values():
            if isinstance(ch, dict) and "next" in ch:
                referenced.add(ch["next"])
    
    # Create more meaningful intermediate scenes for missing nodes
    missing_tags = referenced - set(story_dict.keys())
    for tag in missing_tags:
        tag_num = int(tag.split('_')[1]) if '_' in tag else 0
        
        # Create intermediate scenes that continue the story instead of ending it
        if tag_num <= 6:  # Create continuing scenes for nodes 1-6
            next_tag = f"tag_{tag_num + 1:03d}" if tag_num < 6 else None
            alt_tag = f"tag_{tag_num + 2:03d}" if tag_num < 7 else None
            
            # Create choices that lead to next progression or conclusion
            choices = {}
            if next_tag and tag_num < 6:
                choices["1"] = {"text": "Continue the adventure", "next": next_tag}
            if alt_tag and tag_num < 6:
                choices["2"] = {"text": "Take a different path", "next": alt_tag}
            elif tag_num == 6:
                choices["1"] = {"text": "Reach the first conclusion", "next": "tag_007"}
                choices["2"] = {"text": "Reach the second conclusion", "next": "tag_008"}
            
            story_dict[tag] = {
                "text": f"{player_name}, your journey continues as you face new challenges and opportunities. Each step brings you closer to your destiny.",
                "choices": choices,
                "media": {"images": [], "audio": []}
            }
        else:  # Create conclusion scenes for nodes 7-8
            story_dict[tag] = {
                "text": f"{player_name}, your epic adventure reaches its climax. Through courage, wisdom, and determination, you have achieved your goal and become the hero you were meant to be. Your legend will be remembered for generations. The End.",
                "choices": {},
                "media": {"images": [], "audio": []}
            }
    # --- END PATCH ---

    # If we are still here, story_dict was produced by LLM path. Assign NPCs to scenes using legacy integrator.
    try:
        from backend.npc.scene_integration import npc_integrator
        npc_assignments = await npc_integrator.assign_npcs_to_scenes(
            player_id=player_id,
            player_name=player_name,
            player_archetype="Hero",
            story_theme=theme,
            story_dict=story_dict,
            num_npcs=5,
        )
        for scene_tag, npc_ids in npc_assignments.items():
            if scene_tag in story_dict:
                story_dict[scene_tag]["npcs_present"] = npc_ids
    except Exception:
        pass

    # --- RECRUITMENT: In legacy LLM path keep existing injection logic ---
    if RECRUITMENT_AVAILABLE:
        for scene_tag, scene in story_dict.items():
            if scene.get("npcs_present"):
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
                        if key in scene["choices"]:
                            scene["choices"][key].update(data)
                        else:
                            scene["choices"][key] = data

    # --- FALLBACK: Ensure we have at least 30 meaningful scenes ---
    # Check if story has enough continuing scenes (not just ending scenes)
    continuing_scenes = sum(1 for scene in story_dict.values() if scene.get("choices"))
    print(f"DEBUG: Generated story has {len(story_dict)} total scenes, {continuing_scenes} continuing scenes")
    
    # More flexible validation: accept stories with 25+ scenes and 20+ continuing scenes
    if len(story_dict) < 25 or continuing_scenes < 20:
        print(f"DEBUG: Insufficient story structure, creating fallback {TOTAL_SCENES}-scene structure")
        story_dict = create_fallback_30_scene_story(theme, intent_vector, player_name)
    
    # --- VALIDATION & AUTO-HEALING ---
    issues = validate(story_dict)
    if issues:
        logger.warning(f"Found {len(issues)} validation issues: {issues}")
        story_dict = auto_heal(story_dict)
        logger.info("Auto-healing completed")
        
        # Re-validate after healing
        remaining_issues = validate(story_dict)
        if remaining_issues:
            logger.error(f"Critical issues remain after healing: {remaining_issues}")
            # Only abort if intro_001 is missing or healing completely failed
            if "intro_001" not in story_dict:
                raise Exception("Critical: Missing intro_001 scene after healing")
    
    first_tag = list(story_dict.keys())[0] if story_dict else "tag_001"
    print(f"DEBUG: story_dict keys: {list(story_dict.keys())}")
    print(f"DEBUG: first_tag: {first_tag}")

    if "media" not in story_dict[first_tag] or not story_dict[first_tag]["media"]:
        story_dict[first_tag]["media"] = None  # or {}
        task: Task = {
            "type": "generate_image",
            "playerId": player_id,
            "sceneTag": first_tag,
            "payload": {}  # Fill with relevant info as needed
        }
        # Idempotency: check if already enqueued/skipped for now
        TASK_QUEUE.put(task)

    return first_tag, story_dict
