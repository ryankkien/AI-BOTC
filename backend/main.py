#backend/main.py
import asyncio
import uvicorn
import json #for parsing and sending structured data
import os #for environment variables
import random #for shuffling roles if needed
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse #for testing
from typing import Dict, List, Any, Optional
from datetime import datetime

from .storyteller.grimoire import Grimoire
from .storyteller.rules import RuleEnforcer
from .storyteller.roles import ROLES_DATA, RoleAlignment, RoleType, get_role_details #import all necessary items
from .agents.player_agent import PlayerAgent
from .agents.base_agent import BaseAgent #if we need to type hint with base class
from .agents.storyteller_agent import StorytellerAgent

#game settings configuration
class GameSettings:
    def __init__(self):
        self.memory_curator_enabled = True
        self.auto_night_actions = True
        self.verbose_logging = True
        self.ai_chat_frequency = "normal"  #"low", "normal", "high"
        self.private_chat_enabled = True
    
    def to_dict(self):
        return {
            "memory_curator_enabled": self.memory_curator_enabled,
            "auto_night_actions": self.auto_night_actions,
            "verbose_logging": self.verbose_logging,
            "ai_chat_frequency": self.ai_chat_frequency,
            "private_chat_enabled": self.private_chat_enabled
        }
    
    def update_from_dict(self, settings_dict):
        for key, value in settings_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)

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
            /* make logs and chat panels resizable and preserve newlines */
            #messages, #storytellerLog { list-style-type: none; padding: 5px; margin: 0; flex-grow: 1; overflow-y: auto; border: 1px solid #eee; resize: vertical; white-space: pre-wrap; }
            #playerRoles { list-style-type: none; padding: 0; }
            /* ensure each log entry preserves whitespace and wraps */
            .message-item, .log-item, .role-item { margin-bottom: 5px; padding: 8px; border-radius: 4px; white-space: pre-wrap; }
            .chat-message { background-color: #e1f5fe; }
            .game-event { background-color: #fff9c4; }
            .error-message { background-color: #ffcdd2; color: #c62828; }
            /* tabs styling */
            .tabs { display: flex; border-bottom: 1px solid #ccc; margin-bottom: 10px; }
            .tab-button { flex: 1; padding: 8px; background: none; border: none; cursor: pointer; transition: background-color 0.3s; }
            .tab-button:hover { background-color: #eee; }
            .tab-button.active { border-bottom: 2px solid #5cb85c; color: #5cb85c; font-weight: bold; }
            .tab-contents { display: flex; flex-direction: column; flex-grow: 1; overflow: auto; }
            .tab-content { flex-grow: 1; overflow-y: auto; }
            .info-message { background-color: #c8e6c9; }
            .storyteller-message { background-color: #d1c4e9; } /* Storyteller messages color */
            .connection-bar { padding: 10px; background-color: #f0f0f0; border-bottom: 1px solid #ccc; }
            .role-item.selected { background-color: #007bff; color: white; font-weight: bold; }
            h1, h2, h3 { margin-top: 0; }
            
            /* settings popup styles */
            .settings-overlay { 
                display: none; 
                position: fixed; 
                top: 0; 
                left: 0; 
                width: 100%; 
                height: 100%; 
                background-color: rgba(0,0,0,0.5); 
                z-index: 1000; 
            }
            .settings-popup { 
                position: absolute; 
                top: 50%; 
                left: 50%; 
                transform: translate(-50%, -50%); 
                background: white; 
                padding: 20px; 
                border-radius: 10px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.3); 
                min-width: 400px; 
                max-width: 600px; 
            }
            .settings-section { 
                margin-bottom: 20px; 
                padding: 15px; 
                border: 1px solid #ddd; 
                border-radius: 5px; 
                background-color: #f9f9f9; 
            }
            .settings-section h3 { 
                margin-top: 0; 
                color: #333; 
                border-bottom: 1px solid #ddd; 
                padding-bottom: 5px; 
            }
            .setting-item { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                margin-bottom: 10px; 
            }
            .setting-item:last-child { 
                margin-bottom: 0; 
            }
            .setting-label { 
                flex-grow: 1; 
                margin-right: 10px; 
                font-weight: 500; 
            }
            .setting-description { 
                font-size: 12px; 
                color: #666; 
                margin-top: 2px; 
            }
            .setting-control { 
                flex-shrink: 0; 
            }
            .toggle-switch { 
                position: relative; 
                width: 50px; 
                height: 24px; 
                background-color: #ccc; 
                border-radius: 12px; 
                cursor: pointer; 
                transition: background-color 0.3s; 
            }
            .toggle-switch.active { 
                background-color: #4CAF50; 
            }
            .toggle-slider { 
                position: absolute; 
                top: 2px; 
                left: 2px; 
                width: 20px; 
                height: 20px; 
                background-color: white; 
                border-radius: 10px; 
                transition: transform 0.3s; 
            }
            .toggle-switch.active .toggle-slider { 
                transform: translateX(26px); 
            }
            .settings-buttons { 
                display: flex; 
                justify-content: flex-end; 
                gap: 10px; 
                margin-top: 20px; 
            }
            .btn { 
                padding: 8px 16px; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer; 
                transition: background-color 0.3s; 
            }
            .btn-primary { 
                background-color: #007bff; 
                color: white; 
            }
            .btn-primary:hover { 
                background-color: #0056b3; 
            }
            .btn-secondary { 
                background-color: #6c757d; 
                color: white; 
            }
            .btn-secondary:hover { 
                background-color: #545b62; 
            }
            select { 
                padding: 4px 8px; 
                border: 1px solid #ccc; 
                border-radius: 4px; 
            }
        </style>
    </head>
    <body>
        <!-- settings popup overlay -->
        <div id="settingsOverlay" class="settings-overlay">
            <div class="settings-popup">
                <h2>⚙️ Game Settings</h2>
                
                <div class="settings-section">
                    <h3>AI Behavior Settings</h3>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">Memory Curator</div>
                            <div class="setting-description">when enabled, ai players use llm to filter important memories. when disabled, they remember everything.</div>
                        </div>
                        <div class="setting-control">
                            <div id="memoryCuratorToggle" class="toggle-switch active">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">Private Chat</div>
                            <div class="setting-description">allow ai players to have private conversations during night phases</div>
                        </div>
                        <div class="setting-control">
                            <div id="privateChatToggle" class="toggle-switch active">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">AI Chat Frequency</div>
                            <div class="setting-description">how often ai players will chat during day phases</div>
                        </div>
                        <div class="setting-control">
                            <select id="chatFrequencySelect">
                                <option value="low">Low</option>
                                <option value="normal" selected>Normal</option>
                                <option value="high">High</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <div class="settings-section">
                    <h3>Game Flow Settings</h3>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">Auto Night Actions</div>
                            <div class="setting-description">automatically process night actions without manual storyteller intervention</div>
                        </div>
                        <div class="setting-control">
                            <div id="autoNightToggle" class="toggle-switch active">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">Verbose Logging</div>
                            <div class="setting-description">detailed logging for debugging and analysis</div>
                        </div>
                        <div class="setting-control">
                            <div id="verboseLoggingToggle" class="toggle-switch active">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="settings-buttons">
                    <button class="btn btn-secondary" onclick="closeSettings()">Cancel</button>
                    <button class="btn btn-primary" onclick="saveSettings()">Save Settings</button>
                </div>
            </div>
        </div>

        <div class="connection-bar">
            Player ID (Observer): <input type="text" id="observerId" value="ObserverClient"/>
            <button onclick="connectWs()">Connect</button>
            <button onclick="requestGameStart()">Start 10-AI Player Game</button>
            <button onclick="saveLogs()">Save Comprehensive Logs</button>
            <button onclick="openSettings()">⚙️ Settings</button>
        </div>
        <div class="container">
            <div class="main-content">
                <div class="tabs">
                  <button class="tab-button active" data-target="storyteller">Storyteller Log & Game Events</button>
                  <button class="tab-button" data-target="chat">AI Player Chat</button>
                </div>
                <div class="tab-contents">
                  <div id="storyteller" class="tab-content">
                    <ul id="storytellerLog"></ul>
                  </div>
                  <div id="chat" class="tab-content" style="display:none;">
                    <ul id="messages"></ul>
                  </div>
                </div>
            </div>
            <div class="sidebar">
                <h2>Player Roles</h2>
                <ul id="playerRoles"></ul>
                <h2 id="memoryHeader">Player Perspective</h2>
                <div id="memoryPanel" style="border:1px solid #eee; padding:5px; flex-grow:1; overflow-y:auto;">Click on a player role to see their perspective</div>
            </div>
        </div>

        <script>
            var ws = null;
            const storytellerLog = document.getElementById('storytellerLog');
            const messagesList = document.getElementById('messages');
            const playerRolesList = document.getElementById('playerRoles');
            var rolesMap = {}; // map of playerId to role for observer display
            var currentSettings = {
                memory_curator_enabled: true,
                auto_night_actions: true,
                verbose_logging: true,
                ai_chat_frequency: "normal",
                private_chat_enabled: true
            };

            // settings ui functions
            function openSettings() {
                // request current settings from server
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: "REQUEST_SETTINGS" }));
                }
                updateSettingsUI();
                document.getElementById('settingsOverlay').style.display = 'block';
            }

            function closeSettings() {
                document.getElementById('settingsOverlay').style.display = 'none';
            }

            function updateSettingsUI() {
                document.getElementById('memoryCuratorToggle').classList.toggle('active', currentSettings.memory_curator_enabled);
                document.getElementById('privateChatToggle').classList.toggle('active', currentSettings.private_chat_enabled);
                document.getElementById('autoNightToggle').classList.toggle('active', currentSettings.auto_night_actions);
                document.getElementById('verboseLoggingToggle').classList.toggle('active', currentSettings.verbose_logging);
                document.getElementById('chatFrequencySelect').value = currentSettings.ai_chat_frequency;
            }

            function saveSettings() {
                // collect settings from ui
                const newSettings = {
                    memory_curator_enabled: document.getElementById('memoryCuratorToggle').classList.contains('active'),
                    private_chat_enabled: document.getElementById('privateChatToggle').classList.contains('active'),
                    auto_night_actions: document.getElementById('autoNightToggle').classList.contains('active'),
                    verbose_logging: document.getElementById('verboseLoggingToggle').classList.contains('active'),
                    ai_chat_frequency: document.getElementById('chatFrequencySelect').value
                };
                
                // send to server
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ 
                        type: "UPDATE_SETTINGS", 
                        payload: newSettings 
                    }));
                    currentSettings = newSettings;
                    addMessageToList(storytellerLog, "settings updated successfully", "info-message");
                }
                
                closeSettings();
            }

            // toggle switch click handlers
            document.addEventListener('DOMContentLoaded', function() {
                ['memoryCuratorToggle', 'privateChatToggle', 'autoNightToggle', 'verboseLoggingToggle'].forEach(id => {
                    document.getElementById(id).addEventListener('click', function() {
                        this.classList.toggle('active');
                    });
                });
                
                // close settings when clicking overlay
                document.getElementById('settingsOverlay').addEventListener('click', function(e) {
                    if (e.target === this) {
                        closeSettings();
                    }
                });
            });

            function formatPlayerPerspective(perspective) {
                if (perspective.error) {
                    return `<div style="color: red;">Error: ${perspective.error}</div>`;
                }
                
                let html = '';
                
                // Player Info
                const player = perspective.player_info;
                html += `<h3>${player.name} (${player.id})</h3>`;
                html += `<p><strong>Role:</strong> ${player.role}</p>`;
                html += `<p><strong>Alignment:</strong> ${player.alignment}</p>`;
                html += `<p><strong>Status:</strong> ${JSON.stringify(player.status)}</p>`;
                
                // Private Information
                const privateInfo = perspective.private_information;
                html += `<h4>🔒 Private Information</h4>`;
                html += `<p><strong>Role Ability:</strong> ${privateInfo.role_ability}</p>`;
                if (privateInfo.storyteller_told_me) {
                    html += `<p><strong>Storyteller told me:</strong> ${privateInfo.storyteller_told_me}</p>`;
                }
                if (privateInfo.private_clues && privateInfo.private_clues.length > 0) {
                    html += `<p><strong>Private clues:</strong></p><ul>`;
                    privateInfo.private_clues.forEach(clue => {
                        html += `<li>${clue}</li>`;
                    });
                    html += `</ul>`;
                }
                
                // My Actions
                const actions = perspective.my_actions;
                html += `<h4>⚡ My Actions</h4>`;
                if (actions.votes_cast && actions.votes_cast.length > 0) {
                    html += `<p><strong>Votes cast:</strong></p><ul>`;
                    actions.votes_cast.forEach(vote => {
                        html += `<li>${JSON.stringify(vote)}</li>`;
                    });
                    html += `</ul>`;
                }
                if (actions.nominations_made && actions.nominations_made.length > 0) {
                    html += `<p><strong>Nominations made:</strong></p><ul>`;
                    actions.nominations_made.forEach(nom => {
                        html += `<li>${JSON.stringify(nom)}</li>`;
                    });
                    html += `</ul>`;
                }
                if (actions.actions_taken && actions.actions_taken.length > 0) {
                    html += `<p><strong>Actions taken:</strong></p><ul>`;
                    actions.actions_taken.forEach(action => {
                        html += `<li>${JSON.stringify(action)}</li>`;
                    });
                    html += `</ul>`;
                }
                
                // My Observations
                const observations = perspective.my_observations;
                html += `<h4>👁️ My Observations</h4>`;
                if (observations.important_events && observations.important_events.length > 0) {
                    html += `<p><strong>Important events:</strong></p><ul>`;
                    observations.important_events.forEach(event => {
                        html += `<li>${event}</li>`;
                    });
                    html += `</ul>`;
                }
                if (observations.observations && observations.observations.length > 0) {
                    html += `<p><strong>Other observations:</strong></p><ul>`;
                    observations.observations.forEach(obs => {
                        html += `<li>${obs}</li>`;
                    });
                    html += `</ul>`;
                }
                
                // Communications
                const comms = perspective.communications;
                html += `<h4>💬 Communications</h4>`;
                if (comms.private_conversations && Object.keys(comms.private_conversations).length > 0) {
                    html += `<p><strong>Private conversations:</strong></p>`;
                    Object.entries(comms.private_conversations).forEach(([partnerName, convo]) => {
                        html += `<details><summary>With ${partnerName}</summary>`;
                        html += `<ul>`;
                        convo.messages.forEach(msg => {
                            html += `<li><strong>${msg.sender_name}:</strong> ${msg.text} <em>(${msg.timestamp})</em></li>`;
                        });
                        html += `</ul></details>`;
                    });
                }
                
                // Game Context
                const context = perspective.game_context;
                html += `<h4>🎮 Game Context</h4>`;
                html += `<p><strong>Phase:</strong> ${context.current_phase}</p>`;
                html += `<p><strong>Day:</strong> ${context.day_number}</p>`;
                html += `<p><strong>Players alive:</strong> ${context.players_alive}/${context.total_players}</p>`;
                
                return html;
            }

            function addMessageToList(listElement, text, type) {
                var li = document.createElement('li');
                li.className = 'message-item ' + type;
                var details = document.createElement('details');
                var summary = document.createElement('summary');
                var firstLine = text.split('\\n')[0];
                summary.textContent = firstLine;
                details.appendChild(summary);
                var pre = document.createElement('pre');
                pre.style.whiteSpace = 'pre-wrap';
                pre.textContent = text;
                details.appendChild(pre);
                li.appendChild(details);
                listElement.appendChild(li);
                listElement.scrollTop = listElement.scrollHeight;
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
                        case "PLAYER_ROLES_UPDATE": // New message type for roles
                            rolesMap = {};
                            playerRolesList.innerHTML = '';
                            if (payload.roles && Array.isArray(payload.roles)) {
                                payload.roles.forEach((player, idx) => {
                                    rolesMap[player.id] = player.role;
                                    const li = document.createElement('li');
                                    li.className = 'role-item';
                                    li.textContent = `${idx+1}. ${player.name}: ${player.role}`;
                                    li.dataset.playerId = player.id;
                                    li.style.cursor = 'pointer';
                                    li.addEventListener('click', () => {
                                        // Remove selection from all other roles
                                        document.querySelectorAll('.role-item').forEach(item => item.classList.remove('selected'));
                                        // Add selection to clicked role
                                        li.classList.add('selected');
                                        ws.send(JSON.stringify({ type: 'REQUEST_MEMORY', payload: { player_id: player.id } }));
                                    });
                                    playerRolesList.appendChild(li);
                                });
                            }
                            break;
                        case "GAME_EVENT": // Generic game event from storyteller
                             addMessageToList(storytellerLog, `STORYTELLER: ${payload.message}`, "storyteller-message");
                             break;
                        case "CHAT_MESSAGE":
                            const senderName = payload.sender_name || payload.sender;
                            const role = rolesMap[payload.sender] || '';
                            const display = role ? `${senderName} (${role})` : senderName;
                            addMessageToList(messagesList, `${display}: ${payload.text}`, "chat-message");
                            break;
                        case "MEMORY_UPDATE":
                            const memPid = payload.player_id;
                            const perspective = payload.perspective;
                            document.getElementById('memoryPanel').innerHTML = formatPlayerPerspective(perspective);
                            // Update header to show whose perspective this is
                            const playerName = perspective.player_info ? perspective.player_info.name : memPid;
                            document.getElementById('memoryHeader').textContent = `${playerName}'s Perspective`;
                            break;
                        case "SETTINGS_UPDATE":
                            // server sent current settings
                            currentSettings = payload;
                            updateSettingsUI();
                            addMessageToList(storytellerLog, "received current settings from server", "info-message");
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
            
            //implement save_logs button functionality
            function saveLogs() {
                fetch('/save_logs')
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            addMessageToList(storytellerLog, 'ERROR: ' + data.error, 'error-message');
                        } else {
                            addMessageToList(storytellerLog, 'INFO: Comprehensive logs saved successfully at ' + data.filepath, 'info-message');
                        }
                    })
                    .catch(error => {
                        addMessageToList(storytellerLog, 'ERROR: error saving logs: ' + error, 'error-message');
                    });
            }
            
            // Removed sendMessage function as observer does not send chat.
            // If you need to send other specific commands for testing, add new functions like requestGameStart.
            // tab switching logic
            document.addEventListener('DOMContentLoaded', function() {
                const tabButtons = document.querySelectorAll('.tab-button');
                tabButtons.forEach(function(btn) {
                    btn.addEventListener('click', function() {
                        tabButtons.forEach(b => b.classList.remove('active'));
                        document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
                        this.classList.add('active');
                        const target = this.getAttribute('data-target');
                        document.getElementById(target).style.display = 'block';
                    });
                });
            });
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
        self.settings = GameSettings()  #add game settings
        
        # LLM configuration - support multiple providers
        self.llm_provider_type = os.getenv("LLM_PROVIDER", "auto")
        self.llm_model = os.getenv("LLM_MODEL")
        
        # Legacy support for Google API key
        self.google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        
        # Get the appropriate API key based on provider
        self.api_key = self._get_api_key()
        
        self.human_player_expected_actions: Dict[str, asyncio.Future] = {} # player_id -> Future for action
        self._game_lock = asyncio.Lock() #to prevent concurrent modifications to game state
        self._game_started_event = asyncio.Event()
        self._current_nominating_player_index: int = 0
        self._nomination_order: List[str] = []
        self._daily_chat_log: List[Dict[str,str]] = [] #to feed to agents for day decisions
        
        # initialize LLM-based storyteller with new system
        self.storyteller_agent = StorytellerAgent(
            api_key=self.api_key, 
            game_manager=self, 
            provider_type=self.llm_provider_type,
            model=self.llm_model
        )

    def _get_api_key(self) -> Optional[str]:
        """Get the appropriate API key based on provider type"""
        if self.llm_provider_type == "openai" or self.llm_provider_type == "auto":
            return os.getenv("OPENAI_API_KEY")
        elif self.llm_provider_type == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif self.llm_provider_type == "google":
            return os.getenv("GOOGLE_API_KEY")
        else:
            # Try to find any available API key
            return (os.getenv("OPENAI_API_KEY") or 
                   os.getenv("ANTHROPIC_API_KEY") or 
                   os.getenv("GOOGLE_API_KEY"))

    def is_game_running(self) -> bool:
        return self.grimoire is not None and self.rule_enforcer is not None and not self._game_started_event.is_set()

    def get_available_actions(self, player_id: str, action_type: str) -> List[str]:
        #return canonical list of what actions a given player can take for a specific action_type
        if action_type.startswith("NIGHT_ACTION"):
            return ["CHOOSE_ONE", "CHOOSE_TWO", "PASS"]
        elif action_type == "NOMINATION_CHOICE":
            return ["NOMINATE", "PASS_NOMINATION"]
        elif action_type == "VOTE_CHOICE":
            return ["VOTE_YES", "VOTE_NO"]
        elif action_type == "COMMUNICATION_CHOICE":
            return ["PUBLIC_CHAT", "PRIVATE_CHAT", "SILENT"]
        else:
            return []

    async def _get_ai_player_action(self, player_id: str, action_id: str, action_type: str, action_details: Dict[str, Any]):
        agent = self.agents.get(player_id)
        if not agent or not self.grimoire or not self.grimoire.is_player_alive(player_id):
            print(f"Cannot get action for {player_id}: Not an active AI agent.")
            # Store a None or error action if ST LLM is awaiting this player
            if action_id in self.pending_storyteller_actions and player_id in self.pending_storyteller_actions[action_id]["expected_players"]:
                 self.pending_storyteller_actions[action_id]["received_actions"][player_id] = {"action_type": "ERROR_NO_ACTION_POSSIBLE"}
            return

        # Prepare game state context for the agent (similar to how _collect_ai_night_actions used to do)
        # This might need to be slightly adapted based on what each agent.decide_X method expects.
        # For now, a generic public summary + action_details from ST LLM.
        game_state_summary_for_agent = self._get_public_game_state_summary(f"Storyteller request: {action_type}")
        # Add specific details from the ST LLM's request
        game_state_summary_for_agent.update(action_details)
        #inject canonical list of available actions for this request
        game_state_summary_for_agent["available_actions"] = self.get_available_actions(player_id, action_type)
        # Add full daily chat log as PlayerAgents expect it
        game_state_summary_for_agent["daily_chat_log"] = list(self._daily_chat_log)
        game_state_summary_for_agent["all_players_details"] = [
            {"id": p_id, "name": self.grimoire.game_state.get("player_names", {}).get(p_id, p_id), "is_alive": self.grimoire.is_player_alive(p_id)}
            for p_id in self.grimoire.players
        ]

        action_result = None
        print(f"Requesting '{action_type}' from AI {player_id} for action_id '{action_id}'...")

        try:
            if action_type.startswith("NIGHT_ACTION"): # handle any specific night action types
                # PlayerAgent.get_night_action needs alive_player_ids_with_names
                alive_players_with_names = [
                    {"id": pid, "name": self.grimoire.game_state.get("player_names", {}).get(pid, pid)}
                    for pid in self.grimoire.get_alive_players()
                ]
                action_result = await agent.get_night_action(game_state_summary_for_agent, alive_players_with_names)
            elif action_type == "NOMINATION_CHOICE":
                alive_players_with_names = [
                    {"id": pid, "name": self.grimoire.game_state.get("player_names", {}).get(pid, pid)}
                    for pid in self.grimoire.get_alive_players() if pid != player_id # Can't nominate self
                ]
                # decide_nomination expects: game_state, alive_player_ids_with_names, previous_nominations
                # previous_nominations might need to be passed in action_details by ST LLM or fetched from grimoire log
                previous_noms_today = [log["data"] for log in self.grimoire.game_log if log["event_type"] == "NOMINATION" and log["data"].get("day") == self.grimoire.day_number]
                chosen_nominee_id = await agent.decide_nomination(game_state_summary_for_agent, alive_players_with_names, previous_noms_today)
                if chosen_nominee_id:
                    action_result = {"action_type": "NOMINATE", "player_id": player_id, "nominated_player_id": chosen_nominee_id}
                else:
                    action_result = {"action_type": "PASS_NOMINATION", "player_id": player_id}
            elif action_type == "VOTE_CHOICE":
                nominee_id = action_details.get("nominee_id") # ST LLM must provide this in action_details
                nominee_name = self.grimoire.game_state.get("player_names",{}).get(nominee_id, nominee_id)
                if nominee_id:
                    vote_decision = await agent.decide_vote(game_state_summary_for_agent, nominee_id, nominee_name)
                    action_result = {"action_type": "CAST_VOTE", "player_id": player_id, "nominee_id": nominee_id, "vote": vote_decision}
                else:
                    print(f"VOTE_CHOICE requested for {player_id} but no nominee_id in action_details: {action_details}")
                    action_result = {"action_type": "ERROR_VOTE_NO_NOMINEE"}            
            # Add elif for CHAT_MESSAGE or other specific actions if ST LLM is to request them individually
            # For PUBLIC_CHAT, the _process_ai_communication_round might still be used, or ST LLM can prompt individuals.
            elif action_type == "COMMUNICATION_CHOICE": # For public/private chat decisions
                action_result = await agent.decide_communication(game_state_summary_for_agent)
            else:
                print(f"AI Action Warning: Unknown action_type '{action_type}' requested for {player_id}")
                action_result = {"action_type": "UNKNOWN_REQUEST", "original_request": action_type}

        except Exception as e:
            print(f"Error getting action {action_type} from AI {player_id}: {e}")
            action_result = {"action_type": f"ERROR_IN_AGENT_ACTION", "details": str(e)}
            import traceback
            traceback.print_exc()

        # Store the result in the pending_storyteller_actions structure
        if action_id in self.pending_storyteller_actions:
            if player_id in self.pending_storyteller_actions[action_id]["expected_players"]:
                self.pending_storyteller_actions[action_id]["received_actions"][player_id] = action_result
                print(f"AI action received from {player_id} for action_id '{action_id}': {action_result}")
            else:
                print(f"AI Action Warning: {player_id} responded for action_id '{action_id}', but was not in expected_players list: {self.pending_storyteller_actions[action_id]['expected_players']}")
        else:
            print(f"AI Action Warning: Received action for '{action_id}' from {player_id}, but this action_id is not pending.")

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
                # update AI agents' memory for key events
                for agent in self.agents.values():
                    etype = params["event_type"]
                    edata = params["data"]
                    if etype == "CHAT":
                        agent.update_memory("CHAT_MESSAGE", edata)
                    elif etype == "NOMINATION":
                        agent.update_memory("NOMINATION_EVENT", edata)
                    elif etype in ("VOTE_RESULT", "VOTING_RESULT"):  # ST LLM may use VOTING_RESULT
                        agent.update_memory("VOTE_RESULT", edata)
            else:
                print(f"LOG_EVENT Error: Missing grimoire, event_type, or data in params: {params}")

        elif command_type == "BROADCAST_MESSAGE":
            if "message_type" in params and "payload" in params:
                await self.broadcast_message(params["message_type"], params["payload"])
            else:
                print(f"BROADCAST_MESSAGE Error: Missing message_type or payload in params: {params}")

        elif command_type == "SEND_PERSONAL_MESSAGE":
            if "player_id" in params and "message_type" in params and "payload" in params:
                #deliver private-night info to ai agents' memory
                ai_id = params["player_id"]
                msg_type = params["message_type"]
                data = params["payload"]
                if ai_id in self.agents:
                    if msg_type == "PRIVATE_NIGHT_INFO":
                        self.agents[ai_id].update_memory("PRIVATE_NIGHT_INFO", data)
                    if msg_type == "PRIVATE_INFO_UPDATE":
                        # store full private info payload
                        self.agents[ai_id].memory["private_info"] = data
                await self.send_personal_message(ai_id, msg_type, data)
            else:
                print(f"SEND_PERSONAL_MESSAGE Error: Missing player_id, message_type, or payload: {params}")

        elif command_type == "UPDATE_PLAYER_STATUS":
            if self.grimoire and "player_id" in params and "status_key" in params and "value" in params:
                self.grimoire.update_status(params["player_id"], params["status_key"], params["value"])
            else:
                print(f"UPDATE_PLAYER_STATUS Error: Missing grimoire or params: {params}")

        elif command_type == "UPDATE_GRIMOIRE_VALUE":
            if self.grimoire and "key_path" in params and "value" in params:
                key_path = params["key_path"]
                value = params["value"]
                if len(key_path) == 1:
                    setattr(self.grimoire, key_path[0], value)
                    print(f"Set grimoire.{key_path[0]} = {value}")
                elif len(key_path) > 1:
                    obj = self.grimoire
                    for key_segment in key_path[:-1]:
                        if hasattr(obj, key_segment):
                            obj = getattr(obj, key_segment)
                        elif isinstance(obj, dict) and key_segment in obj:
                            obj = obj[key_segment]
                        else:
                            print(f"UPDATE_GRIMOIRE_VALUE Error: Invalid path {key_path}")
                            return
                    if hasattr(obj, key_path[-1]):
                         setattr(obj, key_path[-1], value)
                    elif isinstance(obj, dict):
                        obj[key_path[-1]] = value
                    else:
                        print(f"UPDATE_GRIMOIRE_VALUE Error: Cannot set value at path {key_path}")
                    print(f"Set grimoire path {key_path} = {value}")
            else:
                print(f"UPDATE_GRIMOIRE_VALUE Error: Missing grimoire or params: {params}")

        elif command_type == "EXECUTE_PLAYER":
            if self.rule_enforcer and "player_id" in params and "reason" in params:
                self.rule_enforcer._execute_player(params["player_id"], params["reason"])
                await self.broadcast_game_event(f"Player {self.grimoire.game_state.get('player_names',{}).get(params['player_id'], params['player_id'])} has died due to: {params['reason']}")
            else:
                print(f"EXECUTE_PLAYER Error: Missing rule_enforcer or params: {params}")
        
        elif command_type == "REQUEST_PLAYER_ACTION":
            player_id = params.get("player_id")
            action_id = params.get("action_id") # Crucial for tracking
            action_type = params.get("action_type")
            action_details = params.get("action_details", {})

            if not all([player_id, action_id, action_type]):
                print(f"REQUEST_PLAYER_ACTION Error: Missing player_id, action_id, or action_type in params: {params}")
                return

            print(f"Storyteller LLM requests action '{action_id}' of type '{action_type}' from player {player_id} with details: {action_details}")

            if player_id in self.agents: # It's an AI player
                # Create a task to get the AI's action. This will run in the background.
                # The result will be stored in self.pending_storyteller_actions by the helper itself.
                asyncio.create_task(self._get_ai_player_action(player_id, action_id, action_type, action_details))
                print(f"Task created for AI {player_id} to decide action '{action_id}'.")
            elif player_id in self.active_connections: # It's a human player (or at least connected client)
                # For human players, we need to send them a message prompting for their action.
                # Their response will come via `handle_incoming_message`.
                # We still need to record that we are expecting this action_id from them.
                if action_id not in self.pending_storyteller_actions:
                     print(f"REQUEST_PLAYER_ACTION Warning: action_id {action_id} was not pre-declared by AWAIT_PLAYER_RESPONSES for human {player_id}. This might be okay if ST LLM requests then awaits immediately.")
                     # It implies the ST LLM should issue AWAIT just after this for this player/action_id

                # Send a tailored message type based on action_type
                if action_type.startswith("NIGHT_ACTION"):  
                    await self.send_personal_message(player_id, "REQUEST_NIGHT_ACTION", {"action_id": action_id, **action_details})
                elif action_type == "NOMINATION_CHOICE":
                     await self.send_personal_message(player_id, "REQUEST_NOMINATION", {"action_id": action_id, **action_details})
                elif action_type == "VOTE_CHOICE":
                    await self.send_personal_message(player_id, "REQUEST_VOTE", {"action_id": action_id, **action_details})
                elif action_type == "COMMUNICATION_CHOICE":
                    await self.send_personal_message(player_id, "REQUEST_CHAT_DECISION", {"action_id": action_id, **action_details})
                else:
                    await self.send_personal_message(player_id, "REQUEST_GENERIC_ACTION", {"action_id": action_id, "action_type": action_type, **action_details})
                print(f"Sent '{action_type}' prompt to human player {player_id} for action_id '{action_id}'.")
            else:
                print(f"REQUEST_PLAYER_ACTION Error: Player {player_id} not found in agents or active_connections.")
                 # If ST LLM is awaiting this player, we should probably mark an error for them.
                if action_id in self.pending_storyteller_actions and player_id in self.pending_storyteller_actions[action_id]["expected_players"]:
                    self.pending_storyteller_actions[action_id]["received_actions"][player_id] = {"action_type": "ERROR_PLAYER_NOT_FOUND"}

        elif command_type == "AWAIT_PLAYER_RESPONSES":
            action_id = params.get("action_id")
            expected_players = params.get("expected_players", [])
            if action_id and expected_players:
                if action_id not in self.pending_storyteller_actions:
                    self.pending_storyteller_actions[action_id] = {"expected_players": expected_players, "received_actions": {}}
                else: # Merge expected players if action_id already exists (e.g. ST requests one by one then awaits all)
                    existing_expected = set(self.pending_storyteller_actions[action_id]["expected_players"])
                    new_expected = set(expected_players)
                    self.pending_storyteller_actions[action_id]["expected_players"] = list(existing_expected.union(new_expected))
                
                print(f"Game Loop: Now awaiting responses for action_id '{action_id}' from {self.pending_storyteller_actions[action_id]['expected_players']}")
                # The main game loop will see this action_id in pending_storyteller_actions and will continue to feed it to ST LLM
                # until all expected_players have their actions in received_actions for this action_id.
            else:
                 print(f"Game Loop Warning: AWAIT_PLAYER_RESPONSES command missing action_id or expected_players.")

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

    async def setup_new_game(self, player_ids_roles: Dict[str, str], human_player_ids: List[str] = [], player_names: Dict[str, str] = {}):
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

            # Separate state mutation commands from personal message commands to defer private info until agents exist
            state_commands = [cmd for cmd in setup_commands if cmd.get("command") != "SEND_PERSONAL_MESSAGE"]
            deferred_private_msgs = [cmd for cmd in setup_commands if cmd.get("command") == "SEND_PERSONAL_MESSAGE"]
            # First, apply all state-changing commands
            for command_obj in state_commands:
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
                
                # Set player name from provided mapping or use a better fallback
                if player_id not in player_display_names:
                    if player_id in player_names:
                        # Use the provided random name
                        player_display_names[player_id] = player_names[player_id]
                    else:
                        # Better fallback than generic "AI Player"
                        player_display_names[player_id] = f"Player {player_id[-1]}"  # Use last character of ID
                    self.grimoire.game_state.setdefault("player_names", {})[player_id] = player_display_names[player_id]

                # Populate role info for observer using grimoire's state
                actual_role_name = self.grimoire.get_player_role(player_id)
                display_name = player_display_names.get(player_id, player_id)
                all_player_role_info.append({"id": player_id, "name": display_name, "role": actual_role_name})

                # Initialize PlayerAgent objects
                if player_id not in human_player_ids:
                    alignment = self.grimoire.get_player_alignment(player_id)
                    if self.api_key:
                        self.agents[player_id] = PlayerAgent(
                            player_id, 
                            actual_role_name, 
                            alignment, 
                            api_key=self.api_key, 
                            game_manager=self,
                            provider_type=self.llm_provider_type,
                            model=self.llm_model
                        )
                        print(f"Initialized AI Agent for {display_name} as {actual_role_name} ({alignment}) using {self.llm_provider_type} provider")
                    else:
                        self.agents[player_id] = PlayerAgent(
                            player_id, 
                            actual_role_name, 
                            alignment, 
                            api_key=None, 
                            game_manager=self
                        )
                        print(f"Skipping LLM for AI agent {display_name} due to missing API key. Player will be passive.")
                    # populate initial private info into agent.memory
                    agent = self.agents[player_id]
                    role_details = get_role_details(actual_role_name)
                    private_payload = {
                        "role": actual_role_name,
                        "alignment": alignment,
                        "description": role_details.get("description", ""),
                        "clues": self.grimoire.get_private_clues(player_id)
                    }
                    # extra info: demon/minion/red_herring if applicable
                    if role_details.get("knows_demon", False):
                        demon_ids = [pid for pid, r in self.grimoire.roles.items() if r == "Imp"]
                        private_payload["known_demon"] = demon_ids[0] if demon_ids else None
                    if actual_role_name == "Imp":
                        minion_ids = [pid for pid, r in self.grimoire.roles.items() if get_role_details(r)["type"] == RoleType.MINION]
                        private_payload["known_minions"] = minion_ids
                        private_payload["demon_bluffs"] = getattr(self.grimoire, "demon_bluffs", [])
                    if role_details.get("has_red_herring", False):
                        private_payload["red_herring"] = getattr(self.grimoire, "fortune_teller_red_herring", None)
                    agent.memory["private_info"] = private_payload
                    # set game settings reference
                    agent.game_settings = self.settings
                else:
                     print(f"Player {display_name} ({actual_role_name}) is a human player.")
            # --- End of PlayerAgent setup ---
            
            # Replay deferred personal messages now that agents and clients are ready
            for command_obj in deferred_private_msgs:
                await self.execute_storyteller_command(command_obj)
            
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
                await self.active_connections[player_id].send_text(json.dumps({"type": message_type, "payload": payload, "playerId": player_id}))
            except json.JSONDecodeError as je:
                print(f"json encode error sending personal message to {player_id}: {je}")
            except KeyError as ke_send_personal:
                print(f"keyerror sending personal message to {player_id}: {repr(ke_send_personal)}")
            except Exception as e:
                print(f"error sending personal message to {player_id}: {type(e).__name__} - {e}")
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
            "clues": self.grimoire.get_private_clues(player_id),
        }
        #provide demon identification to roles that know the demon
        if role_details.get("knows_demon", False):
            demon_ids = [pid for pid, r in self.grimoire.roles.items() if r == "Imp"]
            if demon_ids:
                private_payload["known_demon"] = demon_ids[0]
        #provide minion identification and bluffs to the demon
        if role == "Imp":
            minion_ids = [pid for pid, r in self.grimoire.roles.items() if get_role_details(r)["type"] == RoleType.MINION]
            private_payload["known_minions"] = minion_ids
            private_payload["demon_bluffs"] = getattr(self.grimoire, "demon_bluffs", [])
        #provide fortune teller red herring if applicable
        if role_details.get("has_red_herring", False):
            private_payload["red_herring"] = getattr(self.grimoire, "fortune_teller_red_herring", None)
        #this method sends all private info updates to the player
        await self.send_personal_message(player_id, "PRIVATE_INFO_UPDATE", private_payload)

    async def run_game_loop(self):
        print("Game loop waiting for game to be fully started (Storyteller LLM driven)...")
        await self._game_started_event.wait()
        print("Game loop starting active processing (Storyteller LLM driven).")

        if not self.grimoire:
            print("Game loop exiting: Grimoire not initialized by Storyteller LLM.")
            return
        
        self.pending_storyteller_actions: Dict[str, Dict[str, Any]] = {}

        try:
            loop_iteration = 0
            while self.grimoire is not None and loop_iteration < 500:
                loop_iteration += 1
                print(f"--- Game Loop Iteration: {loop_iteration} ---")
                # allow AI players to chat during day phase
                if self.grimoire.current_phase == "DAY_CHAT":
                    game_state_summary = self._get_public_game_state_summary("AI communication round")
                    await self._process_ai_communication_round(game_state_summary)
                current_context_lines = []
                current_context_lines.append(f"EVENT: Start of game loop iteration {loop_iteration}.")
                current_context_lines.append(f"GRIMOIRE_PHASE: {self.grimoire.current_phase}")
                current_context_lines.append(f"GRIMOIRE_DAY: {self.grimoire.day_number}")
                grimoire_summary = {
                    "players": self.grimoire.players,
                    "roles": self.grimoire.roles,
                    "alignments": self.grimoire.alignments,
                    "statuses": self.grimoire.statuses,
                    "current_phase": self.grimoire.current_phase,
                    "day_number": self.grimoire.day_number,
                    "game_log_tail": self.grimoire.game_log[-5:]
                }
                current_context_lines.append(f"GRIMOIRE_SNAPSHOT: {json.dumps(grimoire_summary)}")
                if self._daily_chat_log:
                    current_context_lines.append(f"RECENT_PUBLIC_CHAT_LOG: {json.dumps(self._daily_chat_log[-10:])}")
                
                # Consolidate ALL submitted player actions for the ST LLM context
                # This will now also include actions submitted by humans via handle_incoming_message
                all_submitted_actions_for_st_llm = {}
                if self.pending_storyteller_actions:
                    for action_id, details in self.pending_storyteller_actions.items():
                        if details["received_actions"]:
                            all_submitted_actions_for_st_llm[action_id] = details["received_actions"]
                
                if all_submitted_actions_for_st_llm:
                    current_context_lines.append(f"PLAYER_ACTIONS_COLLECTED_SO_FAR: {json.dumps(all_submitted_actions_for_st_llm)}")
                
                # Also explicitly state what is still pending, so LLM knows what it's waiting for vs what it received.
                if self.pending_storyteller_actions:
                     current_context_lines.append(f"PENDING_STORYTELLER_ACTIONS_OVERVIEW: {json.dumps({aid: list(data['received_actions'].keys()) for aid, data in self.pending_storyteller_actions.items()}) }")

                print(f"Requesting commands from Storyteller LLM... Current Phase: {self.grimoire.current_phase}, Day: {self.grimoire.day_number}")
                storyteller_commands = await self.storyteller_agent.generate_commands(current_context_lines)
                print(f"Received {len(storyteller_commands)} commands from Storyteller LLM: {storyteller_commands}")

                should_await_player_responses_this_cycle = False
                active_await_action_ids = set() # Track action_ids we are actively awaiting this cycle

                for command_obj in storyteller_commands:
                    await self.execute_storyteller_command(command_obj)
                    if command_obj.get("command") == "AWAIT_PLAYER_RESPONSES":
                        should_await_player_responses_this_cycle = True
                        action_id = command_obj["params"].get("action_id")
                        if action_id: active_await_action_ids.add(action_id)
                    
                    if command_obj.get("command") == "END_GAME":
                        print("Game loop ending due to END_GAME command from Storyteller.")
                        return
                
                if not self.grimoire:
                    print("Game loop ending as Grimoire is None.")
                    break

                # After executing ST LLM commands, check if we need to pause for player inputs
                if should_await_player_responses_this_cycle:
                    print(f"Game Loop: Pausing to collect player responses for action_ids: {active_await_action_ids} as per Storyteller LLM directive.")
                    # The actual collection for AIs is triggered by REQUEST_PLAYER_ACTION creating tasks.
                    # For humans, REQUEST_PLAYER_ACTION sends them a message.
                    # We now need to wait until expected actions are filled or a timeout occurs.
                    # This loop iteration will end, and the next one will provide the updated pending_storyteller_actions to the ST LLM.
                    
                    # Check if all expected actions for *any* of the active_await_action_ids are complete
                    all_awaited_actions_complete = True
                    for action_id in list(active_await_action_ids): # Iterate over a copy if we modify dict
                        if action_id in self.pending_storyteller_actions:
                            pending_action_details = self.pending_storyteller_actions[action_id]
                            expected = set(pending_action_details["expected_players"])
                            received = set(pending_action_details["received_actions"].keys())
                            if not expected.issubset(received):
                                all_awaited_actions_complete = False
                                print(f"Still waiting for actions from {list(expected - received)} for action_id '{action_id}'.")
                                break # No need to check other action_ids if one is still pending
                            else:
                                print(f"All actions for action_id '{action_id}' have been received.")
                                # OPTIONAL: ST LLM could explicitly command to clear a pending action once resolved.
                                # If not, it will keep seeing it in context. For now, leave it for ST LLM to manage.
                                # For example, ST LLM might say: LOG_EVENT (action X resolved), then doesn't AWAIT X again.
                        else:
                            print(f"Warning: Game loop was awaiting action_id '{action_id}' but it's no longer in pending_storyteller_actions.")
                    
                    if not all_awaited_actions_complete:
                        await asyncio.sleep(1) # Wait before re-querying ST LLM if still waiting for players
                        continue # Go to next loop iteration to provide updated context (with any newly collected actions)
                    else:
                        print("All actively awaited player responses received for this cycle. Proceeding to next ST LLM query without forced delay.")
                
                await asyncio.sleep(0.1) # Short pause if not awaiting

        except asyncio.CancelledError:
            print("Game loop was cancelled.")
        except Exception as e:
            print(f"Critical error in game loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._game_started_event.clear()
            print("Game loop ended.")
            self.pending_storyteller_actions = {}

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
                # update all AI memories with public chat
                for agent in self.agents.values():
                    agent.update_memory("CHAT_MESSAGE", chat_event)
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

    async def handle_incoming_message(self, player_id: str, raw_data: str):
        try:
            msg = json.loads(raw_data)
        except json.JSONDecodeError:
            print(f"failed to decode message from {player_id}: {raw_data}")
            return

        msg_type = msg.get("type")
        payload = msg.get("payload")

        if msg_type == "REQUEST_GAME_START":
            # start a default 10-AI player game with random roles
            num_players = 10
            default_player_ids = [f"AI_Player_{i}" for i in range(1, num_players + 1)]
            
            # Generate random names for the AI players
            random_names = generate_random_player_names(num_players)
            
            # assign random roles to AI players
            available_roles = list(ROLES_DATA.keys())
            random.shuffle(available_roles)
            # take as many roles as players
            selected_roles = available_roles[:len(default_player_ids)]
            player_ids_roles = {pid: selected_roles[i] for i, pid in enumerate(default_player_ids)}
            
            # Create a mapping of player IDs to random names
            player_names_mapping = {pid: random_names[i] for i, pid in enumerate(default_player_ids)}
            
            await self.setup_new_game(player_ids_roles, human_player_ids=[], player_names=player_names_mapping)

        elif msg_type == "CHAT_MESSAGE":
            # record and broadcast public chat from human
            text = payload.get("text") if isinstance(payload, dict) else payload
            chat_event = {"sender": player_id, "sender_name": self.grimoire.game_state.get("player_names", {}).get(player_id, player_id), "text": text, "timestamp": "#timestamp#"}
            self._daily_chat_log.append(chat_event)
            await self.broadcast_message("CHAT_MESSAGE", chat_event)
            # update AI memories for human chat
            for agent in self.agents.values():
                agent.update_memory("CHAT_MESSAGE", chat_event)

        elif msg_type in ("REQUEST_NIGHT_ACTION_RESPONSE", "REQUEST_NOMINATION", "REQUEST_VOTE", "REQUEST_CHAT_DECISION", "REQUEST_GENERIC_ACTION"):
            # human response to Storyteller action prompt
            action_id = payload.get("action_id") if isinstance(payload, dict) else None
            if action_id and action_id in self.pending_storyteller_actions:
                self.pending_storyteller_actions[action_id]["received_actions"][player_id] = payload
                print(f"received human action for {player_id}, action_id {action_id}: {payload}")

        elif msg_type == "REQUEST_MEMORY":
            requested = payload.get("player_id")
            if requested in self.agents:
                # Get individual player perspective instead of raw memory
                player_perspective = self._get_player_perspective(requested)
                await self.send_personal_message(player_id, "MEMORY_UPDATE", {"player_id": requested, "perspective": player_perspective})
            else:
                print(f"REQUEST_MEMORY for unknown player {requested}")

        elif msg_type == "REQUEST_SETTINGS":
            # send current settings to the requesting client
            await self.send_personal_message(player_id, "SETTINGS_UPDATE", self.settings.to_dict())

        elif msg_type == "UPDATE_SETTINGS":
            # update settings from client
            if payload and isinstance(payload, dict):
                self.settings.update_from_dict(payload)
                print(f"settings updated by {player_id}: {self.settings.to_dict()}")
                # apply settings to existing agents if game is running
                if self.agents:
                    for agent in self.agents.values():
                        if hasattr(agent, 'memory_curator_enabled'):
                            agent.memory_curator_enabled = self.settings.memory_curator_enabled
                        #update agent references to settings
                        agent.game_settings = self.settings
                await self.send_personal_message(player_id, "INFO", "settings updated successfully")
            else:
                await self.send_personal_message(player_id, "ERROR", "invalid settings payload")

        else:
            print(f"unknown message type from {player_id}: {msg_type}")

    def _get_player_perspective(self, player_id: str) -> Dict[str, Any]:
        """Get a formatted view of the game from a specific player's perspective"""
        if player_id not in self.agents:
            return {"error": f"Player {player_id} not found"}
        
        agent = self.agents[player_id]
        player_info = self.grimoire.players.get(player_id, {})
        
        perspective = {
            "player_info": {
                "id": player_id,
                "name": player_info.get("name", player_id),
                "role": agent.role,
                "alignment": agent.alignment,
                "status": agent.status
            },
            "private_information": {
                "storyteller_told_me": agent.memory.get("private_info"),
                "private_clues": agent.memory.get("private_clues", []),
                "role_ability": agent.role_details.get("description", "No description available")
            },
            "my_actions": {
                "votes_cast": agent.memory.get("votes", []),
                "nominations_made": agent.memory.get("nominations", []),
                "actions_taken": agent.memory.get("actions_taken", [])
            },
            "my_observations": {
                "important_events": agent.memory.get("important_events", []),
                "observations": agent.memory.get("observations", [])
            },
            "communications": {
                "public_chat_log": agent.memory.get("public_chat_log", []),
                "private_conversations": self._format_private_conversations(agent.memory.get("private_chat_logs", {}))
            },
            "game_context": {
                "current_phase": self.grimoire.current_phase if self.grimoire else "Unknown",
                "day_number": self.grimoire.day_number if self.grimoire else 0,
                "players_alive": len([p for p in self.grimoire.players if self.grimoire.statuses.get(p, {}).get("alive", True)]) if self.grimoire else 0,
                "total_players": len(self.grimoire.players) if self.grimoire else 0
            }
        }
        
        return perspective
    
    def _format_private_conversations(self, private_chat_logs: Dict[str, List]) -> Dict[str, Any]:
        """Format private conversations for display"""
        formatted_convos = {}
        for partner_id, messages in private_chat_logs.items():
            partner_name = self.grimoire.players.get(partner_id, {}).get("name", partner_id) if self.grimoire else partner_id
            formatted_convos[partner_name] = {
                "partner_id": partner_id,
                "messages": messages
            }
        return formatted_convos

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

#add endpoint to save game logs chronologically in a json file
@app.get("/save_logs")
async def save_logs():
    if not game_manager.grimoire:
        return {"error":"no game in progress to save logs"}
    
    # Collect all comprehensive game data
    comprehensive_logs = {
        "metadata": {
            "save_timestamp": datetime.utcnow().isoformat(),
            "game_phase": game_manager.grimoire.current_phase,
            "day_number": game_manager.grimoire.day_number,
            "players_count": len(game_manager.grimoire.players),
            "game_started": game_manager._game_started_event.is_set()
        },
        "game_log": sorted(game_manager.grimoire.game_log, key=lambda e: e["timestamp"]),
        "storyteller_log": game_manager.grimoire.storyteller_log,
        "daily_chat_log": game_manager._daily_chat_log,
        "game_state": {
            "players": game_manager.grimoire.players,
            "roles": game_manager.grimoire.roles,
            "alignments": game_manager.grimoire.alignments,
            "statuses": game_manager.grimoire.statuses,
            "demon_bluffs": game_manager.grimoire.demon_bluffs,
            "fortune_teller_red_herring_player_id": game_manager.grimoire.fortune_teller_red_herring_player_id,
            "current_demon_player_id": game_manager.grimoire.current_demon_player_id,
            "baron_added_outsiders": game_manager.grimoire.baron_added_outsiders,
            "private_clues": game_manager.grimoire.private_clues,
            "general_game_state": game_manager.grimoire.game_state
        },
        "agent_memories": {},
        "storyteller_agent_data": {
            "prompts": getattr(game_manager.storyteller_agent, 'debug_prompts', []),
            "responses": getattr(game_manager.storyteller_agent, 'debug_responses', [])
        },
        "pending_actions": getattr(game_manager, 'pending_storyteller_actions', {}),
        "nomination_state": {
            "current_nominating_player_index": game_manager._current_nominating_player_index,
            "nomination_order": game_manager._nomination_order
        }
    }
    
    # Collect agent memories and debug data
    for player_id, agent in game_manager.agents.items():
        agent_data = {
            "memory": agent.memory,
            "role": agent.role,
            "alignment": agent.alignment,
            "status": agent.status,
            "debug_prompts": getattr(agent, 'debug_prompts', []),
            "debug_responses": getattr(agent, 'debug_responses', [])
        }
        comprehensive_logs["agent_memories"][player_id] = agent_data
    
    # Create logs directory if not exists
    os.makedirs("logs", exist_ok=True)
    filename = datetime.utcnow().strftime("comprehensive_game_log_%Y%m%d_%H%M%S.json")
    filepath = os.path.join("logs", filename)
    
    with open(filepath, "w") as f:
        json.dump(comprehensive_logs, f, indent=2, default=str)
    
    return {"message": "comprehensive logs saved successfully", "filepath": filepath}

@app.get("/debug/bot_info")
async def get_bot_debug_info():
    """Get detailed debugging information for all bots"""
    if not game_manager.grimoire:
        return {"error": "no game in progress"}
    
    bot_info = {
        "storyteller": {
            "type": "storyteller",
            "status": "active",
            "memory": {
                "game_state": {
                    "current_phase": game_manager.grimoire.current_phase,
                    "day_number": game_manager.grimoire.day_number,
                    "players_alive": len([p for p in game_manager.grimoire.players if game_manager.grimoire.statuses.get(p, {}).get("alive", True)]),
                    "total_players": len(game_manager.grimoire.players)
                },
                "recent_actions": game_manager.grimoire.game_log[-5:] if game_manager.grimoire.game_log else [],
                "pending_actions": getattr(game_manager, 'pending_storyteller_actions', {})
            },
            "stats": {
                "total_decisions": len(game_manager.grimoire.storyteller_log),
                "game_events_processed": len(game_manager.grimoire.game_log)
            }
        },
        "players": {}
    }
    
    # Add player bot information
    for player_id, agent in game_manager.agents.items():
        player_info = game_manager.grimoire.players.get(player_id, {})
        bot_info["players"][player_id] = {
            "type": "player",
            "name": player_info.get("name", player_id),
            "role": agent.role,
            "alignment": agent.alignment,
            "status": agent.status,
            "memory": {
                "private_info": agent.memory.get("private_info"),
                "important_events": agent.memory.get("important_events", []),
                "private_clues": agent.memory.get("private_clues", []),
                "chat_messages_count": len(agent.memory.get("public_chat_log", [])),
                "private_conversations": len(agent.memory.get("private_chat_logs", {}))
            },
            "stats": {
                "actions_taken": len(agent.memory.get("actions_taken", [])),
                "observations_made": len(agent.memory.get("observations", [])),
                "votes_cast": len(agent.memory.get("votes", []))
            }
        }
    
    return bot_info

@app.get("/settings")
async def get_settings():
    """get current game settings"""
    return game_manager.settings.to_dict()

@app.post("/settings")
async def update_settings(settings_update: dict):
    """update game settings"""
    try:
        game_manager.settings.update_from_dict(settings_update)
        #apply settings to existing agents if game is running
        if game_manager.agents:
            for agent in game_manager.agents.values():
                agent.game_settings = game_manager.settings
        return {"success": True, "settings": game_manager.settings.to_dict()}
    except Exception as e:
        return {"error": f"failed to update settings: {str(e)}"}

def generate_random_player_names(count: int) -> List[str]:
    """Generate a list of random player names for AI players."""
    first_names = [
        "Alex", "Blake", "Casey", "Drew", "Emery", "Finley", "Gray", "Harper", 
        "Indigo", "Jordan", "Kai", "Lane", "Morgan", "Nova", "Oakley", "Parker",
        "Quinn", "River", "Sage", "Taylor", "Uma", "Vale", "Wren", "Xander",
        "Yuki", "Zara", "Avery", "Bryce", "Cameron", "Dakota", "Ellis", "Frankie",
        "Gale", "Hayden", "Iris", "Jules", "Kendall", "Logan", "Marley", "Nico",
        "Orion", "Peyton", "Reese", "Skyler", "Tatum", "Unity", "Vega", "Winter",
        "Xylo", "Yarrow", "Zen", "Aspen", "Bay", "Cedar", "Dove", "Echo",
        "Fern", "Grove", "Haven", "Ivy", "Jade", "Knox", "Lark", "Moss",
        "North", "Ocean", "Pine", "Quest", "Rain", "Storm", "True", "Vale"
    ]
    
    last_names = [
        "Stone", "Rivers", "Woods", "Fields", "Brooks", "Cross", "Vale", "Hill",
        "Fox", "Wolf", "Bear", "Hawk", "Raven", "Swift", "Bright", "Sharp",
        "Wild", "Free", "Bold", "Wise", "Kind", "True", "Fair", "Strong",
        "Grace", "Hope", "Joy", "Peace", "Dawn", "Moon", "Star", "Sun",
        "Storm", "Rain", "Snow", "Wind", "Fire", "Earth", "Sky", "Sea",
        "North", "South", "East", "West", "Blue", "Green", "Gold", "Silver",
        "Black", "White", "Gray", "Red", "Rose", "Sage", "Pine", "Oak",
        "Ash", "Elm", "Birch", "Cedar", "Maple", "Willow", "Hazel", "Rowan"
    ]
    
    # Shuffle both lists to ensure randomness
    random.shuffle(first_names)
    random.shuffle(last_names)
    
    names = []
    for i in range(count):
        first = first_names[i % len(first_names)]
        last = last_names[i % len(last_names)]
        names.append(f"{first} {last}")
    
    return names

if __name__ == "__main__":
    print("Starting game server on http://localhost:8000")
    print("Open http://localhost:8000 in a browser to observe.")
    print("Ensure GOOGLE_API_KEY environment variable is set for AI players.")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True) 