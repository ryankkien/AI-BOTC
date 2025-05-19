import os
import json
import google.generativeai as genai
from typing import Any

class StorytellerAgent:
    def __init__(self, api_key: str = None, game_manager: Any = None):
        self.game_manager = game_manager
        # configure the LLM for narrative duties
        effective_api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if effective_api_key:
            genai.configure(api_key=effective_api_key)
            self.llm = genai.GenerativeModel('gemini-1.5-flash-latest')
        else:
            print("warning: GOOGLE_API_KEY not set, storyteller llm unavailable")
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
- {"command": "REQUEST_PLAYER_ACTION", "params": {"action_id": "string_unique_id_for_this_request", "player_id": "string", "action_type": "string_e.g_NIGHT_CHOICE_FORTUNE_TELLER_or_VOTE_ON_NOMINEE", "action_details": {object_context_for_player_e.g_nominee_info_or_list_of_targets}}}
- {"command": "AWAIT_PLAYER_RESPONSES", "params": {"action_id": "string_unique_id_matching_REQUEST_PLAYER_ACTION", "expected_players": ["player_id1", "player_id2"]}} # Pauses for player inputs for the given action_id
- {"command": "END_GAME", "params": {"winner": "string", "reason": "string"}}

CORE RULES TO FOLLOW (summarized from your full instructions):

PREPARATION
- Input: player_ids_roles map.
- Action: Shuffle seating order (if not given). Store in Grimoire.
- Output Commands:
    - LOG_EVENT (GAME_SETUP: seating order)
    - LOG_EVENT (PHASE_CHANGE: FIRST_NIGHT, day_number=0)
    - Other initial setup commands (e.g., demon bluffs)

FIRST NIGHT
- Context: Grimoire state after PREPARATION.
- Action: Determine and send all first-night info (Minions see Demon; Demon sees Minions & bluffs; Washerwoman, Librarian, etc. get their specific clues).
- Output Commands:
    - SEND_PERSONAL_MESSAGE (for each piece of private info)
    - LOG_EVENT (ABILITY_USE for each info sent)
    - LOG_EVENT (FIRST_NIGHT_ABILITIES completed)
    - LOG_EVENT (PHASE_CHANGE: DAY_CHAT, day_number=1)
    - BROADCAST_MESSAGE (GAME_EVENT: "Day 1 begins...")

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
    - If not over: LOG_EVENT (PHASE_CHANGE: DAY_CHAT, increment day_number) & broadcasts.

VICTORY & END GAME
- Context: Result of CHECK_VICTORY_CONDITIONS.
- Action: Announce winner.
- Output Commands:
    - BROADCAST_MESSAGE (GAME_END: winner, reason)

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

        if self.game_manager:
            await self.game_manager.broadcast_message("LLM_DEBUG", {"agent": "storyteller", "prompt": prompt})

        try:
            response = await self.llm.generate_content_async(prompt)
            if self.game_manager:
                await self.game_manager.broadcast_message("LLM_DEBUG", {"agent": "storyteller", "response": response.text})
            raw_response_text = response.text.strip()
            # print(f"--- STORYTELLER RAW RESPONSE START ---\\n{raw_response_text}\\n--- STORYTELLER RAW RESPONSE END ---") # For debugging
            
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