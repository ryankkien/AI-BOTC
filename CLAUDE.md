# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-BOTC is a Blood on the Clocktower (Trouble Brewing edition) simulation with LLM-powered AI agents. The system consists of a FastAPI backend running the game engine and AI agents, with a React frontend for real-time observation.

## Key Architecture

### Backend (Python/FastAPI)
- **Entry Point**: `backend/main.py` - FastAPI app with WebSocket support
- **Game Engine**: `backend/storyteller/grimoire.py` - Core game state management
- **AI Agents**: 
  - `backend/agents/storyteller_agent.py` - LLM-powered game master
  - `backend/agents/player_agent.py` - Individual AI players with memory management
- **LLM Integration**: `backend/llm_providers.py` - Unified interface for OpenAI, Anthropic, Google, and LiteLLM

### Frontend (React)
- **Entry Point**: `frontend/src/App.js`
- **Main Component**: `frontend/src/components/TownSquare.js` - Game visualization
- **Real-time Updates**: WebSocket via socket.io-client

## Common Development Commands

### Backend
```bash
# Setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/

# Run specific test
pytest tests/test_grimoire.py::TestGrimoire::test_initialization
```

### Frontend
```bash
# Setup
cd frontend
npm install

# Development server
npm start

# Run tests
npm test

# Build for production
npm build
```

## Environment Configuration

Create `backend/.env` from `.env.example`:
```
LLM_PROVIDER=openai  # or anthropic, google, litellm, auto
OPENAI_API_KEY=your_key_here
LLM_MIN_INTERVAL=1.0  # Rate limiting between API calls
```

## Game Flow Architecture

1. **WebSocket Communication**: Client sends `REQUEST_GAME_START` → GameManager → StorytellerAgent
2. **Turn Processing**: StorytellerAgent issues commands (LOG_EVENT, REQUEST_PLAYER_ACTION, etc.) → GameManager executes
3. **Player Actions**: GameManager prompts PlayerAgent → Agent responds with action → Back to Storyteller
4. **Memory Management**: PlayerAgent uses `_curate_memory()` with optional LLM filtering (controlled by settings)

## Key Implementation Details

### Storyteller Commands
- `LOG_EVENT`: Record game events
- `BROADCAST_MESSAGE`: Public announcements
- `SEND_PERSONAL_MESSAGE`: Private player information
- `REQUEST_PLAYER_ACTION`: Prompt player for night action/vote
- `AWAIT_PLAYER_RESPONSES`: Wait for player responses
- `END_GAME`: Declare winner

### Player Action Types
- Night actions: `CHOOSE_ONE`, `CHOOSE_TWO`, `PASS`
- Day actions: `PUBLIC_CHAT`, `PRIVATE_CHAT`, `SILENT`
- Voting: `NOMINATE`, `PASS_NOMINATION`, `VOTE_YES`, `VOTE_NO`

### Settings System
Access via http://localhost:8000 → Settings button
- `memory_curator_enabled`: Toggle LLM memory filtering
- `private_chat_enabled`: Allow private conversations
- `ai_chat_frequency`: Control AI talkativeness
- `auto_night_actions`: Automatic night phase processing

## Testing Strategy

### Backend Tests
- `test_grimoire.py`: Game state management
- `test_roles.py`: Role mechanics and abilities
- `test_rules.py`: Rule enforcement
- `test_main.py`: API endpoints and WebSocket

### Frontend Tests
Components have corresponding `.test.js` files testing rendering and interactions.

## Important Files to Know

- `backend/storyteller/roles.py`: All role definitions and abilities
- `backend/agents/base_agent.py`: Base class for all AI agents
- `frontend/src/components/EnhancedDebugPanel.js`: Debug UI for monitoring AI behavior
- `backend/utils/logger.py`: Comprehensive game logging (outputs to `logs/`)

## Recent Bug Fixes (2024-06-24)

The following critical issues have been resolved:

1. **First Night Hang**: Fixed phase transition from FIRST_NIGHT to DAY_CHAT
   - Enhanced Storyteller system prompt with specific first night handling
   - Fixed game loop to properly handle PASSIVE_OR_NO_ACTION responses
   - Added fallback grimoire initialization if Storyteller doesn't set up properly

2. **Missing Role Information**: AI players now receive meaningful first night clues
   - Information roles (Washerwoman, Chef, Empath) get specific clues
   - Evil roles (Imp, Poisoner) know team composition and bluffs
   - Clues are properly stored in agent memory and displayed in summaries

3. **Game Ending Issues**: Implemented proper victory condition checking
   - Added `check_victory_conditions()` method to GameManager
   - Automatic victory checking after executions
   - Manual CHECK_VICTORY command for Storyteller LLM

4. **AI Communication**: AIs now have concrete information to share during day phase
   - Enhanced memory summarization to include role clues
   - Better prompt context for meaningful discussions

## Common Development Tasks

### Adding a New Role
1. Define in `backend/storyteller/roles.py`
2. Add to `TROUBLE_BREWING_ROLES` list
3. Implement special mechanics in `StorytellerAgent._handle_night_action()`
4. Add tests in `test_roles.py`

### Modifying AI Behavior
1. PlayerAgent prompts: `backend/agents/player_agent.py` - `_build_prompt_context()`
2. Memory management: `_curate_memory()` method
3. Decision making: `decide_action()` and `decide_communication()`

### Debugging AI Decisions
1. Enable verbose logging in settings
2. Check `logs/comprehensive_game_log_*.json` for full game history
3. Use frontend debug panel to monitor real-time AI reasoning

### Troubleshooting Game Issues
1. Check that API keys are properly set in environment variables
2. Verify Storyteller LLM is responding correctly (check console logs)
3. If game hangs, check `pending_storyteller_actions` in debug info
4. Victory conditions: Good wins if Demon executed, Evil wins if ≤2 players or all Good dead

 # Using Gemini CLI for Large Codebase Analysis

  When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive
  context window. Use `gemini -p` to leverage Google Gemini's large context capacity.

  ## File and Directory Inclusion Syntax

  Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the
   gemini command:

  ### Examples:

  **Single file analysis:**
  ```bash
  gemini -p "@src/main.py Explain this file's purpose and structure"

  Multiple files:
  gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"

  Entire directory:
  gemini -p "@src/ Summarize the architecture of this codebase"

  Multiple directories:
  gemini -p "@src/ @tests/ Analyze test coverage for the source code"

  Current directory and subdirectories:
  gemini -p "@./ Give me an overview of this entire project"
  
#
 Or use --all_files flag:
  gemini --all_files -p "Analyze the project structure and dependencies"

  Implementation Verification Examples

  Check if a feature is implemented:
  gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"

  Verify authentication implementation:
  gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"

  Check for specific patterns:
  gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"

  Verify error handling:
  gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"

  Check for rate limiting:
  gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"

  Verify caching strategy:
  gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"

  Check for specific security measures:
  gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"

  Verify test coverage for features:
  gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"

  When to Use Gemini CLI

  Use gemini -p when:
  - Analyzing entire codebases or large directories
  - Comparing multiple large files
  - Need to understand project-wide patterns or architecture
  - Current context window is insufficient for the task
  - Working with files totaling more than 100KB
  - Verifying if specific features, patterns, or security measures are implemented
  - Checking for the presence of certain coding patterns across the entire codebase

  Important Notes

  - Paths in @ syntax are relative to your current working directory when invoking gemini
  - The CLI will include file contents directly in the context
  - No need for --yolo flag for read-only analysis
  - Gemini's context window can handle entire codebases that would overflow Claude's context
  - When checking implementations, be specific about what you're looking for to get accurate results # Using Gemini CLI for Large Codebase Analysis


  When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive
  context window. Use `gemini -p` to leverage Google Gemini's large context capacity.


  ## File and Directory Inclusion Syntax


  Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the
   gemini command:


  ### Examples:


  **Single file analysis:**
  ```bash
  gemini -p "@src/main.py Explain this file's purpose and structure"


  Multiple files:
  gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"


  Entire directory:
  gemini -p "@src/ Summarize the architecture of this codebase"


  Multiple directories:
  gemini -p "@src/ @tests/ Analyze test coverage for the source code"


  Current directory and subdirectories:
  gemini -p "@./ Give me an overview of this entire project"
  # Or use --all_files flag:
  gemini --all_files -p "Analyze the project structure and dependencies"


  Implementation Verification Examples


  Check if a feature is implemented:
  gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"


  Verify authentication implementation:
  gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"


  Check for specific patterns:
  gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"


  Verify error handling:
  gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"


  Check for rate limiting:
  gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"


  Verify caching strategy:
  gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"


  Check for specific security measures:
  gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"


  Verify test coverage for features:
  gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"


  When to Use Gemini CLI


  Use gemini -p when:
  - Analyzing entire codebases or large directories
  - Comparing multiple large files
  - Need to understand project-wide patterns or architecture
  - Current context window is insufficient for the task
  - Working with files totaling more than 100KB
  - Verifying if specific features, patterns, or security measures are implemented
  - Checking for the presence of certain coding patterns across the entire codebase


  Important Notes


  - Paths in @ syntax are relative to your current working directory when invoking gemini
  - The CLI will include file contents directly in the context
  - No need for --yolo flag for read-only analysis
  - Gemini's context window can handle entire codebases that would overflow Claude's context
  - When checking implementations, be specific about what you're looking for to get accurate results
  -Create and edit a GEMINI.md with instructios for geminizj