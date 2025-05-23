# Enhanced Bot Debugging Features

This document describes the comprehensive debugging system implemented for the Blood on the Clocktower AI bot game.

## Overview

The debugging system provides multiple interfaces to monitor, analyze, and understand bot behavior in real-time. It includes detailed thought tracking, memory inspection, performance metrics, and comprehensive game state monitoring.

## Debugging Components

### 1. Enhanced Debug Panel
**Access**: Click "View Enhanced Debug" button in the side panel

**Features**:
- **Bot Selection**: Choose any bot (Storyteller or Player) from the sidebar
- **Categorized Views**: 
  - **Thoughts**: Real-time prompts and responses with timestamps
  - **Memory**: Complete bot memory and knowledge state
  - **Stats**: Performance metrics and activity statistics
- **Search & Filter**: Search through bot thoughts and responses
- **Timestamps**: Detailed timing information for all bot activities
- **Provider Information**: Shows which LLM provider generated each response
- **Performance Metrics**: Generation time, content length, and correlation hashes

### 2. Debug Dashboard
**Access**: Click "View Debug Dashboard" button in the side panel

**Features**:
- **Overview Tab**: 
  - System status summary
  - Bot activity grid showing all bots at once
  - Recent game activity timeline
- **Bot Details Tab**:
  - Deep dive into individual bot information
  - Complete memory dumps
  - Recent thought history
  - Detailed statistics
- **System Logs Tab**:
  - Raw game state information
  - Player data structures
  - Debug data summaries
- **Auto-refresh**: Automatically updates every 5 seconds
- **Manual Refresh**: Force refresh button for immediate updates

### 3. Legacy Debug Panels
**Access**: Individual bot debug panels (maintained for compatibility)

**Features**:
- Simple prompt/response viewing
- Basic bot selection
- Minimal interface for quick debugging

## Debug Data Structure

### Enhanced LLM Debug Messages
Each debug message now includes:
```json
{
  "agent": "bot_id",
  "type": "prompt|response|error",
  "content": "actual_content",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "provider": "OpenAIProvider",
  "prompt_length": 1234,
  "response_length": 567,
  "generation_time_seconds": 2.34,
  "prompt_hash": 1234
}
```

### Bot Information API
**Endpoint**: `GET /debug/bot_info`

Provides comprehensive bot information including:
- Memory states
- Statistics
- Recent activities
- Role and alignment information
- Performance metrics

## Usage Guide

### Monitoring Bot Thoughts
1. Open the Enhanced Debug Panel or Debug Dashboard
2. Select the bot you want to monitor
3. Navigate to the "Thoughts" or "Bot Details" section
4. Use search filters to find specific content
5. Enable timestamps to see timing information

### Analyzing Bot Performance
1. Use the Debug Dashboard's Overview tab
2. Check the Bot Activity Summary for quick metrics
3. Look at generation times and response lengths
4. Monitor the Recent Activity timeline for game events

### Debugging Bot Memory
1. Select a bot in the Enhanced Debug Panel
2. Go to the "Memory" tab
3. Inspect the complete memory structure
4. Look for private information, clues, and observations
5. Check important events and action history

### Troubleshooting
1. Use the System Logs tab in the Debug Dashboard
2. Check for error messages in bot thoughts
3. Monitor generation times for performance issues
4. Verify bot status and game state consistency

## Technical Implementation

### Backend Enhancements
- **Enhanced LLM Logging**: Timestamps, performance metrics, and structured data
- **Debug API Endpoint**: Comprehensive bot information retrieval
- **Error Tracking**: Detailed error logging with context

### Frontend Components
- **EnhancedDebugPanel**: Advanced single-bot debugging interface
- **DebugDashboard**: Comprehensive multi-bot monitoring system
- **Real-time Updates**: WebSocket integration for live debugging
- **Responsive Design**: Optimized for different screen sizes

### Data Flow
1. LLM providers generate enhanced debug messages
2. Backend broadcasts debug data via WebSocket
3. Frontend components receive and structure the data
4. Multiple visualization interfaces present the information
5. API endpoints provide additional detailed information

## Best Practices

### For Development
- Use the Debug Dashboard for overall system monitoring
- Use Enhanced Debug Panel for detailed bot analysis
- Enable auto-refresh during active development
- Monitor generation times to optimize performance

### For Game Analysis
- Track bot decision-making patterns in the Thoughts view
- Analyze memory evolution over game phases
- Compare bot performance metrics
- Use search filters to find specific game events

### For Troubleshooting
- Check System Logs for data structure issues
- Monitor error messages in bot thoughts
- Verify timestamp consistency across components
- Use manual refresh to ensure data freshness

## Future Enhancements

Planned improvements include:
- Historical data persistence
- Advanced filtering and search capabilities
- Performance trend analysis
- Bot behavior pattern recognition
- Export functionality for analysis
- Real-time alerts for anomalies

## Configuration

### Auto-refresh Settings
- Default: 5 seconds
- Configurable in Debug Dashboard
- Can be disabled for manual control

### Display Options
- Timestamp visibility toggle
- Search filter persistence
- Bot selection memory
- View preference saving

This debugging system provides unprecedented visibility into bot behavior and game state, enabling effective development, testing, and analysis of the AI Blood on the Clocktower implementation. 