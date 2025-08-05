# SPR-NPC08 – Dynamic NPC Scene Integration

## Overview

The Dynamic NPC Scene Integration system automatically places dynamically generated NPCs into appropriate story scenes based on their roles, archetypes, and narrative hooks. This creates a personalized narrative experience where NPCs appear at the right time and in the right context.

## Architecture

### Core Components

#### 1. NPCSceneIntegrator Class
- **Role-based Assignment:** Assigns NPCs based on their roles and story progression
- **Progressive Introduction:** NPCs appear gradually throughout the story
- **Narrative Hook Matching:** Places NPCs in scenes that match their narrative hooks
- **Caching:** Maintains NPC assignments per player for consistency

#### 2. Integration Points
- **Story Generation:** Replaces hardcoded NPC assignments in `purpose_agents/generate_story.py`
- **Scene Response:** Enhanced scene response logic in `backend/main.py`
- **NPC Profile Management:** Ensures all assigned NPCs have corresponding profiles

### Assignment Logic

#### Role-Based Placement
```python
role_assignment_rules = {
    "Mentor": {"acts": [1], "max_per_scene": 1, "priority": 1},
    "Guide": {"acts": [1], "max_per_scene": 1, "priority": 2},
    "Companion": {"acts": [1, 2], "max_per_scene": 2, "priority": 3},
    "Rival": {"acts": [2, 3], "max_per_scene": 1, "priority": 5},
    "Antagonist": {"acts": [2, 3], "max_per_scene": 1, "priority": 6}
}
```

#### Progressive Introduction
- **Opening Scenes (Act 1):** 1 NPC (Mentor/Guide)
- **Early Scenes (Act 1-2):** 2 NPCs (Companion/Ally)
- **Mid-Story (Act 2):** 2-3 NPCs (Rival/Antagonist)
- **Late Scenes (Act 3):** 2-3 NPCs (Group dynamics)

#### Narrative Hook Matching
The system checks if NPC narrative hooks match scene context:
- **Keywords:** secret, knowledge, ancient, mystery, danger, challenge, etc.
- **Scene Analysis:** Examines scene text and choice descriptions
- **Priority:** NPCs with matching hooks are prioritized for scene placement

## Usage

### Basic Integration
```python
from npc.scene_integration import assign_npcs_to_scenes

# Assign NPCs to story scenes
assignment_plan = await assign_npcs_to_scenes(
    player_id="player_123",
    player_name="Alex",
    player_archetype="Hero",
    story_theme="Epic Quest",
    story_dict=story_dict,
    num_npcs=3
)
```

### Scene-Specific NPC Retrieval
```python
from npc.scene_integration import get_scene_npcs

# Get NPCs for a specific scene
npc_ids = get_scene_npcs("player_123", "tag_001")
```

### Detailed NPC Context
```python
from npc.scene_integration import get_scene_npc_context

# Get detailed NPC information for a scene
context = get_scene_npc_context("player_123", "tag_001")
```

## Testing

### Unit Tests
- **Role Assignment:** Verify NPCs assigned to correct acts
- **Progressive Introduction:** Check NPC count increases appropriately
- **Narrative Hooks:** Test hook matching logic
- **Integration:** Test full workflow with story generation

### Test Scenarios
- **Hero Archetype:** Mentor → Rival → Group dynamics
- **Sage Archetype:** Apprentice → Sage → Multiple sages
- **Explorer Archetype:** Companion → Fellow explorer → Group adventure

## Benefits

1. **Personalized Stories:** Each player gets unique NPC placement
2. **Narrative Consistency:** NPCs appear in contextually appropriate scenes
3. **Progressive Engagement:** NPCs introduced gradually for better pacing
4. **Dynamic Interactions:** Multiple NPCs in later scenes create complex dynamics
5. **Maintainable Code:** Replaces hardcoded logic with flexible, testable system

## Future Enhancements

1. **Advanced NLP:** Use semantic analysis for better hook matching
2. **Relationship Dynamics:** Consider NPC-to-NPC relationships in placement
3. **Player Preferences:** Factor in player choices and preferences
4. **Scene Complexity:** Adjust NPC count based on scene complexity
5. **Memory Integration:** Consider past NPC interactions in placement

## Implementation Details

### Key Methods

#### `assign_npcs_to_scenes()`
- Generates NPCs using SPR-NPC06 system
- Creates assignment plan based on story structure
- Caches assignments for consistency

#### `_create_scene_assignment_plan()`
- Categorizes NPCs by role
- Determines act numbers for scenes
- Applies progressive introduction rules
- Selects NPCs based on narrative hooks

#### `_select_npcs_for_scene()`
- Prioritizes NPCs by role importance
- Matches narrative hooks to scene context
- Respects role limits per scene
- Returns optimal NPC selection

### Integration with Story Generation

The system integrates with `purpose_agents/generate_story.py` by:
1. Replacing hardcoded NPC assignments
2. Using dynamic NPC generation from SPR-NPC06
3. Applying intelligent placement rules
4. Ensuring NPC profiles exist for all assigned NPCs

### Scene Response Enhancement

The scene response logic in `backend/main.py` is enhanced to:
1. Use dynamic NPC assignments
2. Generate appropriate dialogue for present NPCs
3. Handle group dynamics with multiple NPCs
4. Maintain backward compatibility

## Error Handling

- **Fallback System:** Graceful degradation to existing logic if integration fails
- **NPC Profile Validation:** Ensures all assigned NPCs have corresponding profiles
- **Cache Management:** Handles missing or invalid cached assignments
- **Database Connection:** Proper session management and error recovery

## Performance Considerations

- **Caching:** NPC assignments cached per player to avoid regeneration
- **Efficient Queries:** Batch database operations where possible
- **Memory Management:** Proper cleanup of database sessions
- **Async Operations:** Non-blocking NPC generation and assignment

## Configuration

### Role Assignment Rules
Customizable rules for different story types and player archetypes:
```python
custom_rules = {
    "Mentor": {"acts": [1], "max_per_scene": 1, "priority": 1},
    "Rival": {"acts": [2, 3], "max_per_scene": 1, "priority": 5}
}
```

### Progressive Introduction Settings
Adjustable NPC counts per scene type:
```python
progressive_rules = {
    "opening": 1,      # Opening scenes
    "early": 2,        # Early/mid scenes  
    "late": 3          # Later scenes
}
```

### Narrative Hook Keywords
Extensible keyword list for hook matching:
```python
hook_keywords = [
    "secret", "knowledge", "ancient", "mystery",
    "danger", "challenge", "test", "choice"
]
```

## Troubleshooting

### Common Issues

1. **No NPCs Assigned:** Check if NPC generation is working
2. **Incorrect Placement:** Verify role assignment rules
3. **Missing Profiles:** Ensure NPC profiles exist in database
4. **Cache Issues:** Clear cache if assignments seem incorrect

### Debug Information

Enable debug logging to see:
- NPC generation process
- Assignment plan creation
- Scene selection logic
- Cache operations

### Testing Commands

```bash
# Run unit tests
pytest backend/tests/test_npc_scene_integration.py -v

# Test integration with story generation
python scripts/test_npc_api.py

# Verify NPC assignments
curl -X GET "http://localhost:8000/npc/list"
``` 