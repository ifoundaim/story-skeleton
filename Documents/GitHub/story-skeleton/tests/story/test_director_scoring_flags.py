from backend.story.state import StoryState, Promise, Reputation, Resources
from backend.story.director import score_beat, select_next_beat
import random


def make_state() -> StoryState:
    return StoryState(
        scene_index=10,
        phase="mid",
        tension=0.5,
        target_curve=[0.2] * 30,
        player={"name": "P", "theme": "bond", "archetype": "Hero"},
        npcs={
            "n1": {"trust": 0.65, "arc_state": "bond", "interactions": 3, "last_invite_scene": None, "role": "Companion"},
            "n2": {"trust": 0.3, "arc_state": "intro", "interactions": 0, "last_invite_scene": 4, "role": "Rival"},
        },
        party=[],
        flags={"config": {"recruitment": {"cooldown_scenes": 2, "party_capacity": 3}}},
        world_flags={"city_saved": True, "villain_escaped": False, "supplies": 5, "mission_pending": True},
        promises=[
            Promise(id="save_city", description="Save the city", created_at_scene=5, due_by_scene=15),
            Promise(id="help_npc", description="Help the NPC", created_at_scene=8, npc_id="n1", due_by_scene=12),
        ],
        reputation=Reputation(truthful=0.7, merciful=0.6, loyal=0.8, resolute=0.5),
        resources=Resources(supplies=10, injuries=2, time=5)
    )


def test_flag_consumption_bonus():
    """Test that beats that clear flags get scoring bonuses."""
    state = make_state()
    
    # Beat that clears one flag
    beat_clear_one = {
        "id": "clear_one",
        "tags": ["action"],
        "effects": {
            "clear_world_flag": ["villain_escaped"]
        }
    }
    
    # Beat that clears multiple flags
    beat_clear_multiple = {
        "id": "clear_multiple",
        "tags": ["action"],
        "effects": {
            "clear_world_flag": ["villain_escaped", "mission_pending"]
        }
    }
    
    # Beat that clears non-existent flags
    beat_clear_nonexistent = {
        "id": "clear_nonexistent",
        "tags": ["action"],
        "effects": {
            "clear_world_flag": ["nonexistent_flag"]
        }
    }
    
    # Beat with no flag clearing
    beat_no_clear = {
        "id": "no_clear",
        "tags": ["action"],
        "effects": {}
    }
    
    # Score all beats
    weights = {"flag_consumption": 0.10}
    score1 = score_beat(beat_clear_one, state, [])
    score2 = score_beat(beat_clear_multiple, state, [])
    score3 = score_beat(beat_clear_nonexistent, state, [])
    score4 = score_beat(beat_no_clear, state, [])
    
    # Multiple flag clearing should score higher than single
    assert score2 > score1
    
    # Single flag clearing should score higher than no clearing
    assert score1 > score4
    
    # Clearing non-existent flags should score same as no clearing
    assert abs(score3 - score4) < 0.01


def test_promise_window_bonus():
    """Test that beats that fulfill promises within window get scoring bonuses."""
    # Create separate states for each test case
    state_in_window = make_state()  # Scene 10, help_npc due by scene 12
    
    # Beat that fulfills promise within window
    beat_fulfill_in_window = {
        "id": "fulfill_in_window",
        "tags": ["bond"],
        "effects": {
            "fulfill_promise": "help_npc"
        }
    }
    
    # Beat that fulfills promise after deadline
    state_late = make_state()  # Fresh state
    state_late.scene_index = 15  # Move past deadline
    beat_fulfill_late = {
        "id": "fulfill_late",
        "tags": ["bond"],
        "effects": {
            "fulfill_promise": "help_npc"  # Same promise, but late
        }
    }
    
    # Beat with no promise fulfillment
    state_no_fulfill = make_state()  # Fresh state
    beat_no_fulfill = {
        "id": "no_fulfill",
        "tags": ["bond"],
        "effects": {}
    }
    
    # Score beats
    weights = {"promise_window": 0.10}
    score1 = score_beat(beat_fulfill_in_window, state_in_window, [])
    score2 = score_beat(beat_fulfill_late, state_late, [])
    score3 = score_beat(beat_no_fulfill, state_no_fulfill, [])
    
    # Fulfilling within window should score higher than late
    assert score1 > score2, f"Score1: {score1}, Score2: {score2}"
    
    # Fulfilling late should still score higher than no fulfillment
    assert score2 > score3, f"Score2: {score2}, Score3: {score3}"


def test_promise_window_bonus_already_resolved():
    """Test that beats don't get bonus for already resolved promises."""
    state = make_state()
    
    # Fulfill the promise first
    state.fulfill_promise("help_npc")
    
    # Beat that tries to fulfill already fulfilled promise
    beat_fulfill_resolved = {
        "id": "fulfill_resolved",
        "tags": ["bond"],
        "effects": {
            "fulfill_promise": "help_npc"
        }
    }
    
    # Beat with no promise fulfillment
    beat_no_fulfill = {
        "id": "no_fulfill",
        "tags": ["bond"],
        "effects": {}
    }
    
    # Score beats
    weights = {"promise_window": 0.10}
    score1 = score_beat(beat_fulfill_resolved, state, [])
    score2 = score_beat(beat_no_fulfill, state, [])
    
    # Should score the same since promise is already resolved
    assert abs(score1 - score2) < 0.01


def test_combined_consequence_scoring():
    """Test that beats with multiple consequence effects get combined bonuses."""
    state = make_state()
    
    # Beat that clears flags AND fulfills promises
    beat_combined = {
        "id": "combined",
        "tags": ["action", "bond"],
        "effects": {
            "clear_world_flag": ["villain_escaped"],
            "fulfill_promise": "help_npc"
        }
    }
    
    # Beat that only clears flags
    beat_flags_only = {
        "id": "flags_only",
        "tags": ["action"],
        "effects": {
            "clear_world_flag": ["villain_escaped"]
        }
    }
    
    # Beat that only fulfills promises
    beat_promises_only = {
        "id": "promises_only",
        "tags": ["bond"],
        "effects": {
            "fulfill_promise": "help_npc"
        }
    }
    
    # Beat with no consequences
    beat_none = {
        "id": "none",
        "tags": ["action"],
        "effects": {}
    }
    
    # Score all beats
    weights = {"flag_consumption": 0.10, "promise_window": 0.10}
    score_combined = score_beat(beat_combined, state, [])
    score_flags = score_beat(beat_flags_only, state, [])
    score_promises = score_beat(beat_promises_only, state, [])
    score_none = score_beat(beat_none, state, [])
    
    # Combined should score highest
    assert score_combined > score_flags
    assert score_combined > score_promises
    assert score_combined > score_none
    
    # Individual effects should score higher than none
    assert score_flags > score_none
    assert score_promises > score_none


def test_director_selection_with_consequences():
    """Test that director selects beats with consequence bonuses when appropriate."""
    state = make_state()
    
    # Create two similar beats, one with consequence effects
    beat_with_consequences = {
        "id": "with_consequences",
        "tags": ["action"],
        "effects": {
            "clear_world_flag": ["villain_escaped"],
            "fulfill_promise": "help_npc"
        }
    }
    
    beat_without_consequences = {
        "id": "without_consequences",
        "tags": ["action"],
        "effects": {}
    }
    
    candidates = [beat_with_consequences, beat_without_consequences]
    weights = {"flag_consumption": 0.10, "promise_window": 0.10}
    
    # Use deterministic RNG for testing
    rng = random.Random(42)
    
    # Run selection multiple times to ensure consistency
    selections = []
    for _ in range(10):
        selected = select_next_beat(state, candidates, weights, rng)
        selections.append(selected["id"])
    
    # Should consistently select the beat with consequences
    assert all(selection == "with_consequences" for selection in selections)


def test_consequence_weights_in_config():
    """Test that consequence weights from config are properly applied."""
    # Create states with different weights in config
    state_low = make_state()
    state_low.flags["config"] = {"weights": {"flag_consumption": 0.05}}
    
    state_high = make_state()
    state_high.flags["config"] = {"weights": {"flag_consumption": 0.20}}
    
    # Beat with flag clearing
    beat = {
        "id": "test_beat",
        "tags": ["action"],
        "effects": {
            "clear_world_flag": ["villain_escaped"]
        }
    }
    
    score_low = score_beat(beat, state_low, [])
    score_high = score_beat(beat, state_high, [])
    
    # Higher weight should result in higher score
    assert score_high > score_low, f"Score_high: {score_high}, Score_low: {score_low}"
