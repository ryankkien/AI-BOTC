#backend/storyteller/rules.py
# NOTE: legacy rule enforcer logic now largely deprecated; game logic is driven by StorytellerAgent LLM
import random
from typing import List, Dict, Any, Optional, Tuple
from .grimoire import Grimoire
from .roles import ROLES_DATA, RoleType, RoleAlignment, get_role_details, get_all_roles

class RuleEnforcer:
    def __init__(self, grimoire: Grimoire, game_manager=None): #game_manager for sending messages
        self.grimoire = grimoire
        self.game_manager = game_manager #to send private info during setup

    async def assign_roles_and_setup_game(self, requested_player_count: int, specific_roles: Optional[List[str]] = None):
        # moved to LLM-driven StorytellerAgent; old setup logic retained below for reference
        pass
        # """
        # all_player_ids = list(self.grimoire.players)
        # random.shuffle(all_player_ids)
        # self.grimoire.players = all_player_ids
        # self.grimoire.log_event("GAME_SETUP", {"event": "Seating order established", "order": all_player_ids})
        # ... (remaining original setup code) ...
        # await self._resolve_first_night_info()
        # """

    async def _resolve_first_night_info(self):
        # moved to LLM-driven StorytellerAgent; old night-info logic retained below for reference
        pass
        # """
        # self.grimoire.log_event("FIRST_NIGHT_ABILITIES", {"status": "processing"})
        # demon_ids = [...]
        # ... (remaining original first-night info code) ...
        # self.grimoire.log_event("FIRST_NIGHT_ABILITIES", {"status": "completed"})
        # """

    def transition_to_day(self):
        # moved to LLM-driven StorytellerAgent
        pass
        # """
        # self.grimoire.day_number += 1
        # self.grimoire.current_phase = "DAY_CHAT"
        # ... reset statuses ...
        # self.grimoire.log_event("PHASE_CHANGE", {"new_phase": "DAY_CHAT", "day": self.grimoire.day_number})
        # """

    def process_nomination(self, nominator_id: str, nominee_id: str):
        # moved to LLM-driven StorytellerAgent
        pass
        # """
        # original nomination validation and logics...
        # """

    def process_votes(self, votes: Dict[str, bool]):
        # moved to LLM-driven StorytellerAgent
        pass
        # """
        # nominee_id = self.grimoire.game_state.get("current_nominee_id")
        # ... tally votes and call _execute_player or transition_to_day ...
        # """

    def transition_to_night(self):
        # moved to LLM-driven StorytellerAgent
        pass
        # """
        # self.grimoire.current_phase = "NIGHT"
        # self.grimoire.log_event("PHASE_CHANGE", {"new_phase": "NIGHT", "day": self.grimoire.day_number})
        # """

    async def resolve_night_actions(self, night_actions: Dict[str, Any]):
        # moved to LLM-driven StorytellerAgent; original resolution logic retained below
        pass
        # """
        # self.grimoire.log_event("NIGHT_ABILITIES", {"status": "processing", "actions_received": night_actions})
        # ... Monk, Poisoner, Imp kill, Empath, Spy, Undertaker logic ...
        # self.grimoire.log_event("NIGHT_ABILITIES", {"status": "completed"})
        # self._check_for_deaths_and_game_end()
        # """

    def _check_for_deaths_and_game_end(self):
        # moved to LLM-driven StorytellerAgent; original end-game checks below
        pass
        # """
        # game_over, winner = self.check_victory_conditions()
        # if game_over: self.grimoire.log_event("GAME_OVER", {"winner": winner, "reason": ...})
        # """

    def _execute_player(self, player_id: str, reason: str):
        if self.grimoire.is_player_alive(player_id):
            self.grimoire.update_status(player_id, "alive", False)
            self.grimoire.log_event("DEATH", {"player_id": player_id, "role_at_death": self.grimoire.get_player_role(player_id), "reason": reason})
            # Undertaker might get info now (or at start of night phase)
        else:
            self.grimoire.storyteller_log.append(f"Attempted to execute already dead player {player_id}")

    def check_victory_conditions(self) -> Tuple[bool, Optional[str]]:
        alive_players = self.grimoire.get_alive_players()
        alive_player_count = len(alive_players)

        if alive_player_count == 0: #should not happen if checks are right
            return True, "No one (Draw)" 

        #good win: demon executed (or killed by slayer)
        #check if any demon is alive
        demons_in_game = self.grimoire.get_player_ids_by_role("Imp") #extend if more demons
        any_demon_alive = any(self.grimoire.is_player_alive(d_id) for d_id in demons_in_game)
        
        if not any_demon_alive and demons_in_game: #make sure a demon was in play
            self.grimoire.storyteller_log.append("Victory Check: Demon is dead. Good wins.")
            return True, RoleAlignment.GOOD.value

        #evil win: only two players left and one is a demon (or demon + minion)
        if alive_player_count <= 2:
            if any_demon_alive: #if demon is one of the last 2 (or 1)
                self.grimoire.storyteller_log.append(f"Victory Check: {alive_player_count} players left, Demon alive. Evil wins.")
                return True, RoleAlignment.EVIL.value
            else: #e.g. two good players left, this implies demon died earlier
                self.grimoire.storyteller_log.append(f"Victory Check: {alive_player_count} players left, Demon NOT alive. Good wins (should have been caught earlier).")
                return True, RoleAlignment.GOOD.value #this case should have been caught by demon death

        #evil win: saint executed (This is checked in process_votes, but can double check here)
        #this requires tracking if a saint was executed. Game log would have it.
        for event in reversed(self.grimoire.game_log):
            if event["event_type"] == "DEATH" and event["data"].get("reason") == "Executed by majority vote":
                if self.grimoire.get_player_role(event["data"]["player_id"]) == "Saint":
                    self.grimoire.storyteller_log.append("Victory Check: Saint was executed. Evil wins.")
                    return True, RoleAlignment.EVIL.value
            if event["event_type"] == "GAME_END_CONDITION" and event["data"].get("reason") == "Saint executed": #already logged
                 return True, RoleAlignment.EVIL.value

        #mayor win condition: If only 3 players live and no execution occurs, good wins.
        #this needs to be checked at the end of a day phase where voting led to no execution.
        #the process_votes method transitions to DAY_CHAT if no execution. The game loop would then call this.
        if self.grimoire.current_phase == "DAY_CHAT" and alive_player_count == 3:
            #check if an execution occurred this day (more complex, needs tracking day's executions)
            #for now, if we are in DAY_CHAT, 3 alive, AND the *previous* phase was VOTING resulting in no execution...
            #This is tricky. Simpler: Mayor ability might need a flag in grimoire or a specific check after vote resolution.
            mayor_ids = self.grimoire.get_player_ids_by_role("Mayor")
            if any(self.grimoire.is_player_alive(m_id) for m_id in mayor_ids):
                #check if previous phase was voting and resulted in no execution
                last_event = self.grimoire.game_log[-1] if self.grimoire.game_log else None
                if (
                    last_event and 
                    last_event["event_type"] == "PHASE_CHANGE" and 
                    last_event["data"]["new_phase"] == "DAY_CHAT" and 
                    last_event["data"].get("reason") == "No execution from vote"
                ):
                   self.grimoire.storyteller_log.append("Victory Check: Mayor condition met. Good wins.")
                   return True, RoleAlignment.GOOD.value

        return False, None #no victory condition met 

    async def _send_private_night_info(self, player_id: str, payload: Dict[str, Any]):
        # record private clue in grimoire then send to player
        self.grimoire.add_private_clue(player_id, payload)
        if self.game_manager:
            await self.game_manager.send_personal_message(player_id, "PRIVATE_NIGHT_INFO", payload)

    def get_player_knowledge(self, player_id: str) -> List[Any]:
        """Return all private clues that a player has received so far."""
        return self.grimoire.get_private_clues(player_id) 