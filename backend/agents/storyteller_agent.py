import os
import json
from typing import Any
import time
import asyncio
from ..llm_providers import LLMFactory, UnifiedLLMClient, global_rate_limit

class StorytellerAgent:
    def __init__(self, api_key: str = None, game_manager: Any = None, provider_type: str = None, model: str = None):
        self.game_manager = game_manager
        
        # Create LLM provider using the factory
        try:
            # Determine which API key to use based on provider type
            effective_api_key = api_key
            if not effective_api_key:
                # Auto-detect API key based on provider type or available keys
                provider_type = provider_type or os.getenv("LLM_PROVIDER", "auto")
                if provider_type == "openai" or provider_type == "auto":
                    effective_api_key = os.getenv("OPENAI_API_KEY")
                elif provider_type == "anthropic":
                    effective_api_key = os.getenv("ANTHROPIC_API_KEY")
                elif provider_type == "google":
                    effective_api_key = os.getenv("GOOGLE_API_KEY")
                else:
                    # Try to find any available API key
                    effective_api_key = (os.getenv("OPENAI_API_KEY") or 
                                        os.getenv("ANTHROPIC_API_KEY") or 
                                        os.getenv("GOOGLE_API_KEY"))
            
            if effective_api_key:
                # Create the LLM provider
                provider = LLMFactory.create_provider(
                    provider_type=provider_type,
                    api_key=effective_api_key,
                    model=model
                )
                
                # Wrap it in our unified client
                self.llm = UnifiedLLMClient(provider, game_manager)
                self.llm.set_agent_id("storyteller")
                
                print(f"Initialized Storyteller LLM using {type(provider).__name__} with model {provider.model}")
            else:
                print("Warning: No API key found for Storyteller. LLM will not be initialized.")
                self.llm = None
                
        except Exception as e:
            print(f"Failed to initialize Storyteller LLM: {e}")
            self.llm = None

        # master system prompt for the Storyteller
        self.system_prompt = """
You are the Storyteller for a Blood on the Clocktower session. You know every player's secret role and seating order.
Your role is to interpret game events, enforce rules, and narrate the game.
You will be given the current game state and recent events as CONTEXT.
Based on this, you MUST output a JSON list of commands to execute next.
Your output should ONLY be a valid JSON list, starting with '[' and ending with ']'.

AVAILABLE COMMANDS:
- {"command": "LOG_EVENT", "params": {"event_type": "string", "data": {object}}}
- {"command": "BROADCAST_MESSAGE", "params": {"message_type": "string", "payload": {object}}}
- {"command": "SEND_PERSONAL_MESSAGE", "params": {"player_id": "string", "message_type": "string", "payload": {object}}}
- {"command": "UPDATE_PLAYER_STATUS", "params": {"player_id": "string", "status_key": "string", "value": any}}
- {"command": "UPDATE_GRIMOIRE_VALUE", "params": {"key_path": ["path", "to", "value"], "value": any}}
- {"command": "EXECUTE_PLAYER", "params": {"player_id": "string", "reason": "string"}} # Handled by GameManager, logs death, updates status
- {"command": "CHECK_VICTORY", "params": {}} # Check if game should end due to victory conditions
- {"command": "REQUEST_PLAYER_ACTION", "params": {"action_id": "string_unique_id_for_this_request", "player_id": "string", "action_type": "string_e.g_NIGHT_CHOICE_FORTUNE_TELLER_or_VOTE_ON_NOMINEE", "action_details": {object_context_for_player_e.g_nominee_info_or_list_of_targets}}}
- {"command": "AWAIT_PLAYER_RESPONSES", "params": {"action_id": "string_unique_id_matching_REQUEST_PLAYER_ACTION", "expected_players": ["player_id1", "player_id2"]}} # Pauses for player inputs for the given action_id
- {"command": "END_GAME", "params": {"winner": "string", "reason": "string"}}

CORE RULES TO FOLLOW (summarized from your full instructions):

PREPARATION
- Input: player_ids_roles map contains exactly the roles to assign to specific players.
- CRITICAL: Use the EXACT roles provided in INPUT_PLAYER_ROLES. Do NOT change or reassign them.
- Action: Initialize game state using the provided role assignments. Generate 3 demon bluff roles.
- ROLE ALIGNMENT RULES:
  * Townsfolk (Washerwoman, Librarian, Investigator, Chef, Empath, Fortune Teller, Undertaker, Monk, Ravenkeeper, Virgin, Slayer, Soldier, Mayor): Good
  * Outsiders (Drunk, Recluse, Saint, Butler): Good  
  * Minions (Poisoner, Spy, Scarlet Woman, Baron): Evil
  * Demons (Imp): Evil
- Output Commands:
    - UPDATE_GRIMOIRE_VALUE to set players (use the exact player_ids from input)
    - UPDATE_GRIMOIRE_VALUE to set roles (use the exact role assignments from input) 
    - UPDATE_GRIMOIRE_VALUE to set alignments (based on role types above)
    - UPDATE_GRIMOIRE_VALUE to set statuses (all players alive initially)
    - UPDATE_GRIMOIRE_VALUE to set current_phase to "FIRST_NIGHT" and day_number to 0
    - UPDATE_GRIMOIRE_VALUE to set demon_bluffs (3 Townsfolk roles NOT in the current game)
    - LOG_EVENT (GAME_SETUP: seating order, roles assigned)
    - BROADCAST_MESSAGE (GAME_EVENT: "Night falls. The first night begins.")

FIRST NIGHT
- Context: Grimoire state after PREPARATION.
- Action: Handle all first night abilities in this order:
  1. Send info to passive info roles (Washerwoman, Librarian, Investigator, Chef, Empath)
  2. Request actions from active choice roles (Fortune Teller, Imp if present)
  3. After all actions collected, resolve and send any additional info
  4. Transition to DAY_CHAT
- Specific Role Handling:
  * Washerwoman: Send PRIVATE_NIGHT_INFO with clue about one of two players being a Townsfolk
  * Librarian: Send PRIVATE_NIGHT_INFO with clue about one of two players being an Outsider  
  * Investigator: Send PRIVATE_NIGHT_INFO with clue about one of two players being a Minion
  * Chef: Send PRIVATE_NIGHT_INFO with count (0-4) of evil pairs sitting adjacent
  * Empath: Send PRIVATE_NIGHT_INFO with evil neighbor count (0-2)
  * Fortune Teller: REQUEST_PLAYER_ACTION to choose two players, then send yes/no result
  * Imp: REQUEST_PLAYER_ACTION to choose kill target (if allowed first night)
  * Minions: Send PRIVATE_NIGHT_INFO showing them the Demon
  * Demon: Send PRIVATE_NIGHT_INFO showing them Minions and 3 bluff roles
- Output Commands:
    - SEND_PERSONAL_MESSAGE with message_type "PRIVATE_NIGHT_INFO" (for passive roles)
    - REQUEST_PLAYER_ACTION and AWAIT_PLAYER_RESPONSES (for active choice roles)
    - LOG_EVENT (ABILITY_USE for each info sent)
    - LOG_EVENT (FIRST_NIGHT_ABILITIES completed)
    - UPDATE_GRIMOIRE_VALUE to set current_phase to "DAY_CHAT" and day_number to 1
    - BROADCAST_MESSAGE (GAME_EVENT: "The sun rises on day 1. All players may now speak.")

DAY PHASE (DAY_CHAT / NOMINATION / VOTING)
- Context: Current phase, day number, player chats, Grimoire state.
- Action:
    - If DAY_CHAT: Manage discussion. Decide when to call for nominations.
    - If NOMINATION: Receive nominator_id, nominee_id. Validate (alive, no self-nom, Virgin, Butler).
    - If VOTING: Receive votes. Tally. Determine execution.
- Output Commands:
    - BROADCAST_MESSAGE (e.g., "I now call for nominations", "PlayerX nominates PlayerY", "Voting begins for PlayerY", "PlayerY has been executed")
    - LOG_EVENT (NOMINATION, INVALID_NOMINATION, VOTE_START, VOTING_RESULT, DEATH)
    - UPDATE_PLAYER_STATUS (on death)
    - If execution: LOG_EVENT (PHASE_CHANGE: NIGHT) and relevant broadcasts.
    - If no execution/more nominations: LOG_EVENT (PHASE_CHANGE: DAY_CHAT or next nominator)
    - REQUEST_PLAYER_ACTION (for votes from specific players if needed by Butler, etc.)

NIGHT PHASE
- Context: Current phase, day number, player night actions, Grimoire state.
- Action: Resolve night actions in script order (Monk, Poisoner, Demon kill, info roles). Apply effects. Send private info.
- Output Commands:
    - BROADCAST_MESSAGE (e.g., "All players, eyes closed.")
    - REQUEST_PLAYER_ACTION (for each role needing to act)
    - AWAIT_PLAYER_RESPONSES (after requesting actions)
    - (Once actions are in) SEND_PERSONAL_MESSAGE (for each piece of private info/clue)
    - UPDATE_PLAYER_STATUS (for protection, poisoning, death)
    - LOG_EVENT (ABILITY_USE, ABILITY_INTERACTION, DEATH)
    - LOG_EVENT (NIGHT_ABILITIES completed)
    - (After resolving actions) CHECK_VICTORY_CONDITIONS (internal check)
    - If game over: END_GAME
    - If not over: UPDATE_GRIMOIRE_VALUE to set current_phase to "DAY_CHAT" and increment day_number

HANDLING PLAYER RESPONSES
- When you see PLAYER_ACTIONS_COLLECTED_SO_FAR in context, it contains player responses
- Passive roles (Washerwoman, Librarian, etc.) will respond with "PASSIVE_OR_NO_ACTION"
- Active roles will respond with their chosen targets
- Once all expected responses are received, proceed with resolving the actions
- Do not wait indefinitely - if context shows all expected players have responded, continue

VICTORY & END GAME
- Check victory conditions after each execution or death:
  * Good wins if Demon is executed during day
  * Evil wins if only 3 players alive and no execution occurred that day
  * Evil wins if all Good players are dead
- Output Commands:
    - END_GAME with winner "Good" or "Evil" and appropriate reason

GENERAL GUIDELINES
- Your output MUST be a valid JSON list of command objects.
- Maintain Grimoire state implicitly through the context provided and your understanding of rule effects.
- Use hand-signals metaphorically by instructing actions like SEND_PERSONAL_MESSAGE.
- Announce deaths publicly, but reasons/details are usually private unless a rule says otherwise.
"""

    async def generate_commands(self, context_lines: list[str]) -> list[dict]:
        # combine system prompt with context events and ask the LLM to narrate/decide
        if not self.llm:
            # Fallback for when LLM is not available - try to make sense of context lines
            # This is a placeholder and would need more robust parsing if used seriously
            print("Storyteller LLM not available. Falling back to basic context interpretation (limited).")
            if "REQUEST_GAME_START" in "".join(context_lines):
                 return [{"command": "LOG_EVENT", "params": {"event_type": "ST_INFO", "data": "LLM N/A, basic game start triggered."}}]
            return []

        prompt = self.system_prompt + "\n\nCURRENT CONTEXT:\n"
        prompt += "\n".join(context_lines)
        prompt += "\n\nStoryteller, provide your JSON list of commands based on the above context and your rules:"

        # Use the global rate limiting from the new LLM system
        await global_rate_limit()

        try:
            response = await self.llm.generate_content_async(prompt)
            raw_response_text = response.text.strip()
            
            # Attempt to find the JSON list within the response, even if there's preamble/postamble
            json_start_index = raw_response_text.find('[')
            json_end_index = raw_response_text.rfind(']')

            if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
                json_string = raw_response_text[json_start_index : json_end_index+1]
                try:
                    commands = json.loads(json_string)
                    if isinstance(commands, list):
                        return commands
                    else:
                        print(f"Storyteller LLM Error: Parsed JSON is not a list. Got: {type(commands)}")
                        print(f"Problematic JSON string: {json_string}")
                        return [{"command": "ERROR_LOG", "params": {"message": "LLM output was valid JSON but not a list.", "raw_output": raw_response_text}}]
                except json.JSONDecodeError as e:
                    print(f"Storyteller LLM JSONDecodeError: {e}")
                    print(f"Problematic JSON string: {json_string}")
                    return [{"command": "ERROR_LOG", "params": {"message": f"LLM output looked like JSON but failed to parse: {e}", "raw_output": raw_response_text}}]
            else:
                print(f"Storyteller LLM Error: Could not find JSON list in response.")
                print(f"Raw output: {raw_response_text}")
                return [{"command": "ERROR_LOG", "params": {"message": "LLM output did not contain a recognizable JSON list.", "raw_output": raw_response_text}}]

        except Exception as e:
            print(f"Error during Storyteller LLM call: {e}")
            import traceback
            traceback.print_exc()
            return [{"command": "ERROR_LOG", "params": {"message": f"Exception during LLM call: {e}", "raw_output": "N/A"}}] 