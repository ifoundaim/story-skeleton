# Consequence Toast System

## Overview

The "This Will Be Remembered" micro-feedback system provides real-time, tasteful feedback to players when their choices have consequences. This system leverages the Consequence Fabric to show on-screen ripples without spoilers.

## Features

### Real-time Feedback
- **WebSocket Events**: Backend emits real-time events when consequences occur
- **Toast Notifications**: Frontend displays subtle, animated toast notifications
- **Auto-dismiss**: Toasts automatically fade after 2.5 seconds
- **Manual Dismiss**: Users can manually dismiss toasts by clicking the X button

### Toast Variants
- **Promise Set** 🤝: When a promise is made to an NPC
- **Promise Fulfilled** ✅: When a promise is successfully completed
- **Promise Breached** ❌: When a promise is broken
- **Reputation Shift** ⭐: When NPC trust or reputation changes
- **Flag Set** 🚩: When story flags are set
- **Flag Cleared** 🧹: When story flags are cleared
- **Resource Change** 💎: When resources are gained or lost

### Accessibility
- **Reduced Motion**: Respects `prefers-reduced-motion` media query
- **Screen Reader Support**: Proper ARIA labels and live regions
- **Keyboard Navigation**: All interactive elements are keyboard accessible
- **High Contrast**: Color-coded toasts for different consequence types

### User Configuration
- **Enable/Disable**: Users can turn off consequence toasts entirely
- **Severity Filter**: Choose between "All consequences" or "Important only"
- **Settings Panel**: Accessible via the settings button (gear icon) in the bottom-left corner

## Technical Implementation

### Backend

#### WebSocket Manager (`backend/websocket_manager.py`)
```python
class WebSocketManager:
    async def emit_consequence_toast(
        self,
        kind: str,
        label: str,
        player_id: Optional[str] = None,
        delta: Optional[float] = None,
        npc_id: Optional[str] = None
    ):
        """Emit a consequence toast event."""
```

#### Beat DSL Integration (`backend/story/beat_dsl.py`)
The `apply_effects` function has been enhanced to emit WebSocket events when consequences occur:

```python
def apply_effects(beat: Dict[str, Any], state: StoryState, npc_list: List[str], player_id: Optional[str] = None) -> None:
    # ... existing effect application logic ...
    
    # Emit WebSocket events for each consequence type
    if WEBSOCKET_AVAILABLE:
        asyncio.create_task(websocket_manager.emit_consequence_toast(
            kind="promise_set",
            label=f"Promise made to {npc_name}",
            player_id=player_id,
            npc_id=npc_id
        ))
```

#### WebSocket Endpoint (`backend/main.py`)
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time consequence feedback."""
```

### Frontend

#### ConsequenceToaster Component (`frontend/src/components/ConsequenceToaster.tsx`)
- Renders toast notifications with animations
- Handles accessibility features
- Supports manual dismissal
- Color-coded by consequence type

#### useConsequenceToasts Hook (`frontend/src/hooks/useConsequenceToasts.ts`)
- Manages WebSocket connection
- Handles toast state and auto-dismissal
- Respects user settings
- Provides reconnection logic

#### Settings System (`frontend/src/contexts/SettingsContext.tsx`)
- Manages user preferences
- Persists settings in localStorage
- Provides settings panel UI

## Configuration

### Environment Variables
- `TOASTS_ENABLED=true` (default: true)
- `TOASTS_MIN_SEVERITY=info|important` (default: info)

### User Settings
- **Show consequence toasts**: Enable/disable the entire system
- **Minimum severity**: Filter between all consequences or important only
- **Reduced motion**: Minimize animations for accessibility

## Testing

### Frontend Tests
- `frontend/src/components/__tests__/ConsequenceToaster.test.tsx`
- `frontend/src/hooks/__tests__/useConsequenceToasts.test.ts`

### Backend Tests
- `backend/tests/test_consequence_toasts.py`

Run tests with:
```bash
# Frontend tests
cd frontend && npm test

# Backend tests
cd backend && python -m pytest tests/test_consequence_toasts.py -v
```

## Usage Examples

### Making a Promise
When a player makes a promise to an NPC, the system will:
1. Apply the promise to the story state
2. Emit a WebSocket event with type `promise_set`
3. Display a toast notification: "Promise made to Alice 🤝"

### Trust Changes
When NPC trust changes:
1. Update the NPC's trust value
2. Emit a WebSocket event with type `reputation_shift`
3. Display a toast: "Alice trust ↑ ⭐" with the delta value

### Flag Setting
When story flags are set:
1. Update the story state flags
2. Emit a WebSocket event with type `flag_set`
3. Display a toast: "Flag set: important_decision 🚩"

## Best Practices

### Toast Design
- Keep messages concise and clear
- Use appropriate icons for each consequence type
- Ensure good contrast ratios
- Respect user motion preferences

### Performance
- WebSocket connections are managed efficiently
- Toast animations are optimized for performance
- Auto-dismissal prevents memory leaks
- Reconnection logic handles network issues gracefully

### Accessibility
- All toasts have proper ARIA labels
- Screen readers announce new toasts
- Keyboard navigation is fully supported
- Reduced motion preferences are respected

## Troubleshooting

### WebSocket Connection Issues
- Check that the backend WebSocket endpoint is running
- Verify the WebSocket URL is correct
- Check browser console for connection errors
- Ensure no firewall is blocking WebSocket connections

### Toast Not Appearing
- Verify toasts are enabled in settings
- Check severity filter settings
- Ensure WebSocket connection is established
- Check browser console for JavaScript errors

### Performance Issues
- Reduce the number of concurrent toasts
- Check for memory leaks in long-running sessions
- Monitor WebSocket connection health
- Consider implementing toast queuing for high-frequency events
