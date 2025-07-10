# purpose_agents/generate_story.py

import openai
import random

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
    }}
  }},
  ...
}}
"""
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )

    story_json = response.choices[0].message["content"]
    story_dict = eval(story_json)  # replace with json.loads() if formatted safely
    first_tag = "tag_001"

    return first_tag, story_dict
