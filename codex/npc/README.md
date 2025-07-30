# Context-Aware NPC Dialogue (SPR-NPC02)

This module implements dynamic NPC dialogue generation based on player trust, emotional state, and memory context.

## Overview

The NPC dialogue system generates contextual responses that reflect:
- **Trust Score**: How much the NPC trusts the player (0.0 - 1.0)
- **Emotional State**: The player's current emotional vector (8 dimensions)
- **Memory Context**: Recent narrative memory recap

## Architecture

### Core Components

1. **`npc_dialogue.py`**: Main dialogue generation engine
2. **Template System**: Pre-defined dialogue templates for different trust/emotion combinations
3. **Context Loading**: Functions to load trust, emotion, and memory data
4. **Template Selection**: Logic to choose appropriate dialogue based on context

### Data Sources

- **Trust Data**: From NPC state database (currently defaults to 0.5)
- **Emotion Data**: From `backend/emotion_state.json`
- **Memory Data**: From `codex/memory/memory_state.json`

## Usage

### Basic Dialogue Generation

```python
from codex.npc import generate_npc_dialogue

# Generate dialogue for a specific NPC and player
dialogue = generate_npc_dialogue("companion-001", "player-123")
print(dialogue)  # "I'm learning to trust you. Show me what you're capable of."
```

### Advanced Usage with Context

```python
from codex.npc import generate_npc_dialogue_with_context

# Generate dialogue with additional scene context
dialogue = generate_npc_dialogue_with_context(
    npc_id="companion-001",
    player_id="player-123",
    scene_context="The player is facing a difficult choice..."
)
```

## Trust Categories

- **High Trust** (≥0.7): Supportive, encouraging dialogue
- **Medium Trust** (0.3-0.7): Cautious, observational dialogue  
- **Low Trust** (<0.3): Distrustful, challenging dialogue

## Emotion Integration

The system recognizes 8 emotional dimensions:
- joy, grief, awe, fear, desire, disgust, peace, rage

Emotions are categorized as:
- **Positive**: joy, awe, peace (when intensity > 0)
- **Negative**: fear, grief, rage (when intensity < 0)
- **Neutral**: When no emotion exceeds 0.3 threshold

## Dialogue Templates

### High Trust Templates
- `high_trust_joy`: "Your courage inspires me! Let's face this together."
- `high_trust_awe`: "The wonder in your eyes... it reminds me why we're here."
- `high_trust_peace`: "Your calm presence soothes my worries."
- `high_trust_fear`: "I'm here with you. We'll face this fear together."
- `high_trust_grief`: "I feel your pain. Let me help carry this burden."

### Medium Trust Templates
- `medium_trust_neutral`: "I'm learning to trust you. Show me what you're capable of."
- `medium_trust_positive`: "You're growing on me. Keep making good choices."

### Low Trust Templates
- `low_trust_neutral`: "I'm watching you closely. Don't give me reason to doubt."
- `low_trust_negative`: "Your actions concern me. I need to see better from you."

### Fallback Templates
- `fallback_positive`: "I'm here with you on this journey."
- `fallback_neutral`: "I'm observing your choices."
- `fallback_negative`: "I'm watching how you handle this."

## Integration Points

### Backend Integration

The system integrates with the FastAPI backend through:

1. **SceneResponse Model**: Extended to include `npc_text_dynamic` field
2. **Scene Generation**: Dynamic dialogue is generated in `_scene_to_response()`
3. **Error Handling**: Graceful fallback when data is missing

### Frontend Integration

The React frontend displays dynamic dialogue through:

1. **Dialogue Component**: Extended to show `npcTextDynamic` prop
2. **Visual Styling**: Blue-themed styling with fade-in animation
3. **Fallback Display**: Shows static NPC text when dynamic text is unavailable

## Constraints & Limitations

- **Character Limit**: Maximum 150 characters per dialogue line
- **Template-Based**: Currently uses pre-written templates (no LLM generation)
- **Default Trust**: Falls back to 0.5 trust when NPC data is missing
- **Single NPC**: Currently supports one companion NPC per scene

## Testing

Run the test suite:

```bash
python -m pytest tests/test_npc_dialogue.py -v
```

Run the demo script:

```bash
python test_npc_dialogue_demo.py
```

## Future Enhancements

1. **LLM Integration**: Replace templates with AI-generated dialogue
2. **Multiple NPCs**: Support for scene-specific NPCs
3. **Memory Integration**: Use memory recap for more contextual responses
4. **Emotion History**: Consider emotional trajectory over time
5. **Scene Context**: Incorporate current scene description into dialogue

## API Reference

### `generate_npc_dialogue(npc_id: str, player_id: str) -> str`

Generate dynamic NPC dialogue based on trust and emotion context.

**Parameters:**
- `npc_id`: The NPC identifier
- `player_id`: The player identifier

**Returns:**
- Generated dialogue string (max 150 characters)

### `get_trust_category(trust: float) -> str`

Categorize trust level into high/medium/low.

### `get_dominant_emotion(emotion_vector: List[float]) -> Tuple[str, float]`

Extract the dominant emotion and its intensity from the emotion vector.

### `select_dialogue_template(trust_category: str, emotion_name: str, emotion_intensity: float) -> str`

Select appropriate dialogue template based on trust and emotion combination. 