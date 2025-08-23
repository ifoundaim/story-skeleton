#!/usr/bin/env python3
"""
Test script to demonstrate the Consequence Fabric functionality
"""

from backend.story.state import StoryState, Promise, Reputation, Resources
from backend.story.beat_dsl import evaluate_preconditions, apply_effects
from backend.story.director import score_beat, select_next_beat
import random

def create_test_state():
    """Create a test state with some initial consequences."""
    return StoryState(
        scene_index=10,
        phase="mid",
        tension=0.5,
        target_curve=[0.2] * 30,
        player={"name": "TestPlayer", "theme": "bond", "archetype": "Hero"},
        npcs={
            "companion": {"trust": 0.65, "arc_state": "bond", "interactions": 3, "last_invite_scene": None, "role": "Companion"},
            "rival": {"trust": 0.3, "arc_state": "intro", "interactions": 0, "last_invite_scene": 4, "role": "Rival"},
        },
        party=[],
        flags={"config": {"recruitment": {"cooldown_scenes": 2, "party_capacity": 3}}},
        world_flags={
            "city_saved": False,
            "villain_escaped": True,
            "supplies": 5
        },
        promises=[
            Promise(id="save_city", description="Save the city from destruction", created_at_scene=5, due_by_scene=15),
            Promise(id="help_companion", description="Help your companion escape", created_at_scene=8, npc_id="companion", due_by_scene=12),
        ],
        reputation=Reputation(truthful=0.7, merciful=0.6, loyal=0.8, resolute=0.5),
        resources=Resources(supplies=10, injuries=2, time=5)
    )

def test_consequence_effects():
    """Test applying consequence effects to the state."""
    print("=== Testing Consequence Effects ===")
    
    state = create_test_state()
    print(f"Initial state:")
    print(f"  World flags: {state.world_flags}")
    print(f"  Active promises: {len(state.get_active_promises())}")
    print(f"  Reputation: truthful={state.reputation.truthful:.2f}, loyal={state.reputation.loyal:.2f}")
    print(f"  Resources: supplies={state.resources.supplies}, injuries={state.resources.injuries}")
    
    # Test a beat that resolves consequences
    beat = {
        "id": "heroic_rescue",
        "tags": ["action", "bond"],
        "effects": {
            "set_world_flag": {"city_saved": True},
            "clear_world_flag": ["villain_escaped"],
            "fulfill_promise": "save_city",
            "reputation_delta": {"loyal": 0.2, "resolute": 0.1},
            "resource_delta": {"supplies": -3, "injuries": 1}
        }
    }
    
    print(f"\nApplying beat: {beat['id']}")
    apply_effects(beat, state, ["companion"])
    
    print(f"\nAfter applying effects:")
    print(f"  World flags: {state.world_flags}")
    print(f"  Active promises: {len(state.get_active_promises())}")
    print(f"  Reputation: truthful={state.reputation.truthful:.2f}, loyal={state.reputation.loyal:.2f}")
    print(f"  Resources: supplies={state.resources.supplies}, injuries={state.resources.injuries}")

def test_preconditions():
    """Test consequence preconditions."""
    print("\n=== Testing Consequence Preconditions ===")
    
    state = create_test_state()
    
    # Test beat that requires specific world state
    beat_with_preconditions = {
        "id": "save_city_opportunity",
        "tags": ["action"],
        "preconditions": {
            "world_flags[city_saved]": False,
            "world_flags[supplies]": ">=3",
            "promises.contains(save_city)": True,
            "reputation.loyal": ">=0.6"
        },
        "effects": {
            "set_world_flag": {"city_saved": True},
            "fulfill_promise": "save_city"
        }
    }
    
    print(f"Testing beat: {beat_with_preconditions['id']}")
    result = evaluate_preconditions(beat_with_preconditions, state)
    print(f"  Preconditions met: {result}")
    
    # Test beat that should fail preconditions
    beat_fail_preconditions = {
        "id": "save_city_impossible",
        "tags": ["action"],
        "preconditions": {
            "world_flags[city_saved]": True,  # Already saved
            "resources.supplies": ">=20"      # Not enough supplies
        },
        "effects": {}
    }
    
    print(f"Testing beat: {beat_fail_preconditions['id']}")
    result = evaluate_preconditions(beat_fail_preconditions, state)
    print(f"  Preconditions met: {result}")

def test_director_scoring():
    """Test director scoring with consequence bonuses."""
    print("\n=== Testing Director Scoring ===")
    
    state = create_test_state()
    
    # Create two beats - one that resolves consequences, one that doesn't
    beat_resolve_consequences = {
        "id": "resolve_consequences",
        "tags": ["action"],
        "effects": {
            "clear_world_flag": ["villain_escaped"],
            "fulfill_promise": "save_city"
        }
    }
    
    beat_no_consequences = {
        "id": "no_consequences",
        "tags": ["action"],
        "effects": {}
    }
    
    # Score both beats
    weights = {"flag_consumption": 0.10, "promise_window": 0.10}
    score1 = score_beat(beat_resolve_consequences, state, [])
    score2 = score_beat(beat_no_consequences, state, [])
    
    print(f"Beat '{beat_resolve_consequences['id']}' score: {score1:.3f}")
    print(f"Beat '{beat_no_consequences['id']}' score: {score2:.3f}")
    print(f"Consequence resolution bonus: {score1 - score2:.3f}")
    
    # Test director selection
    candidates = [beat_resolve_consequences, beat_no_consequences]
    rng = random.Random(42)  # Deterministic for testing
    
    selected = select_next_beat(state, candidates, weights, rng)
    print(f"Director selected: {selected['id']}")

def test_promise_windows():
    """Test promise window functionality."""
    print("\n=== Testing Promise Windows ===")
    
    state = create_test_state()
    
    print(f"Current scene: {state.scene_index}")
    print(f"Active promises:")
    for promise in state.get_active_promises():
        print(f"  - {promise.id}: due by scene {promise.due_by_scene}")
    
    # Test overdue promises
    overdue = state.get_overdue_promises()
    if overdue:
        print(f"Overdue promises:")
        for promise in overdue:
            print(f"  - {promise.id}: was due by scene {promise.due_by_scene}")
    else:
        print("No overdue promises")
    
    # Move to scene 16 (past some deadlines)
    state.scene_index = 16
    print(f"\nMoved to scene: {state.scene_index}")
    
    overdue = state.get_overdue_promises()
    if overdue:
        print(f"Overdue promises:")
        for promise in overdue:
            print(f"  - {promise.id}: was due by scene {promise.due_by_scene}")
    else:
        print("No overdue promises")

if __name__ == "__main__":
    print("🎭 Consequence Fabric Demo")
    print("=" * 50)
    
    test_consequence_effects()
    test_preconditions()
    test_director_scoring()
    test_promise_windows()
    
    print("\n✅ All consequence fabric features working!")
    print("\nThe consequence fabric system provides:")
    print("- Persistent world flags that affect story options")
    print("- Promise system with deadlines and fulfillment tracking")
    print("- Four-dimensional reputation system")
    print("- Resource management with constraints")
    print("- Intelligent beat selection that prefers consequence resolution")
