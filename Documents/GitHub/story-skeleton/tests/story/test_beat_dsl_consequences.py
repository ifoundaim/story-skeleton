from backend.story.state import StoryState, Promise, Reputation, Resources
from backend.story.beat_dsl import evaluate_preconditions, apply_effects


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
        world_flags={"city_saved": True, "villain_escaped": False, "supplies": 5},
        promises=[
            Promise(id="save_city", description="Save the city", created_at_scene=5, due_by_scene=15),
            Promise(id="help_npc", description="Help the NPC", created_at_scene=8, npc_id="n1", due_by_scene=12),
        ],
        reputation=Reputation(truthful=0.7, merciful=0.6, loyal=0.8, resolute=0.5),
        resources=Resources(supplies=10, injuries=2, time=5)
    )


def test_world_flag_preconditions():
    """Test world flag preconditions in beat DSL."""
    state = make_state()
    
    # Test flag exists and is True
    beat = {
        "preconditions": {
            "world_flags[city_saved]": True
        }
    }
    assert evaluate_preconditions(beat, state) == True
    
    # Test flag exists and is False
    beat = {
        "preconditions": {
            "world_flags[villain_escaped]": False
        }
    }
    assert evaluate_preconditions(beat, state) == True
    
    # Test flag doesn't exist
    beat = {
        "preconditions": {
            "world_flags[unknown_flag]": True
        }
    }
    assert evaluate_preconditions(beat, state) == False
    
    # Test numeric flag comparison
    beat = {
        "preconditions": {
            "world_flags[supplies]": ">=3"
        }
    }
    assert evaluate_preconditions(beat, state) == True


def test_promise_preconditions():
    """Test promise preconditions in beat DSL."""
    state = make_state()
    
    # Test promise exists
    beat = {
        "preconditions": {
            "promises.contains(save_city)": True
        }
    }
    assert evaluate_preconditions(beat, state) == True
    
    # Test promise doesn't exist
    beat = {
        "preconditions": {
            "promises.contains(unknown_promise)": True
        }
    }
    assert evaluate_preconditions(beat, state) == False
    
    # Test NPC has promise
    beat = {
        "preconditions": {
            "promises.contains(n1)": True
        }
    }
    assert evaluate_preconditions(beat, state) == True


def test_reputation_preconditions():
    """Test reputation preconditions in beat DSL."""
    state = make_state()
    
    # Test reputation threshold
    beat = {
        "preconditions": {
            "reputation.truthful": ">=0.6"
        }
    }
    assert evaluate_preconditions(beat, state) == True
    
    # Test reputation below threshold
    beat = {
        "preconditions": {
            "reputation.resolute": ">=0.8"
        }
    }
    assert evaluate_preconditions(beat, state) == False


def test_resource_preconditions():
    """Test resource preconditions in beat DSL."""
    state = make_state()
    
    # Test resource threshold
    beat = {
        "preconditions": {
            "resources.supplies": ">=5"
        }
    }
    assert evaluate_preconditions(beat, state) == True
    
    # Test resource below threshold
    beat = {
        "preconditions": {
            "resources.time": ">=10"
        }
    }
    assert evaluate_preconditions(beat, state) == False


def test_world_flag_effects():
    """Test world flag effects in beat DSL."""
    state = make_state()
    
    beat = {
        "effects": {
            "set_world_flag": {
                "new_flag": True,
                "supplies": 15
            },
            "clear_world_flag": ["villain_escaped"]
        }
    }
    
    apply_effects(beat, state, [])
    
    assert state.world_flags["new_flag"] == True
    assert state.world_flags["supplies"] == 15
    assert "villain_escaped" not in state.world_flags


def test_promise_effects():
    """Test promise effects in beat DSL."""
    state = make_state()
    
    beat = {
        "effects": {
            "add_promise": {
                "id": "new_promise",
                "description": "New promise",
                "npc_id": "n2",
                "due_by_scene": 20
            },
            "fulfill_promise": "save_city"
        }
    }
    
    apply_effects(beat, state, [])
    
    # Check new promise was added
    new_promise = None
    for promise in state.promises:
        if promise.id == "new_promise":
            new_promise = promise
            break
    
    assert new_promise is not None
    assert new_promise.description == "New promise"
    assert new_promise.npc_id == "n2"
    assert new_promise.due_by_scene == 20
    
    # Check existing promise was fulfilled
    save_city_promise = None
    for promise in state.promises:
        if promise.id == "save_city":
            save_city_promise = promise
            break
    
    assert save_city_promise is not None
    assert save_city_promise.fulfilled == True


def test_reputation_effects():
    """Test reputation effects in beat DSL."""
    state = make_state()
    
    beat = {
        "effects": {
            "reputation_delta": {
                "truthful": 0.1,
                "merciful": -0.05
            }
        }
    }
    
    apply_effects(beat, state, [])
    
    assert abs(state.reputation.truthful - 0.8) < 0.001  # 0.7 + 0.1
    assert abs(state.reputation.merciful - 0.55) < 0.001  # 0.6 - 0.05
    assert state.reputation.loyal == 0.8  # unchanged
    assert state.reputation.resolute == 0.5  # unchanged


def test_resource_effects():
    """Test resource effects in beat DSL."""
    state = make_state()
    
    beat = {
        "effects": {
            "resource_delta": {
                "supplies": 5,
                "injuries": -1,
                "time": -2
            }
        }
    }
    
    apply_effects(beat, state, [])
    
    assert state.resources.supplies == 15  # 10 + 5
    assert state.resources.injuries == 1  # 2 - 1
    assert state.resources.time == 3  # 5 - 2


def test_combined_consequence_effects():
    """Test multiple consequence effects in a single beat."""
    state = make_state()
    
    beat = {
        "effects": {
            "set_world_flag": {"mission_complete": True},
            "clear_world_flag": ["villain_escaped"],
            "add_promise": {
                "id": "final_promise",
                "description": "Final mission",
                "due_by_scene": 25
            },
            "reputation_delta": {"loyal": 0.1},
            "resource_delta": {"supplies": 10}
        }
    }
    
    apply_effects(beat, state, [])
    
    # Check all effects were applied
    assert state.world_flags["mission_complete"] == True
    assert "villain_escaped" not in state.world_flags
    
    final_promise = None
    for promise in state.promises:
        if promise.id == "final_promise":
            final_promise = promise
            break
    assert final_promise is not None
    
    assert state.reputation.loyal == 0.9  # 0.8 + 0.1
    assert state.resources.supplies == 20  # 10 + 10
