# Choice & Consequence Design Guide

## Overview

The Consequence Fabric system provides Detroit: Become Human-level consequence tracking, creating visible and persistent ripples from player choices throughout the story. This guide covers how to design and implement meaningful consequences that enhance player agency and story depth.

## Core Concepts

### 1. World Flags
World flags are persistent boolean, string, or numeric values that track story state changes.

```python
# Setting flags in beat effects
{
    "effects": {
        "set_world_flag": {
            "city_saved": True,
            "villain_escaped": False,
            "supplies": 15
        }
    }
}

# Checking flags in preconditions
{
    "preconditions": {
        "world_flags[city_saved]": True,
        "world_flags[supplies]": ">=10"
    }
}
```

### 2. Promises
Promises represent commitments made to NPCs or the world, with optional deadlines.

```python
# Adding promises
{
    "effects": {
        "add_promise": {
            "id": "save_city",
            "description": "Save the city from destruction",
            "npc_id": "mayor",  # optional
            "due_by_scene": 15   # optional
        }
    }
}

# Fulfilling promises
{
    "effects": {
        "fulfill_promise": "save_city"
    }
}

# Breaching promises
{
    "effects": {
        "breach_promise": "save_city"
    }
}
```

### 3. Reputation
Four-dimensional reputation system tracking player's perceived character traits.

```python
# Reputation traits
- truthful: 0.0-1.0 (honesty and transparency)
- merciful: 0.0-1.0 (compassion and forgiveness)
- loyal: 0.0-1.0 (commitment to allies)
- resolute: 0.0-1.0 (determination and focus)

# Changing reputation
{
    "effects": {
        "reputation_delta": {
            "truthful": 0.1,    # +0.1 to truthful
            "merciful": -0.05   # -0.05 to merciful
        }
    }
}
```

### 4. Resources
Trackable resources that affect story options and outcomes.

```python
# Resource types
- supplies: int (materials, equipment)
- injuries: int (health status, can be negative for healing)
- time: int (time pressure, deadlines)

# Changing resources
{
    "effects": {
        "resource_delta": {
            "supplies": 5,
            "injuries": -1,  # healing
            "time": -2       # time pressure
        }
    }
}
```

## Design Principles

### 1. Meaningful Consequences
Every choice should have consequences that matter to the player:
- **Immediate**: Visible effects in the current scene
- **Short-term**: Effects that appear within 2-3 scenes
- **Long-term**: Effects that persist throughout the story

### 2. Promise Windows
Use promise deadlines to create urgency and tension:
- **Urgent**: Due within 3-5 scenes
- **Flexible**: Due within 10-15 scenes
- **Open-ended**: No deadline, but affects reputation

### 3. Reputation Balance
Design choices that create interesting trade-offs:
- Truthful vs. Merciful: Honesty vs. Compassion
- Loyal vs. Resolute: Relationships vs. Goals
- Mix of positive and negative changes

### 4. Resource Management
Use resources to create meaningful constraints:
- Limited supplies force strategic choices
- Injuries create vulnerability and healing opportunities
- Time pressure adds urgency to decisions

## Beat Design Patterns

### 1. Consequence Setup
```json
{
    "id": "promise_made",
    "tags": ["bond", "setup"],
    "effects": {
        "add_promise": {
            "id": "help_friend",
            "description": "Help your friend escape",
            "npc_id": "companion",
            "due_by_scene": 12
        },
        "reputation_delta": {
            "loyal": 0.1
        }
    }
}
```

### 2. Consequence Resolution
```json
{
    "id": "promise_kept",
    "tags": ["bond", "resolution"],
    "preconditions": {
        "promises.contains(help_friend)": True
    },
    "effects": {
        "fulfill_promise": "help_friend",
        "reputation_delta": {
            "loyal": 0.2,
            "truthful": 0.1
        },
        "set_world_flag": {
            "friend_saved": True
        }
    }
}
```

### 3. Consequence Failure
```json
{
    "id": "promise_broken",
    "tags": ["conflict", "failure"],
    "preconditions": {
        "promises.contains(help_friend)": True
    },
    "effects": {
        "breach_promise": "help_friend",
        "reputation_delta": {
            "loyal": -0.3,
            "truthful": -0.2
        },
        "set_world_flag": {
            "friend_lost": True
        }
    }
}
```

### 4. Resource-Based Choice
```json
{
    "id": "heal_or_continue",
    "tags": ["choice", "resources"],
    "preconditions": {
        "resources.injuries": ">=2"
    },
    "effects": {
        "resource_delta": {
            "injuries": -2,
            "time": -3
        }
    }
}
```

## Director Scoring Integration

The director automatically rewards beats that resolve outstanding consequences:

### Flag Consumption Bonus
- Beats that clear world flags get scoring bonuses
- Multiple flag clearing provides diminishing returns
- Configurable weight: `flag_consumption: 0.10`

### Promise Window Bonus
- Beats that fulfill promises within their window get higher scores
- Late fulfillment still gets a small bonus
- Configurable weight: `promise_window: 0.10`

## Testing Consequences

### 1. Unit Tests
```python
def test_consequence_effects():
    state = make_state()
    beat = {
        "effects": {
            "set_world_flag": {"test_flag": True},
            "add_promise": {
                "id": "test_promise",
                "description": "Test promise"
            }
        }
    }
    apply_effects(beat, state, [])
    assert state.world_flags["test_flag"] == True
    assert len(state.get_active_promises()) == 1
```

### 2. Integration Tests
```python
def test_director_prefers_consequence_resolution():
    state = make_state_with_pending_promises()
    beats = [
        {"id": "resolve", "effects": {"fulfill_promise": "pending"}},
        {"id": "ignore", "effects": {}}
    ]
    selected = select_next_beat(state, beats, weights, rng)
    assert selected["id"] == "resolve"
```

## Flow Summary Integration

The Flow Summary endpoint provides spoiler-safe consequence tracking:

```python
# GET /flow/summary?player_id=123&chapter=1
{
    "scene_range": [0, 9],
    "choices": [
        {
            "scene_index": 5,
            "text": "Promised to help",
            "tags": ["bond"],
            "effects": {"promise_added": "help_friend"}
        }
    ],
    "consequences": [
        {
            "type": "promise",
            "key": "help_friend",
            "value": "Help your friend escape",
            "npc_id": "companion"
        }
    ],
    "fogged_branches": 3,
    "percent_stats": {"choice_popularity": 0.75}
}
```

## Best Practices

### 1. Consequence Density
- Aim for 2-3 consequences per major choice
- Mix immediate and delayed effects
- Ensure consequences are visible to players

### 2. Promise Design
- Make promises specific and actionable
- Use deadlines to create urgency
- Provide clear success/failure conditions

### 3. Reputation Balance
- Avoid making any trait too high or low
- Create interesting trade-offs
- Use reputation to gate story options

### 4. Resource Management
- Make resources meaningful constraints
- Provide ways to recover from losses
- Use time pressure sparingly

### 5. Testing
- Test consequence chains end-to-end
- Verify director scoring preferences
- Ensure Flow Summary accuracy

## Configuration

Consequence weights are configurable in `config/story_director.yaml`:

```yaml
weights:
  flag_consumption: 0.10     # reward beats that clear world flags
  promise_window: 0.10       # reward beats that fulfill promises within window
```

## Telemetry

Consequence changes are logged for analysis:

```python
log_consequence_change(
    scene_index=10,
    changes={
        "flags_set": ["city_saved"],
        "promises_fulfilled": ["help_friend"],
        "reputation_changes": {"loyal": 0.2}
    }
)
```

## Future Enhancements

1. **Consequence Chains**: Multi-step consequence sequences
2. **NPC Memory**: NPCs remember and react to past choices
3. **Environmental Consequences**: World state changes visible in scenes
4. **Consequence Visualization**: UI showing consequence relationships
5. **Dynamic Promise Generation**: AI-generated promises based on context

This system provides the foundation for creating deeply meaningful player choices that resonate throughout the entire story experience.
