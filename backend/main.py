```python
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from typing import Dict, Any
from trust import TrustManager

app = FastAPI()

# Load player profiles
def load_player_profiles() -> Dict[str, Any]:
    with open('player_profile.json', 'r') as f:
        return json.load(f)

# Save player profiles
def save_player_profiles(data: Dict[str, Any]) -> None:
    with open('player_profile.json', 'w') as f:
        json.dump(data, f, indent=4)

class SoulSeedRequest(BaseModel):
    avatarArchetype: str

class SoulSeedResponse(BaseModel):
    soulSeedId: str
    initialSceneTag: str

@app.post("/soulseed", response_model=SoulSeedResponse)
async def create_soul_seed(request: SoulSeedRequest):
    player_profiles = load_player_profiles()
    
    # Generate soul seed ID and initial scene tag based on avatar archetype
    soul_seed_id = f"seed-{request.avatarArchetype}-{len(player_profiles) + 1}"
    initial_scene_tag = f"scene-{request.avatarArchetype}"

    # Persist soul seed in player profile
    player_profiles[soul_seed_id] = {
        "avatarArchetype": request.avatarArchetype,
        "initialSceneTag": initial_scene_tag
    }
    save_player_profiles(player_profiles)

    return SoulSeedResponse(soulSeedId=soul_seed_id, initialSceneTag=initial_scene_tag)

# Trust Manager integration
trust_manager = TrustManager()

@app.post("/play_scene")
async def play_scene(scene_id: str, player_id: str, score: int):
    # Update trust score
    trust_manager.update(player_id, score)
    return {"message": "Scene played successfully."}
```

```python
# trust.py
import json
from typing import Dict

class TrustManager:
    def __init__(self, filename: str = 'trust_data.json'):
        self.filename = filename
        self.trust_data = self.load()

    def load(self) -> Dict[str, int]:
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save(self) -> None:
        with open(self.filename, 'w') as f:
            json.dump(self.trust_data, f, indent=4)

    def update(self, player_id: str, score: int) -> None:
        if player_id in self.trust_data:
            self.trust_data[player_id] += score
        else:
            self.trust_data[player_id] = score
        self.save()
```

```json
// player_profile.json
{}
```

```json
// trust_data.json
{}
```

Make sure to create the `player_profile.json` and `trust_data.json` files in the same directory as your FastAPI application to avoid file not found errors.
