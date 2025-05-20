# Blood on the Clocktower AI Game Flow

A step-by-step walkthrough of how the FastAPI-based engine, the Storyteller LLM, and the Player LLMs interact to simulate a full game.

---

## 1. Game Setup

**Client Request**
```json
{ "type": "REQUEST_GAME_START" }
```

1. `GameManager.handle_incoming_message` receives the request and calls `setup_new_game(...)`.

### Storyteller LLM System Prompt (trimmed)
```text
you are the storyteller for a blood on the clocktower session. you know every player's secret role and seating order.
your role is to interpret game events, enforce rules, and narrate the game.
... (available commands: LOG_EVENT, BROADCAST_MESSAGE, SEND_PERSONAL_MESSAGE, REQUEST_PLAYER_ACTION, AWAIT_PLAYER_RESPONSES, END_GAME)
```

### Storyteller LLM Context
```text
CURRENT CONTEXT:
EVENT: REQUEST_GAME_START received.
INPUT_PLAYER_ROLES: {"AI_Player_1":"Imp","AI_Player_2":"Washerwoman","AI_Player_3":"Librarian"}
INPUT_HUMAN_PLAYERS: []
GRIMOIRE_STATE: EMPTY_INITIALIZATION
```

### Example ST LLM Response (JSON commands)
```json
[
  {"command":"LOG_EVENT","params":{"event_type":"GAME_SETUP","data":{"event":"seating order established","order":["AI_Player_2","AI_Player_1","AI_Player_3"]}}},
  {"command":"LOG_EVENT","params":{"event_type":"PHASE_CHANGE","data":{"new_phase":"FIRST_NIGHT","day_number":0}}},
  {"command":"SEND_PERSONAL_MESSAGE","params":{"player_id":"AI_Player_1","message_type":"PRIVATE_NIGHT_INFO","payload":{"role":"Imp","alignment":"Evil","clues":[]}}},
  {"command":"SEND_PERSONAL_MESSAGE","params":{"player_id":"AI_Player_2","message_type":"PRIVATE_NIGHT_INFO","payload":{"role":"Washerwoman","alignment":"Good","clues":[]}}},
  {"command":"SEND_PERSONAL_MESSAGE","params":{"player_id":"AI_Player_3","message_type":"PRIVATE_NIGHT_INFO","payload":{"role":"Librarian","alignment":"Good","clues":[]}}}
]
```

---

## 2. First Night Actions

1. `run_game_loop` sees `current_phase == "FIRST_NIGHT"`.
2. ST LLM prompt includes:
   ```text
   CURRENT CONTEXT:
   EVENT: Start of game loop iteration 1.
   GRIMOIRE_PHASE: FIRST_NIGHT
   GRIMOIRE_DAY: 0
   ...
   ```
3. Example ST LLM commands:
   ```json
   [
     {"command":"REQUEST_PLAYER_ACTION","params":{"action_id":"night1_AI_Player_1","player_id":"AI_Player_1","action_type":"NIGHT_ACTION_Imp","action_details":{}}},
     {"command":"REQUEST_PLAYER_ACTION","params":{"action_id":"night1_AI_Player_2","player_id":"AI_Player_2","action_type":"NIGHT_ACTION_Washerwoman","action_details":{}}},
     {"command":"AWAIT_PLAYER_RESPONSES","params":{"action_id":"night1_AI_Player_1","expected_players":["AI_Player_1"]}},
     {"command":"AWAIT_PLAYER_RESPONSES","params":{"action_id":"night1_AI_Player_2","expected_players":["AI_Player_2"]}}
   ]
   ```

---

## 3. Player Night-Action Prompt

`GameManager._get_ai_player_action` builds a per-agent context:
- Public state (phase, day, players)
- `available_actions`: `["CHOOSE_ONE","CHOOSE_TWO","PASS"]`
- `daily_chat_log` & `all_players_details`

**Full Prompt for `Imp`**:  
```text
you are playing blood on the clocktower. your player id is AI_Player_1.
your assigned role is: Imp.
your alignment is: Evil.

current game state:
  day: 0
  phase: FIRST_NIGHT
  players alive: 3/3
  alive players by name: AI Player 1, AI Player 2, AI Player 3
  your current status: {'alive': True, …}

memory summary:
Known facts and observations:
  (none)

full chat history:
  (none)

available actions:
  CHOOSE_ONE, CHOOSE_TWO, PASS

specific task context:
It is FIRST_NIGHT. Review your role …
If you need to choose one player, respond with: CHOOSE_ONE: [PlayerID]
…
```

**Example Player LLM Response**:
```text
CHOOSE_ONE: [AI_Player_2]
```

---

## 4. Day 1 Discussion, Nomination & Voting

1. After night resolution, ST LLM issues `PHASE_CHANGE → DAY_CHAT`.
2. **AI Chat Round** via `decide_communication`, with `_build_prompt_context` plus:
   ```text
   it is the day phase. you need to decide on your communication strategy now.
   options:
   1. PUBLIC_CHAT: [message]
   2. PRIVATE_CHAT: [to ID]
   3. SILENT
   …
   ```
3. ST LLM later requests:
   ```json
   [
     {"command":"REQUEST_PLAYER_ACTION","params":{"action_id":"nom1_AI_Player_3","player_id":"AI_Player_3","action_type":"NOMINATION_CHOICE","action_details":{}}},
     {"command":"AWAIT_PLAYER_RESPONSES","params":{"action_id":"nom1_AI_Player_3","expected_players":["AI_Player_3"]}}
   ]
   ```
4. **Nomination Prompt** includes `available_actions = ["NOMINATE","PASS_NOMINATION"]` and instructs:
   ```text
   it is your turn to nominate …
   format: NOMINATE: [PlayerID]
   ```
5. **Voting Prompt** includes `available_actions = ["VOTE_YES","VOTE_NO"]` and instructs:
   ```text
   player AI_Player_3(ID:…) has been nominated. format: VOTE: [YES/NO]
   ```

---

## 5. Game End

Eventually ST LLM returns:
```json
[{"command":"END_GAME","params":{"winner":"Good","reason":"Demon executed"}}]
```

---

## Summary of Prompt Structure

- **StorytellerAgent** uses a fixed system prompt (full rulebook + available commands) and appends a small **CURRENT CONTEXT** for each turn.
- **PlayerAgent** builds a persona + public state + memory + chat log, injects an **`available_actions`** list, then adds a **Specific Task Context** (night action / chat / nomination / vote).

This ensures both LLMs "know" the rules, their abilities, and their exact legal moves at every step. 