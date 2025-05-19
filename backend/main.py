#backend/main.py
import asyncio
import uvicorn
import json #for parsing and sending structured data
import os #for environment variables
import random #for shuffling roles if needed
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse #for testing
from typing import Dict, List, Any, Optional

from .storyteller.grimoire import Grimoire
from .storyteller.rules import RuleEnforcer
from .storyteller.roles import ROLES_DATA, RoleAlignment, RoleType, get_role_details #import all necessary items
from .agents.player_agent import PlayerAgent
from .agents.base_agent import BaseAgent #if we need to type hint with base class
from .agents.storyteller_agent import StorytellerAgent

#temp html for testing - can be removed later or served from frontend proper
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>BotC AI Observer</title>
        <style>
            body { font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; margin: 0; }
            .container { display: flex; flex: 1; overflow: hidden; }
            .main-content { flex: 3; display: flex; flex-direction: column; padding: 10px; overflow-y: auto; border-right: 1px solid #ccc; }
            .sidebar { flex: 1; padding: 10px; overflow-y: auto; border-left: 1px solid #ccc; display: flex; flex-direction: column;}
            #messages, #storytellerLog { list-style-type: none; padding: 0; margin-bottom: 20px; flex-grow: 1; overflow-y: auto; border: 1px solid #eee; padding: 5px;}
            #playerRoles { list-style-type: none; padding: 0; }
            .message-item, .log-item, .role-item { margin-bottom: 5px; padding: 8px; border-radius: 4px; }
            .chat-message { background-color: #e1f5fe; }
            .game-event { background-color: #fff9c4; }
            .error-message { background-color: #ffcdd2; color: #c62828; }
            .info-message { background-color: #c8e6c9; }
            .storyteller-message { background-color: #d1c4e9; } /* Storyteller messages color */
            .connection-bar { padding: 10px; background-color: #f0f0f0; border-bottom: 1px solid #ccc; }
            h1, h2, h3 { margin-top: 0; }
        </style>
    </head>
    <body>
        <div class="connection-bar">
            Player ID (Observer): <input type="text" id="observerId" value="ObserverClient"/>
            <button onclick="connectWs()">Connect</button>
            <button onclick="requestGameStart()">Start 10-AI Player Game</button>
        </div>
        <div class="container">
            <div class="main-content">
                <h2>Storyteller Log & Game Events</h2>
                <ul id="storytellerLog"></ul>
                <h2>AI Player Chat</h2>
                <ul id="messages"></ul>
            </div>
            <div class="sidebar">
                <h2>Player Roles</h2>
                <ul id="playerRoles"></ul>
            </div>
        </div>

        <script>
            var ws = null;
            const storytellerLog = document.getElementById('storytellerLog');
            const messagesList = document.getElementById('messages');
            const playerRolesList = document.getElementById('playerRoles');

            function addMessageToList(listElement, text, type) {
                var item = document.createElement('li');
                item.className = 'message-item ' + type;
                item.textContent = text;
                listElement.appendChild(item);
                listElement.scrollTop = listElement.scrollHeight; // Scroll to bottom
            }

            function connectWs() {
                var observerId = document.getElementById("observerId").value;
                if (!observerId) { alert("Observer ID cannot be empty!"); return; }
                if (ws) { ws.close(); }
                ws = new WebSocket(`ws://localhost:8000/ws/${observerId}`);
                
                storytellerLog.innerHTML = '';
                messagesList.innerHTML = '';
                playerRolesList.innerHTML = '';

                ws.onopen = function(event) {
                    addMessageToList(storytellerLog, "Connected to server as " + observerId, "info-message");
                };

                ws.onmessage = function(event) {
                    var data;
                    try {
                        data = JSON.parse(event.data);
                    } catch (e) {
                        addMessageToList(storytellerLog, "Raw non-JSON message: " + event.data, "error-message");
                        return;
                    }

                    const messageType = data.type;
                    const payload = data.payload;
                    let displayText = "";

                    if (payload && typeof payload === 'object') {
                        displayText = JSON.stringify(payload, null, 2);
                    } else if (payload) {
                        displayText = payload;
                    }

                    switch (messageType) {
                        case "INFO":
                            addMessageToList(storytellerLog, `INFO: ${displayText}`, "info-message");
                            break;
                        case "ERROR":
                            addMessageToList(storytellerLog, `ERROR: ${displayText}`, "error-message");
                            break;
                        case "GAME_STATE_UPDATE":
                            let reason = payload.reason || "Game State Update";
                            let phase = payload.currentPhase || "Unknown";
                            let day = payload.dayNumber || "N/A";
                            addMessageToList(storytellerLog, `STORYTELLER [${reason}]: Phase: ${phase}, Day: ${day}`, "storyteller-message");
                            // Optionally display full game state if needed for debugging
                            // addMessageToList(storytellerLog, JSON.stringify(payload, null, 2), "game-event");
                            break;
                        case "CHAT_MESSAGE":
                            const senderName = payload.sender_name || payload.sender;
                            addMessageToList(messagesList, `${senderName}: ${payload.text}`, "chat-message");
                            break;
                        case "PLAYER_ROLES_UPDATE": // New message type for roles
                            playerRolesList.innerHTML = ''; // Clear previous roles
                            if (payload.roles && Array.isArray(payload.roles)) {
                                payload.roles.forEach(player => {
                                    addMessageToList(playerRolesList, `${player.name} (${player.id.substring(0,4)}): ${player.role}`, "role-item");
                                });
                            }
                            break;
                        case "GAME_EVENT": // Generic game event from storyteller
                             addMessageToList(storytellerLog, `STORYTELLER: ${payload.message}`, "storyteller-message");
                             break;
                        default:
                            addMessageToList(storytellerLog, `UNKNOWN [${messageType}]: ${displayText}`, "game-event");
                    }
                };

                ws.onclose = function(event) {
                    addMessageToList(storytellerLog, "Disconnected. Reason: " + event.reason + " Code: " + event.code, "error-message");
                    ws = null;
                };
                ws.onerror = function(event) {
                    addMessageToList(storytellerLog, "WebSocket Error: " + JSON.stringify(event), "error-message");
                };
            }

            function requestGameStart() {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    alert("Connect to server first!");
                    return;
                }
                ws.send(JSON.stringify({ type: "REQUEST_GAME_START" }));
                addMessageToList(storytellerLog, "Requested 10-AI player game start.", "info-message");
            }
            
            // Removed sendMessage function as observer does not send chat.
            // If you need to send other specific commands for testing, add new functions like requestGameStart.
        </script>
    </body>
</html>
"""

app = FastAPI()

class GameManager:
    def __init__(self):
        self.grimoire: Optional[Grimoire] = None
        self.rule_enforcer: Optional[RuleEnforcer] = None
        self.agents: Dict[str, BaseAgent] = {}
        self.active_connections: Dict[str, WebSocket] = {} #player_id to websocket
        self.game_loop_task: Optional[asyncio.Task] = None
        self.google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        self.human_player_expected_actions: Dict[str, asyncio.Future] = {} # player_id -> Future for action
        self._game_lock = asyncio.Lock() #to prevent concurrent modifications to game state
        self._game_started_event = asyncio.Event()
        self._current_nominating_player_index: int = 0
        self._nomination_order: List[str] = []
        self._daily_chat_log: List[Dict[str,str]] = [] #to feed to agents for day decisions
        # initialize LLM-based storyteller
        self.storyteller_agent = StorytellerAgent(api_key=self.google_api_key)

    def is_game_running(self) -> bool:
        return self.grimoire is not None and self.rule_enforcer is not None and not self._game_started_event.is_set() #game is running if setup and loop started

    async def execute_storyteller_command(self, command_obj: Dict[str, Any]):
        command_type = command_obj.get("command")
        params = command_obj.get("params", {})

        if not command_type:
            print(f"Storyteller Command Error: Missing 'command' field in {command_obj}")
            return

        print(f"GameManager executing Storyteller command: {command_type} with params: {params}")

        if command_type == "LOG_EVENT":
            if self.grimoire and "event_type" in params and "data" in params:
                self.grimoire.log_event(params["event_type"], params["data"])
            else:
                print(f"LOG_EVENT Error: Missing grimoire, event_type, or data in params: {params}")

        elif command_type == "BROADCAST_MESSAGE":
            if "message_type" in params and "payload" in params:
                await self.broadcast_message(params["message_type"], params["payload"])
            else:
                print(f"BROADCAST_MESSAGE Error: Missing message_type or payload in params: {params}")

        elif command_type == "SEND_PERSONAL_MESSAGE":
            if "player_id" in params and "message_type" in params and "payload" in params:
                await self.send_personal_message(params["player_id"], params["message_type"], params["payload"])
            else:
                print(f"SEND_PERSONAL_MESSAGE Error: Missing player_id, message_type, or payload: {params}")

        elif command_type == "UPDATE_PLAYER_STATUS":
            if self.grimoire and "player_id" in params and "status_key" in params and "value" in params:
                self.grimoire.update_status(params["player_id"], params["status_key"], params["value"])
            else:
                print(f"UPDATE_PLAYER_STATUS Error: Missing grimoire or params: {params}")

        elif command_type == "UPDATE_GRIMOIRE_VALUE":
            # This is a bit more complex as it involves nested updates. 
            # For now, let's assume simple top-level key updates or direct attribute setting.
            # A more robust solution would handle nested paths like ['game_state', 'demon_bluffs']
            if self.grimoire and "key_path" in params and "value" in params:
                key_path = params["key_path"]
                value = params["value"]
                if len(key_path) == 1: #e.g., grimoire.current_phase = "value"
                    setattr(self.grimoire, key_path[0], value)
                    print(f"Set grimoire.{key_path[0]} = {value}")
                elif len(key_path) > 1: #e.g. grimoire.game_state["some_key"] = value
                    obj = self.grimoire
                    for key_segment in key_path[:-1]:
                        if hasattr(obj, key_segment):
                            obj = getattr(obj, key_segment)
                        elif isinstance(obj, dict) and key_segment in obj:
                            obj = obj[key_segment]
                        else:
                            print(f"UPDATE_GRIMOIRE_VALUE Error: Invalid path {key_path}")
                            return
                    if hasattr(obj, key_path[-1]): # Set as attribute if possible
                         setattr(obj, key_path[-1], value)
                    elif isinstance(obj, dict): # Set as dict key if it's a dict
                        obj[key_path[-1]] = value
                    else:
                        print(f"UPDATE_GRIMOIRE_VALUE Error: Cannot set value at path {key_path}")
                    print(f"Set grimoire path {key_path} = {value}")
            else:
                print(f"UPDATE_GRIMOIRE_VALUE Error: Missing grimoire or params: {params}")

        elif command_type == "EXECUTE_PLAYER":
            if self.rule_enforcer and "player_id" in params and "reason" in params:
                # The RuleEnforcer._execute_player method already handles logging and status updates.
                self.rule_enforcer._execute_player(params["player_id"], params["reason"])
                # Potentially broadcast this event here if not handled by LLM's next commands
                await self.broadcast_game_event(f"Player {self.grimoire.game_state.get('player_names',{}).get(params['player_id'], params['player_id'])} has died due to: {params['reason']}")
            else:
                print(f"EXECUTE_PLAYER Error: Missing rule_enforcer or params: {params}")
        
        elif command_type == "REQUEST_PLAYER_ACTION":
            # This is complex: needs to store that an action is expected, and how to resume.
            # For now, just log it. The game loop will need to handle this state.
            player_id = params.get("player_id")
            action_type = params.get("action_type")
            print(f"STORYTELLER REQUESTS ACTION: Player {player_id} to perform {action_type} with details {params.get('action_details')}")
            # This would typically involve setting up a future in self.human_player_expected_actions or a similar mechanism for AI agents
            # and then the game loop would pause or await these actions before feeding results back to StorytellerLLM.
            # For example, for night actions:
            if player_id and action_type == "NIGHT_ACTION" and player_id in self.agents:
                 # This is a conceptual link; _collect_ai_night_actions would need to be callable for a single agent
                 # or this command triggers a flag that _collect_ai_night_actions respects.
                 print(f"GameManager needs to prompt AI {player_id} for their night action based on ST LLM request.")
                 # We can send a specific message to the player to trigger their UI or AI logic if they are human/external.
                 await self.send_personal_message(player_id, "REQUEST_NIGHT_ACTION", params.get("action_details", {}))
            elif player_id and action_type == "VOTE" and player_id in self.agents:
                 await self.send_personal_message(player_id, "REQUEST_VOTE", params.get("action_details", {}))
                 print(f"GameManager needs to prompt AI {player_id} for their vote based on ST LLM request.")

        elif command_type == "AWAIT_PLAYER_RESPONSES":
            # This command implies the GameManager should now pause its loop feeding commands to the ST LLM,
            # and wait until all players listed in expected_players have submitted their actions for action_id.
            # The game loop logic will need to be adapted to handle this pausing and resuming.
            print(f"STORYTELLER AWAITING RESPONSES for action_id {params.get('action_id')} from {params.get('expected_players')}")
            # Set a flag or state in GameManager that the main loop will check.
            # self.waiting_for_actions = params # Or some more structured state object

        elif command_type == "END_GAME":
            if "winner" in params and "reason" in params:
                print(f"Game Over! Winner: {params['winner']}, Reason: {params['reason']}")
                await self.broadcast_message("GAME_END", {"winner" : params['winner'], "reason": params['reason']})
                if self.grimoire: # Clear grimoire to stop game loop
                    self.grimoire = None 
                self._game_started_event.clear()
                if self.game_loop_task and not self.game_loop_task.done():
                    self.game_loop_task.cancel() # Stop the game loop task
            else:
                print(f"END_GAME Error: Missing winner or reason: {params}")

        elif command_type == "ERROR_LOG":
            print(f"Storyteller LLM Reported Error: {params.get('message')}. Raw Output: {params.get('raw_output', 'N/A')}")

        else:
            print(f"GameManager Error: Unknown Storyteller command_type: {command_type}")

    async def setup_new_game(self, player_ids_roles: Dict[str, str], human_player_ids: List[str] = []):
        async with self._game_lock:
            if self.is_game_running() and self.game_loop_task and not self.game_loop_task.done():
                print("Game is already running. Cannot setup a new game.")
                await self.broadcast_game_event("Game is already running. Cannot setup a new game.")
                return

            # Initialize basic game structures
            self.grimoire = Grimoire()
            self.rule_enforcer = RuleEnforcer(self.grimoire, game_manager=self) # Still useful for low-level rule checks if ST LLM delegates
            self.agents = {}
            self._game_started_event.clear()
            self._current_nominating_player_index = 0
            self._nomination_order = []
            self._daily_chat_log = []

            if not self.google_api_key:
                 print("Warning: GOOGLE_API_KEY not set in environment. AI Agents and Storyteller LLM may not function.")
                 await self.broadcast_game_event("Warning: GOOGLE_API_KEY not set. AI Agents/ST LLM may be passive.")
            
            # Prepare context for Storyteller LLM to perform setup
            initial_context = [
                f"EVENT: REQUEST_GAME_START received.",
                f"INPUT_PLAYER_ROLES: {json.dumps(player_ids_roles)}",
                f"INPUT_HUMAN_PLAYERS: {json.dumps(human_player_ids)}",
                f"GRIMOIRE_STATE: EMPTY_INITIALIZATION"
            ]
            
            print("Requesting Storyteller LLM to perform game setup...")
            setup_commands = await self.storyteller_agent.generate_commands(initial_context)
            print(f"Received setup commands from Storyteller LLM: {setup_commands}")

            for command_obj in setup_commands:
                await self.execute_storyteller_command(command_obj)
            
            # --- The following player agent setup remains, as ST LLM doesn't directly init Python objects ---
            # ST LLM should have used UPDATE_GRIMOIRE_VALUE to set player names, roles etc.
            # We now iterate based on grimoire to create agent objects.

            if not self.grimoire:
                print("CRITICAL ERROR: Grimoire not initialized by Storyteller LLM during setup.")
                # Potentially send an error message to client or halt.
                await self.broadcast_game_event("Critical setup error: Storyteller LLM failed to initialize Grimoire.")
                return
            
            player_display_names = self.grimoire.game_state.get("player_names", {})
            all_player_role_info = [] # For broadcasting roles to observer

            # Ensure all players from input are in grimoire after ST LLM setup
            for player_id, role_name in player_ids_roles.items():
                if player_id not in self.grimoire.players:
                    print(f"Warning: Player {player_id} ({role_name}) was in input but not added to Grimoire by Storyteller LLM. Adding manually.")
                    # This is a fallback, ideally ST LLM handles all additions via commands
                    alignment = get_role_details(role_name)["alignment"].value if get_role_details(role_name) else "Unknown"
                    self.grimoire.add_player(player_id, role_name, alignment)
                    # Also ensure name is set if ST LLM missed it
                    if player_id not in player_display_names:
                        player_display_names[player_id] = f"AI Player ({player_id[:4]})" # Generic name
                        self.grimoire.game_state.setdefault("player_names", {})[player_id] = player_display_names[player_id]
                
                # Populate role info for observer using grimoire's state
                actual_role_name = self.grimoire.get_player_role(player_id)
                display_name = player_display_names.get(player_id, player_id)
                all_player_role_info.append({"id": player_id, "name": display_name, "role": actual_role_name})

                # Initialize PlayerAgent objects
                if player_id not in human_player_ids:
                    alignment = self.grimoire.get_player_alignment(player_id)
                    if self.google_api_key:
                        self.agents[player_id] = PlayerAgent(player_id, actual_role_name, alignment, api_key=self.google_api_key, game_manager=self)
                        print(f"Initialized AI Agent for {display_name} as {actual_role_name} ({alignment})")
                    else:
                        # Fallback to passive agent if no API key
                        self.agents[player_id] = PlayerAgent(player_id, actual_role_name, alignment, api_key=None, game_manager=self)
                        print(f"Skipping LLM for AI agent {display_name} due to missing API key. Player will be passive.")
                else:
                     print(f"Player {display_name} ({actual_role_name}) is a human player.")
            # --- End of PlayerAgent setup ---
            
            # Final broadcasts after ST LLM setup and Agent init
            await self.broadcast_player_roles(all_player_role_info) # Broadcast all roles based on Grimoire
            await self.broadcast_game_state("Initial game state after ST LLM setup")
            await self.broadcast_game_event(f"Game setup by Storyteller LLM with {len(self.grimoire.players)} players. Phase: {self.grimoire.current_phase}.")
            
            if self.game_loop_task and not self.game_loop_task.done():
                self.game_loop_task.cancel()
            self.game_loop_task = asyncio.create_task(self.run_game_loop())
            self._game_started_event.set()
            print("Game loop task created and started event set after Storyteller LLM setup.")

    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.active_connections[player_id] = websocket
        print(f"Player {player_id} connected.")
        if self.grimoire and player_id in self.grimoire.players:
            await self.send_private_info(player_id)
            await self.send_public_state_to_player(player_id, "Welcome to the game!")
        else:
            try:
                 await websocket.send_text(json.dumps({"type": "INFO", "payload": "Game not fully setup or player not in game. Waiting..."}))
            except KeyError as ke_initial_send:
                if player_id == "ObserverClient":
                    print(f"Handled known KeyError during initial send_text to ObserverClient: {repr(ke_initial_send)}")
                    #log and continue, do not let it propagate
                else:
                    print(f"Unexpected KeyError during initial send_text to {player_id}: {repr(ke_initial_send)}")
                    raise #re-raise for other clients
            except Exception as e_initial_send:
                print(f"Error during initial send_text to {player_id}: {type(e_initial_send).__name__} - {e_initial_send}")
                if player_id != "ObserverClient":
                    raise #re-raise for other clients if severe

    def disconnect(self, player_id: str):
        if player_id in self.active_connections:
            del self.active_connections[player_id]
            print(f"Player {player_id} disconnected.")
        if player_id in self.human_player_expected_actions:
            self.human_player_expected_actions[player_id].cancel() #cancel pending future if player disconnects
            del self.human_player_expected_actions[player_id]

    async def send_personal_message(self, player_id: str, message_type: str, payload: Any):
        if player_id in self.active_connections:
            try:
                await self.active_connections[player_id].send_text(json.dumps({"type": message_type, "payload": payload, "to":player_id}))
            except json.JSONDecodeError as je:
                print(f"JSON ENCODE Error sending personal message to {player_id}: {je}") # Should not happen with json.dumps, but for completeness
            except KeyError as ke_send_personal:
                 print(f"KEYERROR sending personal message to {player_id}: {repr(ke_send_personal)}")
            except Exception as e:
                print(f"Error sending personal message to {player_id}: {type(e).__name__} - {e}")
                #self.disconnect(player_id) #disconnecting here might be too aggressive

    async def broadcast_message(self, message_type: str, payload: Any, exclude_player_ids: List[str] = []):
        message_str = ""
        try:
            message_str = json.dumps({"type": message_type, "payload": payload})
        except KeyError as ke_json_dump:
            print(f"!!!! KEYERROR during json.dumps in broadcast_message: {repr(ke_json_dump)}. Payload was: {payload}")
            # If json.dumps fails, we can't proceed with broadcasting this message.
            return 
        except Exception as e_json_dump:
            print(f"Error during json.dumps in broadcast_message: {type(e_json_dump).__name__} - {e_json_dump}. Payload was: {payload}")
            return # Can't proceed

        for player_id, connection in list(self.active_connections.items()): # Iterate over a copy
            if player_id not in exclude_player_ids:
                try:
                    await connection.send_text(message_str)
                except KeyError as ke_broadcast_send:
                    if player_id == "ObserverClient":
                        #specifically handle the known issue with observerclient
                        #observer may miss message
                        print(f"Handled known KeyError during send_text to ObserverClient (observer may miss message): {repr(ke_broadcast_send)}")
                        #for now, just log and continue, preventing the error from propagating.
                    else:
                        #if keyerror happens for a non-observerclient during send_text, this is highly unusual.
                        #log it and re-raise as it might indicate a more severe problem.
                        print(f"!!!! UNEXPECTED KEYERROR during send_text to {player_id} in broadcast_message: {repr(ke_broadcast_send)}")
                        raise #re-raise for unexpected cases
                except Exception as e:
                    print(f"Error broadcasting to {player_id} (during send_text): {type(e).__name__} - {e}")
                    # self.disconnect(player_id) # Consider if a disconnect is too aggressive here
    
    async def send_public_state_to_player(self, player_id: str, reason: str):
        if not self.grimoire: return
        game_state_summary = self._get_public_game_state_summary(reason)
        await self.send_personal_message(player_id, "GAME_STATE_UPDATE", game_state_summary)

    async def broadcast_game_state(self, reason: str):
        if not self.grimoire: return
        game_state_summary = self._get_public_game_state_summary(reason)
        await self.broadcast_message("GAME_STATE_UPDATE", game_state_summary)
    
    def _get_public_game_state_summary(self, reason:str) -> Dict[str, Any]:
        if not self.grimoire: return {}
        public_player_data = []
        for p_id in self.grimoire.players:
            public_player_data.append({
                "id": p_id,
                "name": self.grimoire.game_state.get("player_names", {}).get(p_id, p_id),
                "isAlive": self.grimoire.is_player_alive(p_id)
            })
        return {
            "currentPhase": self.grimoire.current_phase,
            "dayNumber": self.grimoire.day_number,
            "players": public_player_data,
            "nominee": self.grimoire.game_state.get("current_nominee_id"),
            "reason": reason
        }

    async def send_private_info(self, player_id: str):
        if not self.grimoire or player_id not in self.grimoire.players: return
        role = self.grimoire.get_player_role(player_id)
        alignment = self.grimoire.get_player_alignment(player_id)
        role_details = get_role_details(role)
        
        private_payload = {
            "role": role,
            "alignment": alignment,
            "description": role_details.get("description", ""),
            "clues": self.grimoire.statuses.get(player_id,{}).get("private_clues",[]), #try to get existing clues
        }
        #demon/minion specific info is usually sent via rule_enforcer during _resolve_first_night_info
        #this method can be used for on-connect refresh or other private updates
        await self.send_personal_message(player_id, "PRIVATE_INFO_UPDATE", private_payload)

    async def _collect_ai_night_actions(self) -> Dict[str, Any]:
        if not self.grimoire: return {}
        actions = {}
        game_state_summary = self._get_public_game_state_summary("Night action phase")
        alive_player_ids = self.grimoire.get_alive_players()

        action_tasks = {}
        for agent_id, agent in self.agents.items():
            if self.grimoire.is_player_alive(agent_id):
                role_details = get_role_details(agent.role)
                is_first_night = self.grimoire.current_phase == "FIRST_NIGHT"
                needs_action = (is_first_night and role_details.get("first_night_ability")) or \
                               (not is_first_night and role_details.get("other_night_ability"))
                
                #some abilities are passive info, PlayerAgent.get_night_action handles this
                if needs_action:
                    print(f"Requesting night action from AI {agent_id} ({agent.role})")
                    action_tasks[agent_id] = asyncio.create_task(agent.get_night_action(game_state_summary, alive_player_ids))
        
        for agent_id, task in action_tasks.items():
            try:
                action = await asyncio.wait_for(task, timeout=30.0) #30s timeout for LLM
                if action:
                    actions[agent_id] = action
                    print(f"Received night action from AI {agent_id}: {action}")
                else:
                    print(f"AI {agent_id} provided no night action.")
            except asyncio.TimeoutError:
                print(f"Timeout getting night action from AI {agent_id}")
            except Exception as e:
                print(f"Error getting night action from AI {agent_id}: {e}")
        return actions

    async def handle_incoming_message(self, player_id: str, message_str: str):
        try:
            message = json.loads(message_str)
            if not isinstance(message, dict):
                # Ensure message is a dictionary before trying to get 'type'
                print(f"Player {player_id} sent non-dictionary JSON: {message_str}")
                await self.send_personal_message(player_id, "ERROR", {"message": "Invalid message format: expected a JSON object."})
                return
            msg_type = message.get("type")
        except json.JSONDecodeError:
            print(f"Player {player_id} sent malformed JSON: {message_str}")
            await self.send_personal_message(player_id, "ERROR", {"message": "Malformed JSON received."})
            return
        except Exception as e: # Catch any other unexpected error during initial parsing/type checking
            print(f"Unexpected error parsing message from {player_id}. Data: '{message_str}'. ErrorType: {type(e)}, Error: {repr(e)}")
            # Optionally send a generic error message back to the client
            await self.send_personal_message(player_id, "ERROR", {"message": "Error processing your message."})
            return

        if msg_type == "REQUEST_GAME_START":
            # Check if a game is already running and its loop is active
            if self.grimoire and self.rule_enforcer and self.game_loop_task and not self.game_loop_task.done():
                print("Game start requested, but a game is already running and its loop is active.")
                await self.send_personal_message(player_id, "INFO", {"message": "A game is already in progress."})
                return
            # Additional check for lingering game state without an active loop
            if self.grimoire and (not self.game_loop_task or self.game_loop_task.done()):
                 print("Game start requested, but previous game resources might exist without a running loop. Attempting to clear and restart.")
                 # setup_new_game should ideally handle resetting/clearing old state

            print("Received REQUEST_GAME_START. Setting up 10-AI player game.")
            await self.broadcast_game_event("Game start requested for 10 AI players...")
            
            # Define roles for a 10-player game
            # Standard 10-player setup: 7 Townsfolk, 1 Outsider, 1 Minion, 1 Demon
            roles_for_10_players = [
                "Washerwoman", "Librarian", "Investigator", "Chef", "Empath", 
                "Fortune Teller", "Undertaker", # Townsfolk (7)
                "Monk",                         # Outsider (1)
                "Poisoner",                     # Minion (1)
                "Imp"                           # Demon (1)
            ]
            # Shuffle roles to make assignments random each game, or keep fixed for testing
            # random.shuffle(roles_for_10_players) 

            ai_player_ids_roles = {}
            for i in range(10):
                ai_player_id = f"AIPlayer{i+1}"
                ai_player_ids_roles[ai_player_id] = roles_for_10_players[i]
            
            await self.setup_new_game(ai_player_ids_roles, human_player_ids=[]) # No human players
            return

        # For any message type other than REQUEST_GAME_START:
        # If game essentials are not ready, inform client.
        if not self.grimoire or not self.rule_enforcer:
            await self.send_personal_message(player_id, "ERROR", {"message": "Game not active. Send REQUEST_GAME_START to begin."}) 
            return

        # Main game logic for messages during an active/initialized game, protected by lock
        async with self._game_lock:
            # Check if the game loop has started and the game is considered fully 'live'
            if not self._game_started_event.is_set():
                # This means setup_new_game might not have completed, its game loop isn't confirmed running,
                # or the game has ended and the event was cleared.
                message_to_send = "Game is not currently active, has ended, or is still initializing."
                if player_id == "ObserverClient":
                    message_to_send = "Game is not currently active, has ended, or is still initializing. Observer commands (other than start) ignored."
                
                print(f"Player {player_id} sent message type '{msg_type}' while game event not set. Sending: {message_to_send}")
                await self.send_personal_message(player_id, "INFO", {"message": message_to_send})
                return

            # At this point: grimoire, rule_enforcer exist, AND _game_started_event IS SET.
            # This implies the game is "live" and the game loop should be running or have run.

            if player_id == "ObserverClient":
                # Observer client sent a message (that isn't REQUEST_GAME_START) while the game is live.
                # These messages are generally ignored, other than providing feedback.
                print(f"ObserverClient sent non-start message (type: {msg_type}) during active game. Ignoring.")
                await self.send_personal_message(
                    player_id,
                    "INFO",
                    {"message": f"Received your message (type: {msg_type}). Game is active. Observer client actions are limited."}
                )
                return

            # AI/Human player active game message handling would continue here
            # This part needs to be reviewed based on how AI/Human player messages are to be handled
            print(f"Player {player_id} (not Observer) sent unhandled message type '{msg_type}': {message_str}")
            await self.send_personal_message(player_id, "INFO", {"message": f"Received unhandled message type: {msg_type}"})
            # Removed processing for SEND_CHAT, NOMINATE, CAST_VOTE, NIGHT_ACTION from observer client
            # These actions are now AI-driven or handled internally by game loop.
            # Based on original logic, these were removed for observer. If actual players send these,
            # they should be processed by their respective logic, which seems to be missing/commented out here.
            # This section should be where human player actions are routed if this function handles them.
            # The original comment implies these are AI-driven or internal, which means this part
            # might only be for logging unhandled messages from non-observer, non-AI (if any) clients.

    async def run_game_loop(self):
        print("Game loop waiting for game to be fully started...")
        await self._game_started_event.wait() # Ensure setup_new_game has completed
        print("Game loop starting active processing.")

        if not self.grimoire or not self.rule_enforcer:
            print("Game loop exiting: Grimoire or RuleEnforcer not initialized.")
            return

        try:
            while self.grimoire is not None: # Loop as long as game is active
                async with self._game_lock:
                    current_phase = self.grimoire.current_phase
                    print(f"Game Loop Tick. Current phase: {current_phase}, Day: {self.grimoire.day_number}")
                    game_state_summary = self._get_public_game_state_summary(f"Start of {current_phase}")
                    alive_player_ids = self.grimoire.get_alive_players()
                
                if current_phase == "FIRST_NIGHT" or current_phase == "NIGHT":
                    await self.broadcast_game_state(f"Night {self.grimoire.day_number} begins.")
                    #collect actions (AI + Human)
                    night_actions: Dict[str, Any] = {}
                    human_night_action_futures: Dict[str, asyncio.Future] = {}

                    #AI actions
                    ai_actions = await self._collect_ai_night_actions()
                    night_actions.update(ai_actions)

                    #human actions
                    for p_id in alive_player_ids:
                        if p_id not in self.agents: #it's a human
                            role_details = get_role_details(self.grimoire.get_player_role(p_id))
                            needs_action = (current_phase == "FIRST_NIGHT" and role_details.get("first_night_ability")) or \
                                           (current_phase == "NIGHT" and role_details.get("other_night_ability"))
                            #further filter if role actually requires a choice (e.g. not Washerwoman passive info)
                            #this logic is partly in PlayerAgent, replicate for human prompts
                            if needs_action and not (role_details.get("name") in ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath"] and current_phase == "FIRST_NIGHT"): #todo: refine this check
                                fut = asyncio.Future()
                                self.human_player_expected_actions[p_id] = fut
                                human_night_action_futures[p_id] = fut
                                await self.send_personal_message(p_id, "REQUEST_NIGHT_ACTION", {"role": role_details.get("name"), "description": role_details.get("description")})
                   
                    for p_id, fut in human_night_action_futures.items():
                        try:
                            action = await asyncio.wait_for(fut, timeout=60.0) #1 min for human night action
                            night_actions[p_id] = action
                            print(f"Received night action from Human {p_id}: {action}")
                        except asyncio.TimeoutError:
                            print(f"Timeout for human night action from {p_id}")
                            #todo: storyteller might make a default action or warn player
                        except asyncio.CancelledError:
                            print(f"Night action future for human {p_id} was cancelled.")
                        finally:
                            if p_id in self.human_player_expected_actions: del self.human_player_expected_actions[p_id]

                    async with self._game_lock:
                        await self.rule_enforcer.resolve_night_actions(night_actions)
                        self.rule_enforcer.transition_to_day()
                    await self.broadcast_game_state(f"Day {self.grimoire.day_number} begins.")
                    self._daily_chat_log = [] #clear log for new day

                elif current_phase == "DAY_CHAT":
                    if not self._nomination_order:
                        self._nomination_order = list(self.grimoire.get_alive_players()) #simple order for now
                        random.shuffle(self._nomination_order)
                        self._current_nominating_player_index = 0
                    
                    # New AI Communication Round
                    # This allows AIs to chat (publicly or privately) before nominations perhaps
                    await self.broadcast_game_event("Day phase: General discussion period begins.")
                    # Pass a summary of game state suitable for AI decision making
                    # Ensure game_state_summary contains 'all_players_details' and 'daily_chat_log' as expected by agents
                    ai_context_game_state = {
                         **self._get_public_game_state_summary("AI Communication Round"),
                         "daily_chat_log": list(self._daily_chat_log), # pass current log
                         "all_players_details": [
                            {"id": p_id, 
                             "name": self.grimoire.game_state.get("player_names", {}).get(p_id, p_id),
                             "is_alive": self.grimoire.is_player_alive(p_id)} 
                            for p_id in self.grimoire.players
                         ]
                    }
                    await self._process_ai_communication_round(ai_context_game_state)
                    await asyncio.sleep(2) # Give some time for observer to read chats

                    # Nomination turn management (simplified)
                    if self._nomination_order and self._current_nominating_player_index < len(self._nomination_order):
                        current_nominator_id = self._nomination_order[self._current_nominating_player_index]
                        if not self.grimoire.is_player_alive(current_nominator_id) or not self.grimoire.get_player_status(current_nominator_id, "can_nominate"):
                            self._current_nominating_player_index += 1 #skip dead or unable nominator
                            continue

                        await self.broadcast_message("NOMINATION_TURN", {"player_id": current_nominator_id, "player_name": self.grimoire.game_state.get("player_names",{}).get(current_nominator_id, current_nominator_id)})
                        print(f"It is {current_nominator_id}'s turn to nominate.")
                        #if AI, trigger nomination. If human, wait for NOMINATE message handled by handle_incoming_message
                        if current_nominator_id in self.agents:
                            # ai nomination: let agent choose a nominee
                            alive_with_names = [
                                {"id": pid, "name": self.grimoire.game_state.get("player_names", {}).get(pid, pid)}
                                for pid in self.grimoire.get_alive_players()
                            ]
                            chosen_nominee = await self.agents[current_nominator_id].decide_nomination(
                                game_state_summary, alive_with_names, []
                            )
                            if chosen_nominee:
                                self.rule_enforcer.process_nomination(current_nominator_id, chosen_nominee)
                                await self.broadcast_game_state(
                                    f"AI {current_nominator_id} nominated {chosen_nominee}."
                                )
                            else:
                                # no nomination from this agent, move to next
                                self._current_nominating_player_index +=1
                                continue
                            # after nomination, proceed to voting phase in next loop
                            continue
                        else: #human nominator, handled by handle_incoming_message which will call rule_enforcer
                            #the game loop effectively pauses here for this human action until message arrives or timeout
                            await asyncio.sleep(30) #simple wait, real solution needs futures from handle_incoming_message
                            pass #waiting for human via websocket
                    else:
                        #all nominations done or no one can nominate -> go to voting if a nominee exists, or night
                        print("Nomination round potentially finished or no one to nominate.")
                        async with self._game_lock:
                            if "current_nominee_id" not in self.grimoire.game_state:
                                #no successful nomination, end of day essentially
                                self.grimoire.log_event("DAY_END_NO_NOMINATION", {})
                                self.rule_enforcer.transition_to_night()
                        await self.broadcast_game_state("No successful nomination. Transitioning to night.")

                elif current_phase == "VOTING":
                    nominee_id = self.grimoire.game_state.get("current_nominee_id")
                    if not nominee_id: self.rule_enforcer.transition_to_day(); continue #should not happen

                    await self.broadcast_message("VOTE_START", {"nominee_id": nominee_id, "nominee_name": self.grimoire.game_state.get("player_names",{}).get(nominee_id, nominee_id)})
                    
                    votes: Dict[str, bool] = {}
                    human_vote_futures: Dict[str, asyncio.Future] = {}

                    #collect AI votes
                    for agent_id, agent in self.agents.items():
                        if self.grimoire.is_player_alive(agent_id):
                            #todo: check Butler condition for AI
                            vote_decision = await agent.decide_vote(game_state_summary, nominee_id)
                            if vote_decision is not None: votes[agent_id] = vote_decision
                    
                    #collect Human votes
                    for p_id in alive_player_ids:
                        if p_id not in self.agents: #human
                            #todo: check Butler condition
                            fut = asyncio.Future()
                            self.human_player_expected_actions[p_id] = fut
                            human_vote_futures[p_id] = fut
                            await self.send_personal_message(p_id, "REQUEST_VOTE", {"nominee_id": nominee_id})

                    for p_id, fut in human_vote_futures.items():
                        try:
                            action_payload = await asyncio.wait_for(fut, timeout=30.0) #30s for human vote
                            if action_payload and "vote" in action_payload:
                                votes[p_id] = action_payload["vote"]
                        except asyncio.TimeoutError:
                            print(f"Timeout for human vote from {p_id}. Defaulting to NO.")
                            votes[p_id] = False #default vote on timeout
                        except asyncio.CancelledError:
                            print(f"Vote future for human {p_id} was cancelled.")
                        finally:
                             if p_id in self.human_player_expected_actions: del self.human_player_expected_actions[p_id]
                   
                    async with self._game_lock:
                        self.rule_enforcer.process_votes(votes)
                    await self.broadcast_game_state(f"Voting on {nominee_id} complete. New phase: {self.grimoire.current_phase}")
                    self._nomination_order = [] #reset for next day or if nominations reopen
                    self._current_nominating_player_index = 0

                #check victory conditions after each major state change (esp. after votes/night actions)
                async with self._game_lock:
                    game_over, winner = self.rule_enforcer.check_victory_conditions()
                
                if game_over:
                    print(f"Game Over! Winner: {winner}")
                    await self.broadcast_message("GAME_END", {"winner": winner, "reason": "Victory condition met"})
                    self.grimoire = None #stop game by clearing grimoire
                    self._game_started_event.clear()
                    break #exit game loop

                await asyncio.sleep(1) #short pause to prevent tight loop if phases change rapidly
        except asyncio.CancelledError:
            print("Game loop was cancelled.")
        except Exception as e:
            print(f"Critical error in game loop: {e}")
            # Potentially try to gracefully end the game or notify players
        finally:
            self._game_started_event.clear()
            print("Game loop ended.")

    async def broadcast_player_roles(self, roles_info: List[Dict[str, str]]):
        """Broadcasts all player roles to all connected clients (for observer mode)."""
        await self.broadcast_message("PLAYER_ROLES_UPDATE", {"roles": roles_info})

    async def broadcast_game_event(self, event_message: str):
        """Broadcasts a generic game event string to all clients."""
        await self.broadcast_message("GAME_EVENT", {"message": event_message})

    async def _deliver_private_ai_message(self, sender_id: str, recipient_id: str, message_text: str):
        """Delivers a private message from one AI agent to another."""
        recipient_agent = self.agents.get(recipient_id)
        sender_agent_name = self.grimoire.game_state.get("player_names", {}).get(sender_id, sender_id)
        if recipient_agent and hasattr(recipient_agent, 'receive_private_message'):
            print(f"Delivering private message from {sender_agent_name} ({sender_id}) to {recipient_id}")
            await recipient_agent.receive_private_message(sender_id=sender_id, sender_name=sender_agent_name, message_text=message_text)
            # Optionally, inform the sender that their private message was delivered (e.g., for logging or confirmation)
            # sender_agent = self.agents.get(sender_id)
            # if sender_agent and hasattr(sender_agent, 'confirm_private_message_delivered'):
            #     await sender_agent.confirm_private_message_delivered(recipient_id, message_text)
        else:
            print(f"Could not deliver private AI message: Recipient {recipient_id} not found or cannot receive private messages.")

    async def _process_ai_communication_round(self, game_state_summary_for_ai: Dict[str, Any]):
        """
        Allows each AI agent to communicate. They can choose to public chat, private chat, or stay silent.
        This is a conceptual new step in the day phase.
        """
        if not self.grimoire: return

        # create a list of player details for ai context (name and id)
        # iterate over the players list instead of using .items()
        all_player_details_for_prompt = [
            {
                "id": p_id,
                "name": self.grimoire.game_state.get("player_names", {}).get(p_id, p_id),
                "is_alive": self.grimoire.is_player_alive(p_id)
            }
            for p_id in self.grimoire.players
        ]

        communication_tasks = {}
        for agent_id, agent in self.agents.items():
            if self.grimoire.is_player_alive(agent_id) and hasattr(agent, 'decide_communication'):
                # Pass the daily_chat_log for context
                current_game_state_for_agent = {
                    **game_state_summary_for_ai,
                    "daily_chat_log": list(self._daily_chat_log), # Pass a copy
                    "all_players_details": all_player_details_for_prompt # List of {'id', 'name', 'is_alive'}
                }
                communication_tasks[agent_id] = asyncio.create_task(
                    agent.decide_communication(current_game_state_for_agent)
                )
        
        processed_communications = await asyncio.gather(*communication_tasks.values(), return_exceptions=True)

        for agent_id, result in zip(communication_tasks.keys(), processed_communications):
            if isinstance(result, Exception):
                print(f"Error getting communication decision from AI {agent_id}: {result}")
                continue
            
            if not result: # AI chose to be silent or error
                continue

            comm_type = result.get("type")
            text = result.get("text")
            recipient_id = result.get("recipient_id")
            sender_name = self.grimoire.game_state.get("player_names", {}).get(agent_id, agent_id)

            if comm_type == "PUBLIC_CHAT" and text:
                print(f"AI {sender_name} ({agent_id}) public chat: {text}")
                chat_event = {
                    "sender": agent_id,
                    "sender_name": sender_name,
                    "text": text,
                    "timestamp": "#placeholder_timestamp#" 
                }
                self.grimoire.log_event("CHAT", chat_event)
                self._daily_chat_log.append(chat_event)
                await self.broadcast_message("CHAT_MESSAGE", chat_event)
            elif comm_type == "PRIVATE_CHAT" and text and recipient_id:
                if recipient_id != agent_id and recipient_id in self.agents: # Cannot private chat self, must be valid AI
                    print(f"AI {sender_name} ({agent_id}) sending private message to {recipient_id}: {text}")
                    await self._deliver_private_ai_message(agent_id, recipient_id, text)
                elif recipient_id == agent_id:
                    print(f"AI {sender_name} ({agent_id}) tried to send private message to self. Ignored.")
                else:
                    print(f"AI {sender_name} ({agent_id}) tried to send private message to invalid recipient {recipient_id}. Ignored.")
            elif comm_type == "SILENT":
                print(f"AI {sender_name} ({agent_id}) chose to remain silent.")
            # else: AI returned an unexpected communication type or was None

game_manager = GameManager()
#get player names for logging etc.
player_names = game_manager.grimoire.game_state.get("player_names", {}) if game_manager.grimoire else {}

@app.on_event("startup")
async def startup_event():
    print("Server starting up...")
    # Game setup is now triggered by a client message for more control during dev
    # Example: send {"type": "REQUEST_GAME_START"} from client to trigger setup below.
    print("Game will be set up upon client request using 'REQUEST_GAME_START' message.")

@app.get("/") #temp endpoint for testing client html
async def get_client_html():
    return HTMLResponse(html)

@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    await game_manager.connect(websocket, player_id)
    try:
        while True:
            data = ""
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                raise
            except KeyError as ke_recv:
                if player_id == "ObserverClient" and ke_recv.args == ('name',):
                    print(f"Handled known KeyError('name') during receive_text for ObserverClient: {repr(ke_recv)}. Disconnecting observer.")
                    game_manager.disconnect(player_id) #ensure disconnection
                    return #exit the while True loop and thus the endpoint function
                else:
                    #log other KeyErrors or for other clients before re-raising
                    print(f"KeyError during websocket.receive_text() for {player_id}: ExceptionType={type(ke_recv)}, Args={ke_recv.args}, ExceptionRepr={repr(ke_recv)}")
                    raise #re-raise
            except Exception as e_recv:
                print(f"Error specifically during websocket.receive_text() for {player_id}: ExceptionType={type(e_recv)}, Args={e_recv.args}, ExceptionRepr={repr(e_recv)}")
                raise # Re-raise to be caught by the outer loop
            await game_manager.handle_incoming_message(player_id, data)
    except WebSocketDisconnect:
        game_manager.disconnect(player_id)
    except Exception as e:
        # Print more detailed error information safely
        err_type_name = type(e).__name__ # Get type name safely
        err_args_str = "N/A"
        try:
            err_args_str = str(e.args) # Try to get args as string
        except Exception:
            err_args_str = "[Could not retrieve e.args]"
        
        err_repr_str = "N/A"
        try:
            err_repr_str = repr(e) # Try to get repr as string
        except Exception: # If repr(e) itself errors (like causing a KeyError)
            err_repr_str = f"[Could not retrieve repr(e). Original error type was: {err_type_name}]"

        scope_info = "N/A"
        try:
            scope_info = str(websocket.scope) # Log the scope
        except Exception as e_scope:
            scope_info = f"[Could not retrieve websocket.scope due to: {type(e_scope).__name__}]"

        print(f"Error in WebSocket connection for {player_id}: OriginalExceptionType={err_type_name}, OriginalArgs={err_args_str}, OriginalReprAttempt={err_repr_str}, Scope={scope_info}")
        game_manager.disconnect(player_id)

if __name__ == "__main__":
    print("Starting game server on http://localhost:8000")
    print("Open http://localhost:8000 in a browser to observe.")
    print("Ensure GOOGLE_API_KEY environment variable is set for AI players.")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True) 