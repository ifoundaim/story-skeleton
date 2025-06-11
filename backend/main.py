from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json, os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import random

# Load environment variables
load_dotenv() 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize FastAPI app
app = FastAPI()

# Allow CORS (frontend to backend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File paths
STORY_FILE = "story.json"
STATE_FILE = "player_state.json"
PROFILE_FILE = "player_profile.json"
MAX_SCENES_PER_RUN = 10

# Request models
class ChoiceInput(BaseModel):
    choice: str

class AvatarInput(BaseModel):
    name: str
    archetype: str

class RitualProgressInput(BaseModel):
    step: str

# Utility functions
def load_json(filepath, default):
    if not Path(filepath).exists():
        return default
    with open(filepath, "r") as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# Sprint 1+2 Story Engine (Existing engine)

def generate_scene_with_ai():
    return "You stand before an unknown path, waiting for your choice."

def propose_choice_scene():
    return {"1": "dark_forest", "2": "sunny_meadow"}

def play_scene(tag, story, player):
    if tag not in story:
        text = generate_scene_with_ai()
        choices = propose_choice_scene()
        story[tag] = {"text": text, "choices": choices}
        save_json(STORY_FILE, story)
    else:
        text = story[tag]["text"]
        choices = story[tag].get("choices", {})
    
    player["visited"].append(tag)
    save_json(STATE_FILE, player)
    return {"text": text, "choices": choices}

@app.get("/start")
async def start():
    story = load_json(STORY_FILE, {})
    player = {"courage": 0, "visited": []}
    save_json(STATE_FILE, player)
    return play_scene("start", story, player)

@app.post("/choice")
async def make_choice(data: ChoiceInput):
    story = load_json(STORY_FILE, {})
    player = load_json(STATE_FILE, {"courage": 0, "visited": []})
    last_scene = player["visited"][-1] if player["visited"] else "start"
    next_tag = story[last_scene].get("choices", {}).get(data.choice)
    if not next_tag:
        return {"error": "Invalid choice."}
    return play_scene(next_tag, story, player)

# Sprint 3: Liminal Initiation Layer

@app.get("/liminal")
async def liminal():
    return {
        "steps": ["ASK", "SEEK", "KNOCK"],
        "message": "You stand before the stone doorway. What is your intention?"
    }

@app.post("/liminal")
async def liminal_progress(data: RitualProgressInput):
    step = data.step.upper()
    valid_steps = ["ASK", "SEEK", "KNOCK"]
    if step not in valid_steps:
        return {"error": "Invalid ritual step."}
    if step == "KNOCK":
        return {"message": "The doorway opens.", "advance": True}
    else:
        return {"message": f"You have invoked '{step}'. Continue.", "advance": False}

# Sprint 4: Avatar Creation Layer

@app.post("/avatar")
async def avatar_creation(data: AvatarInput):
    profile = {
        "playerName": data.name,
        "avatarArchetype": data.archetype,
        "initialSoulCodeSeed": "Pending",
        "avatarAppearanceSeed": "Kai Base"
    }
    save_json(PROFILE_FILE, profile)
    return {"message": "Avatar created successfully.", "profile": profile}
