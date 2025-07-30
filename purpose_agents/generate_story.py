# purpose_agents/generate_story.py

import openai
import os
import random
import json
import re
from .codex_router import TASK_QUEUE, Task

client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def strip_code_fences(text):
    # Remove leading ``` or ```json (with optional whitespace/newline)
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text.strip())
    # Remove trailing ``` (with optional whitespace/newline)
    text = re.sub(r"```\s*$", "", text.strip())
    return text

def create_fallback_8_node_story(theme: str, intent_vector: list[float]) -> dict:
    """Create a guaranteed 8-node story structure as fallback"""
    return {
        "tag_001": {
            "text": f"Your adventure begins in a realm touched by {theme}. Before you lie two paths that will determine your destiny. Each choice you make will shape the legend you become.",
            "choices": {
                "1": {"text": "Take the path of courage and face the unknown", "next": "tag_002"},
                "2": {"text": "Choose wisdom and seek guidance first", "next": "tag_003"}
            },
            "media": {"images": [], "audio": []},
            "npc_text": ""
        },
        "tag_002": {
            "text": "Your courageous choice leads you into the heart of adventure. Challenges arise that test your resolve, but with each step forward, you grow stronger and more determined.",
            "choices": {
                "1": {"text": "Press onward with unwavering determination", "next": "tag_004"},
                "2": {"text": "Adapt your strategy and find a clever solution", "next": "tag_005"}
            },
            "media": {"images": [], "audio": []},
            "npc_text": ""
        },
        "tag_003": {
            "text": "Your wise approach reveals hidden truths and ancient knowledge. Those you meet along the way offer insights that illuminate the path ahead.",
            "choices": {
                "1": {"text": "Use this knowledge to unlock hidden secrets", "next": "tag_006"},
                "2": {"text": "Share your wisdom to unite unlikely allies", "next": "tag_005"}
            },
            "media": {"images": [], "audio": []},
            "npc_text": ""
        },
        "tag_004": {
            "text": "Your determination carries you through trials that would break lesser heroes. Each obstacle overcome reveals new strengths within yourself.",
            "choices": {
                "1": {"text": "Channel your inner strength for the final challenge", "next": "tag_007"},
                "2": {"text": "Inspire others to join your noble cause", "next": "tag_008"}
            },
            "media": {"images": [], "audio": []},
            "npc_text": ""
        },
        "tag_005": {
            "text": "Your adaptive nature and clever thinking open new possibilities. Creative solutions lead to unexpected alliances and discoveries.",
            "choices": {
                "1": {"text": "Embrace the power of collaboration", "next": "tag_008"},
                "2": {"text": "Trust in your own unique abilities", "next": "tag_007"}
            },
            "media": {"images": [], "audio": []},
            "npc_text": ""
        },
        "tag_006": {
            "text": "The secrets you've unlocked reveal the true nature of your quest. Ancient powers stir, recognizing you as their chosen champion.",
            "choices": {
                "1": {"text": "Accept the mantle of destiny", "next": "tag_007"},
                "2": {"text": "Forge your own path to victory", "next": "tag_008"}
            },
            "media": {"images": [], "audio": []},
            "npc_text": ""
        },
        "tag_007": {
            "text": f"Your journey reaches its triumphant conclusion. Through courage, wisdom, and perseverance, you have not only achieved your goal but also discovered the true hero within yourself. Your legend in the realm of {theme} will inspire generations to come. The End.",
            "choices": {},
            "media": {"images": [], "audio": []},
            "npc_text": ""
        },
        "tag_008": {
            "text": f"Your adventure culminates in an unexpected but deeply satisfying victory. By staying true to your values and embracing both strength and compassion, you have brought balance to the world of {theme}. Your name will be remembered as a beacon of hope. The End.",
            "choices": {},
            "media": {"images": [], "audio": []},
            "npc_text": ""
        }
    }

async def generate_story(player_id: str, theme: str, intent_vector: list[float]) -> tuple[str, dict]:
    prompt = f"""
You are a mythic storyteller AI.
Generate a complete 8-node branching story based on:

- Theme: {theme}
- Intent: {intent_vector[:10]}... (truncated)
- Audience: player on a hero's journey

CRITICAL: You must create exactly 8 complete story nodes. Structure the story as follows:

1. **tag_001**: Opening scene with 2 choices leading to tag_002 and tag_003
2. **tag_002**: First path continuation with 2 choices leading to tag_004 and tag_005  
3. **tag_003**: Second path continuation with 2 choices leading to tag_006 and tag_007
4. **tag_004**: Mid-story scene with 2 choices leading to tag_008 and tag_006
5. **tag_005**: Mid-story scene with 2 choices leading to tag_007 and tag_008
6. **tag_006**: Mid-story scene with 2 choices leading to tag_007 and tag_008
7. **tag_007**: Conclusion scene - no choices (story ending)
8. **tag_008**: Conclusion scene - no choices (story ending)

REQUIREMENTS:
- Generate ALL 8 nodes with complete text and proper structure
- Nodes tag_001 through tag_006 MUST have 2 choices each
- Only tag_007 and tag_008 should be ending nodes without choices
- Each scene must advance the story meaningfully
- Make the story engaging with meaningful choices that impact the narrative

Example structure:
{{
  "tag_001": {{
    "text": "[Opening scene description]",
    "choices": {{
      "1": {{"text": "[Choice 1 description]", "next": "tag_002"}},
      "2": {{"text": "[Choice 2 description]", "next": "tag_003"}}
    }},
    "media": {{"images": [], "audio": []}}
  }},
  "tag_002": {{
    "text": "[Continuation scene]",
    "choices": {{
      "1": {{"text": "[Choice 1]", "next": "tag_004"}},
      "2": {{"text": "[Choice 2]", "next": "tag_005"}}
    }},
    "media": {{"images": [], "audio": []}}
  }},
  ... [continue for all 8 nodes]
}}

Respond ONLY with valid JSON containing exactly these 8 nodes: tag_001, tag_002, tag_003, tag_004, tag_005, tag_006, tag_007, tag_008.
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
            next_tag = f"tag_{tag_num + 1:03d}" if tag_num < 8 else None
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
                "text": f"Your journey continues as you face new challenges and opportunities. Each step brings you closer to your destiny.",
                "choices": choices,
                "media": {"images": [], "audio": []}
            }
        else:  # Create conclusion scenes for nodes 7-8
            story_dict[tag] = {
                "text": f"Your epic adventure reaches its climax. Through courage, wisdom, and determination, you have achieved your goal and become the hero you were meant to be. Your legend will be remembered for generations. The End.",
                "choices": {},
                "media": {"images": [], "audio": []}
            }
    # --- END PATCH ---

    # --- PATCH: Ensure npc_text, trust_delta, and media in each node/choice ---
    import uuid
    
    # Generate consistent UUIDs for default NPCs
    lyra_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, f"default:lyra"))
    orin_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, f"default:orin"))
    companion_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, f"default:companion"))
    
    for i, node in enumerate(story_dict.values()):
        # Add NPC presence information to scenes
        if i == 0:
            # Opening scene - both NPCs present
            node["npcs_present"] = [lyra_uuid, orin_uuid]
        elif i in [1, 2]:
            # Early scenes - alternate NPC presence
            node["npcs_present"] = [lyra_uuid] if i == 1 else [orin_uuid]
        elif i in [3, 4, 5]:
            # Mid-story - both NPCs present for group dynamics
            node["npcs_present"] = [lyra_uuid, orin_uuid]
        else:
            # Ending scenes - single companion
            node["npcs_present"] = [companion_uuid]
        
        node.setdefault("npc_text", "")
        node.setdefault("media", {"images": [], "audio": []})
        choices = node.get("choices", {})
        
        for j, ch in enumerate(choices.values()):
            if isinstance(ch, dict):
                # Maintain backward compatibility
                ch.setdefault("trust_delta", 0.0)
                
                # Add multi-NPC trust deltas based on choice context
                if (i == 0 and j == 0):
                    # First choice - courage/action affects both NPCs differently
                    ch["npc_trust_deltas"] = {
                        lyra_uuid: 0.2,  # Lyra appreciates courage
                        orin_uuid: -0.1  # Orin is more cautious
                    }
                    ch["emotion_delta"] = [0.3, -0.1, 0, 0, 0.2, 0, 0.1, 0]
                    ch["soulmap_delta"] = [0.2, 0.1, 0, 0, 0, 0, 0, 0] + [0.0] * 56
                elif (i == 0 and j == 1):
                    # Second choice - caution/wisdom
                    ch["npc_trust_deltas"] = {
                        lyra_uuid: -0.1,  # Lyra prefers action
                        orin_uuid: 0.2    # Orin appreciates wisdom
                    }
                    ch["emotion_delta"] = [-0.2, 0.2, 0, 0.1, 0, 0, 0, -0.3]
                    ch["soulmap_delta"] = [-0.1, 0.2, 0.1, 0, 0, 0, 0, 0] + [0.0] * 56
                elif (i == 1 and j == 0):
                    # Compassion/helping - affects present NPC
                    present_npcs = node.get("npcs_present", [])
                    if present_npcs:
                        ch["npc_trust_deltas"] = {present_npcs[0]: 0.3}
                    ch["emotion_delta"] = [0, 0, 0.4, -0.2, 0, 0.1, 0, 0]
                    ch["soulmap_delta"] = [0, 0, 0.3, 0.2, 0, 0, 0, 0] + [0.0] * 56
                elif (i == 2 and j == 0):
                    # Different NPC interaction
                    present_npcs = node.get("npcs_present", [])
                    if present_npcs:
                        ch["npc_trust_deltas"] = {present_npcs[0]: 0.15}
                elif (i >= 3 and len(node.get("npcs_present", [])) > 1):
                    # Group scenes - choices affect multiple NPCs
                    if j == 0:
                        ch["npc_trust_deltas"] = {
                            lyra_uuid: 0.1,
                            orin_uuid: 0.1
                        }
                    else:
                        ch["npc_trust_deltas"] = {
                            lyra_uuid: 0.05,
                            orin_uuid: 0.15
                        }
    # --- END PATCH ---

    # --- FALLBACK: Ensure we have at least 8 meaningful nodes ---
    # Check if story has enough continuing nodes (not just ending nodes)
    continuing_nodes = sum(1 for node in story_dict.values() if node.get("choices"))
    print(f"DEBUG: Generated story has {len(story_dict)} total nodes, {continuing_nodes} continuing nodes")
    
    if len(story_dict) < 8 or continuing_nodes < 6:
        print(f"DEBUG: Insufficient story structure, creating fallback 8-node structure")
        story_dict = create_fallback_8_node_story(theme, intent_vector)
    
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
