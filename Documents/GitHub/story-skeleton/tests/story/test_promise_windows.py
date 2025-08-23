from backend.story.state import StoryState, Promise
from backend.story.beat_dsl import promise_window


def make_state(scene_index: int = 10) -> StoryState:
    return StoryState(
        scene_index=scene_index,
        phase="mid",
        tension=0.5,
        target_curve=[0.2] * 30,
        player={"name": "P", "theme": "bond", "archetype": "Hero"},
        npcs={
            "n1": {"trust": 0.65, "arc_state": "bond", "interactions": 3, "last_invite_scene": None, "role": "Companion"},
        },
        party=[],
        flags={"config": {"recruitment": {"cooldown_scenes": 2, "party_capacity": 3}}},
        promises=[
            Promise(id="urgent", description="Urgent task", created_at_scene=5, due_by_scene=8),
            Promise(id="flexible", description="Flexible task", created_at_scene=5, due_by_scene=15),
            Promise(id="no_deadline", description="No deadline", created_at_scene=5, due_by_scene=None),
        ]
    )


def test_promise_window_helper():
    """Test the promise_window helper function."""
    # Within window
    assert promise_window(5, 10) == True
    assert promise_window(10, 10) == True  # On deadline
    
    # Past deadline
    assert promise_window(12, 10) == False
    
    # No deadline (always in window)
    assert promise_window(5, None) == True
    assert promise_window(100, None) == True


def test_fulfill_promise_within_window():
    """Test fulfilling a promise within its window."""
    state = make_state(7)  # Scene 7, promise due by scene 8
    
    # Fulfill urgent promise within window
    result = state.fulfill_promise("urgent")
    assert result == True
    
    # Check promise is fulfilled
    urgent_promise = None
    for promise in state.promises:
        if promise.id == "urgent":
            urgent_promise = promise
            break
    
    assert urgent_promise is not None
    assert urgent_promise.fulfilled == True
    assert urgent_promise.breached == False


def test_fulfill_promise_after_deadline():
    """Test fulfilling a promise after its deadline."""
    state = make_state(10)  # Scene 10, promise due by scene 8
    
    # Fulfill urgent promise after deadline
    result = state.fulfill_promise("urgent")
    assert result == True  # Still can be fulfilled, just late
    
    # Check promise is fulfilled
    urgent_promise = None
    for promise in state.promises:
        if promise.id == "urgent":
            urgent_promise = promise
            break
    
    assert urgent_promise is not None
    assert urgent_promise.fulfilled == True
    assert urgent_promise.breached == False


def test_breach_promise():
    """Test breaching a promise."""
    state = make_state(10)  # Scene 10, promise due by scene 8
    
    # Breach urgent promise
    result = state.breach_promise("urgent")
    assert result == True
    
    # Check promise is breached
    urgent_promise = None
    for promise in state.promises:
        if promise.id == "urgent":
            urgent_promise = promise
            break
    
    assert urgent_promise is not None
    assert urgent_promise.fulfilled == False
    assert urgent_promise.breached == True


def test_cannot_fulfill_already_fulfilled_promise():
    """Test that already fulfilled promises cannot be fulfilled again."""
    state = make_state(7)
    
    # Fulfill promise first time
    result1 = state.fulfill_promise("urgent")
    assert result1 == True
    
    # Try to fulfill again
    result2 = state.fulfill_promise("urgent")
    assert result2 == False


def test_cannot_fulfill_breached_promise():
    """Test that breached promises cannot be fulfilled."""
    state = make_state(10)
    
    # Breach promise first
    result1 = state.breach_promise("urgent")
    assert result1 == True
    
    # Try to fulfill breached promise
    result2 = state.fulfill_promise("urgent")
    assert result2 == False


def test_cannot_breach_fulfilled_promise():
    """Test that fulfilled promises cannot be breached."""
    state = make_state(7)
    
    # Fulfill promise first
    result1 = state.fulfill_promise("urgent")
    assert result1 == True
    
    # Try to breach fulfilled promise
    result2 = state.breach_promise("urgent")
    assert result2 == False


def test_get_active_promises():
    """Test getting active (unfulfilled, unbreached) promises."""
    state = make_state(10)
    
    # Initially all promises should be active
    active = state.get_active_promises()
    assert len(active) == 3
    
    # Fulfill one promise
    state.fulfill_promise("urgent")
    active = state.get_active_promises()
    assert len(active) == 2
    
    # Breach another promise
    state.breach_promise("flexible")
    active = state.get_active_promises()
    assert len(active) == 1
    assert active[0].id == "no_deadline"


def test_get_active_promises_by_npc():
    """Test getting active promises filtered by NPC."""
    state = make_state(10)
    
    # Add a promise for a specific NPC
    state.add_promise("npc_promise", "NPC task", npc_id="n1", due_by_scene=15)
    
    # Get active promises for NPC
    active = state.get_active_promises(npc_id="n1")
    assert len(active) == 1
    assert active[0].id == "npc_promise"
    
    # Get active promises for non-existent NPC
    active = state.get_active_promises(npc_id="nonexistent")
    assert len(active) == 0


def test_get_overdue_promises():
    """Test getting promises that are past their due date."""
    state = make_state(10)  # Scene 10
    
    # urgent is due by scene 8, so it's overdue
    overdue = state.get_overdue_promises()
    assert len(overdue) == 1
    assert overdue[0].id == "urgent"
    
    # flexible is due by scene 15, so it's not overdue
    # no_deadline has no deadline, so it's not overdue
    
    # Move to scene 16
    state.scene_index = 16
    overdue = state.get_overdue_promises()
    assert len(overdue) == 2  # urgent and flexible are both overdue


def test_promise_with_no_deadline():
    """Test promises with no deadline."""
    state = make_state(10)
    
    # no_deadline has no deadline
    no_deadline_promise = None
    for promise in state.promises:
        if promise.id == "no_deadline":
            no_deadline_promise = promise
            break
    
    assert no_deadline_promise is not None
    assert no_deadline_promise.due_by_scene is None
    
    # Should not be in overdue list
    overdue = state.get_overdue_promises()
    overdue_ids = [p.id for p in overdue]
    assert "no_deadline" not in overdue_ids
