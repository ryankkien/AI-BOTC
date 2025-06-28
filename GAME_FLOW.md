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
  {"command":"SEND_PERSONAL_MESSAGE","params":{"player_id":"AI_Player_2","message_type":"PRIVATE_NIGHT_INFO","payload":{"role":"Washerwoman","alignment":"Good","clues":{"message": "You are the Washerwoman. You see Player X or Player Y as the Townsfolk Z."}}}},
  {"command":"SEND_PERSONAL_MESSAGE","params":{"player_id":"AI_Player_3","message_type":"PRIVATE_NIGHT_INFO","payload":{"role":"Librarian","alignment":"Good","clues":[]}}}
]

During setup, the Storyteller LLM also performs initial logic for certain roles:
*   **Baron**: If present, two Outsider roles are added to the game's role pool before distribution.
*   **Drunk**: Assigned a false Townsfolk identity and corresponding misleading first night information.
*   **Recluse**: Assigned a pre-determined 'false persona' for investigative roles.
*   **Fortune Teller**: A Good, non-Demon player is selected as their 'red herring'.
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

## 3.5. Nightly Action Resolution Order & Specific Mechanics

The Storyteller LLM processes night actions in a defined order to ensure consistent interactions:
1.  **Protective & Altering Abilities**: (e.g., Monk's protection, Poisoner's poisoning). Poison applied at this stage will affect abilities in subsequent stages of the same night and the next day.
2.  **Killing Abilities**: (e.g., Demon's attack). This considers protections already applied.
3.  **Information Gathering Abilities**: (e.g., Empath, Fortune Teller). Results are determined based on the state of the game after the above stages, including any poisoning effects.

**Key Role Mechanic Handling by ST LLM (Examples):**
*   **Poisoner Malfunction**: If an Empath is poisoned, the ST LLM provides them with a false evil count (e.g., 0).
*   **Imp Promotion**: If the Imp kills themselves, the ST LLM follows a sequence: 1. Check Scarlet Woman promotion. 2. If not, check other Minions for promotion. 3. If none, Imp dies (Good likely wins).
*   **Virgin Ability**: If a Townsfolk nominates the Virgin (first time), ST LLM announces nominator's execution.
*   **Slayer Ability**: Player uses `USE_SLAYER_ABILITY: [TargetPlayerID]`. ST LLM checks target's true role; if Demon, target dies.
*   **Mayor's Save**: If Mayor targeted at night, 50% chance ST LLM makes another (non-attacker) player die instead, informing Mayor.
*   **Recluse Misregistration**: Investigative roles receive info based on Recluse's 'false persona'; Undertaker/Ravenkeeper learn true role.

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
// Or
[{"command":"END_GAME","params":{"winner":"Evil","reason":"Saint executed"}}]
// Or
[{"command":"END_GAME","params":{"winner":"Good","reason":"Mayor wins: 3 players alive and no execution."}}]
```

---

## Summary of Prompt Structure

- **StorytellerAgent** uses a fixed system prompt (full rulebook + available commands) and appends a small **CURRENT CONTEXT** for each turn.
- **PlayerAgent** builds a persona + public state + memory + chat log, injects an **`available_actions`** list, then adds a **Specific Task Context** (night action / chat / nomination / vote).

This ensures both LLMs "know" the rules, their abilities, and their exact legal moves at every step. 
