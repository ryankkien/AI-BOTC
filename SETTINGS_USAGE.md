# Game Settings UI and Memory Curator Feature

## Overview

The backend server now includes a settings UI popup that allows you to configure various game settings, including a memory curator toggle that controls how AI players manage their memories.

## How to Access Settings

1. Start the backend server: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
2. Open http://localhost:8000 in your browser
3. Click the "⚙️ Settings" button in the connection bar

## Settings Available

### AI Behavior Settings

#### Memory Curator
- **When enabled**: AI players use LLM to filter and curate important memories, keeping only strategically relevant events
- **When disabled**: AI players remember everything they've said and heard, storing all events as important memories
- **Impact**: Disabling the curator can lead to more comprehensive but potentially overwhelming memory for AI players

#### Private Chat
- **When enabled**: AI players can have private conversations during night phases
- **When disabled**: AI players only participate in public chat

#### AI Chat Frequency
- **Low**: AI players chat less frequently during day phases
- **Normal**: Standard chat frequency (default)
- **High**: AI players are more talkative

### Game Flow Settings

#### Auto Night Actions
- **When enabled**: Night actions are processed automatically without manual storyteller intervention
- **When disabled**: Requires manual storyteller oversight for night actions

#### Verbose Logging
- **When enabled**: Detailed logging for debugging and analysis
- **When disabled**: Minimal logging output

## Memory Curator Implementation Details

The memory curator feature is implemented in the `PlayerAgent` class:

```python
async def _curate_memory(self, event_type: str, data: Any):
    # Check if memory curator is enabled in settings
    if self.game_settings and not self.game_settings.memory_curator_enabled:
        # If memory curator is disabled, store everything as important
        self.memory.setdefault("important_events", []).append({"type": event_type, "data": data})
        return
    
    # Use LLM to decide if an event is worth remembering long-term
    # ... (LLM-based curation logic)
```

When the memory curator is disabled:
- All events (chat messages, votes, nominations, etc.) are stored directly in the agent's `important_events` memory
- No LLM filtering occurs, ensuring complete information retention
- This can be useful for testing, debugging, or when you want AI players to have perfect recall

## API Endpoints

### REST API
- `GET /settings` - Get current settings
- `POST /settings` - Update settings (send JSON with setting keys and values)

### WebSocket Messages
- `REQUEST_SETTINGS` - Request current settings from server
- `UPDATE_SETTINGS` - Update settings via WebSocket (with payload containing new settings)
- `SETTINGS_UPDATE` - Server response with current settings

## Example Usage

To disable memory curator via REST API:
```bash
curl -X POST http://localhost:8000/settings \
  -H "Content-Type: application/json" \
  -d '{"memory_curator_enabled": false}'
```

To get current settings:
```bash
curl http://localhost:8000/settings
```

## Technical Notes

- Settings are applied immediately to existing AI agents when updated
- The settings popup UI provides real-time updates via WebSocket
- All settings persist for the duration of the server session
- The memory curator setting affects how the `_curate_memory` method behaves in PlayerAgent 