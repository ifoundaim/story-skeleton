# purpose_agents/generate_story.py

import openai
import os
import random
import json
import re

client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def strip_code_fences(text):
    # Remove leading ``` or ```json (with optional whitespace/newline)
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text.strip())
    # Remove trailing ``` (with optional whitespace/newline)
    text = re.sub(r"```\s*$", "", text.strip())
    return text

async def generate_story(player_id: str, theme: str, intent_vector: list[float]) -> tuple[str, dict]:
    prompt = f"""
You are a mythic storyteller AI.
Generate a 3-node branching story based on:

- Theme: {theme}
- Intent: {intent_vector[:10]}... (truncated)
- Audience: player on a hero's journey

Format:
{{
  "tag_001": {{
    "text": "...",
    "choices": {{
      "1": {{"text": "...", "next": "tag_002"}},
      "2": {{"text": "...", "next": "tag_003"}}
    }},
    "media": {{
      "images": [],
      "audio": []
    }}
  }},
  ...
}}
Respond ONLY with valid JSON in the following format:
{{
  "tag_001": {{
    "text": "...",
    "choices": {{
      "1": {{"text": "...", "next": "tag_002"}},
      "2": {{"text": "...", "next": "tag_003"}}
    }},
    "media": {{
      "images": [],
      "audio": []
    }}
  }},
  ...
}}
Each choice must be an object with "text" and "next" keys.
Each node must include a "media" object with "images" and "audio" arrays (initially empty).
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

    # --- PATCH: Ensure all referenced tags exist ---
    referenced = set()
    for node in story_dict.values():
        for ch in node.get("choices", {}).values():
            if isinstance(ch, dict) and "next" in ch:
                referenced.add(ch["next"])
    for tag in referenced:
        if tag not in story_dict:
            story_dict[tag] = {"text": "The story ends here.", "choices": {}, "media": {"images": [], "audio": []}}
    # --- END PATCH ---

    # --- PATCH: Ensure npc_text, trust_delta, and media in each node/choice ---
    for node in story_dict.values():
        node.setdefault("npc_text", "")
        node.setdefault("media", {"images": [], "audio": []})
        choices = node.get("choices", {})
        for ch in choices.values():
            if isinstance(ch, dict):
                ch.setdefault("trust_delta", 0.0)
    # --- END PATCH ---

    first_tag = list(story_dict.keys())[0] if story_dict else "tag_001"
    print(f"DEBUG: story_dict keys: {list(story_dict.keys())}")
    print(f"DEBUG: first_tag: {first_tag}")
    return first_tag, story_dict
