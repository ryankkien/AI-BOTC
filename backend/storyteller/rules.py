#backend/storyteller/rules.py
import random
from typing import List, Dict, Any, Optional, Tuple
from .grimoire import Grimoire
from .roles import ROLES_DATA, RoleType, RoleAlignment, get_role_details, get_all_roles

class RuleEnforcer:
    def __init__(self, grimoire: Grimoire, game_manager=None): #game_manager for sending messages
        self.grimoire = grimoire
        self.game_manager = game_manager #to send private info during setup

    async def assign_roles_and_setup_game(self, requested_player_count: int, specific_roles: Optional[List[str]] = None):
        """Assigns roles to players, sets up initial game state in the Grimoire."""
        #this function is called by GameManager.setup_new_game AFTER players are added to grimoire with roles
        #this function will primarily establish seating order, demon bluffs, red herring, etc.
        
        all_player_ids = list(self.grimoire.players) #get players from grimoire
        random.shuffle(all_player_ids) #establish seating order
        self.grimoire.players = all_player_ids #overwrite with shuffled order
        self.grimoire.log_event("GAME_SETUP", {"event": "Seating order established", "order": all_player_ids})

        #demon bluffs - select 3 non-demon, non-minion roles that are not in play
        #todo: handle case where not enough bluff roles available (e.g. high player count, many specific roles)
        in_play_roles = list(self.grimoire.roles.values())
        potential_bluffs = [r for r in get_all_roles() if r not in in_play_roles and 
                            (get_role_details(r)["type"] == RoleType.TOWNSFOLK or 
                             get_role_details(r)["type"] == RoleType.OUTSIDER)]
        if len(potential_bluffs) >= 3:
            self.grimoire.demon_bluffs = random.sample(potential_bluffs, 3)
        else:
            self.grimoire.demon_bluffs = random.sample(potential_bluffs, len(potential_bluffs)) #take what we can
            self.grimoire.storyteller_log.append(f"Warning: Not enough bluff roles. Selected {len(self.grimoire.demon_bluffs)}")
        self.grimoire.log_event("GAME_SETUP", {"event": "Demon bluffs selected", "bluffs": self.grimoire.demon_bluffs})

        #fortune teller red herring - pick one non-demon player who is not the fortune teller
        fortune_tellers = self.grimoire.get_player_ids_by_role("Fortune Teller")
        if fortune_tellers:
            ft_player_id = fortune_tellers[0] #assume only one FT for now
            demons = []
            for p_id in all_player_ids: # Iterate through all player IDs
                role_name = self.grimoire.get_player_role(p_id)
                if role_name:
                    role_details = get_role_details(role_name)
                    if role_details and role_details["alignment"] == RoleAlignment.EVIL:
                        demons.append(p_id)
            potential_red_herrings = [pid for pid in all_player_ids if pid != ft_player_id and pid not in demons]
            if potential_red_herrings:
                self.grimoire.fortune_teller_red_herring = random.choice(potential_red_herrings)
                self.grimoire.log_event("GAME_SETUP", {"event": "Fortune Teller red herring selected", "player_id": self.grimoire.fortune_teller_red_herring})
            else:
                 self.grimoire.storyteller_log.append("Warning: No valid red herring found for Fortune Teller.")
        
        self.grimoire.current_phase = "FIRST_NIGHT"
        self.grimoire.day_number = 0 #day 0 is first night
        self.grimoire.log_event("PHASE_CHANGE", {"new_phase": "FIRST_NIGHT"})

        #resolve first night info and abilities
        await self._resolve_first_night_info()

    #this function is now called from GameManager during its setup_new_game method
    # def start_game(self, player_count: int, roles_list: List[str]):
    #     #assign roles, set up first night, etc.
    #     #this will involve updating the grimoire
    #     self.grimoire.log_event("GAME_SETUP", {"player_count": player_count, "roles_assigned": True})
    #     #... more setup logic, like seating order, demon bluffs, FT red herring is done in assign_roles_and_setup_game
    #     self.grimoire.current_phase = "FIRST_NIGHT"
    #     self.grimoire.log_event("PHASE_CHANGE", {"new_phase": "FIRST_NIGHT"})
    #     #call first night abilities
    #     await self._resolve_first_night_info()

    async def _resolve_first_night_info(self):
        """Handles information distribution for the first night."""
        self.grimoire.log_event("FIRST_NIGHT_ABILITIES", {"status": "processing"})

        demon_ids = []
        for player_id, role_name in self.grimoire.roles.items():
            role_details = get_role_details(role_name)
            if role_details and role_details["type"] == RoleType.DEMON:
                demon_ids.append(player_id)

        minion_ids = []
        for player_id, role_name in self.grimoire.roles.items():
            role_details = get_role_details(role_name)
            if role_details and role_details["type"] == RoleType.MINION:
                minion_ids.append(player_id)
        
        #demon learns minions and 3 bluff roles
        if demon_ids and self.game_manager: #check game_manager exists for sending messages
            demon_id = demon_ids[0]
            minion_names = [self.grimoire.game_state.get("player_names", {}).get(mid, mid) for mid in minion_ids]
            private_update_payload = {
                "known_minions": minion_names or ["No Minions in play"],
                "demon_bluffs": self.grimoire.demon_bluffs or ["No bluffs available"]
            }
            await self.game_manager.send_personal_message(demon_id, "PRIVATE_NIGHT_INFO", private_update_payload)
            self.grimoire.log_event("ABILITY_USE", {"role": "Imp", "player_id": demon_id, "action": "Received minion/bluff info"})

        #minions learn the demon
        if demon_ids and minion_ids and self.game_manager:
            demon_name = self.grimoire.game_state.get("player_names", {}).get(demon_ids[0], demon_ids[0])
            for minion_id in minion_ids:
                role_details = get_role_details(self.grimoire.get_player_role(minion_id))
                if role_details.get("knows_demon"):
                    private_update_payload = {"known_demon": demon_name}
                    await self.game_manager.send_personal_message(minion_id, "PRIVATE_NIGHT_INFO", private_update_payload)
                    self.grimoire.log_event("ABILITY_USE", {"role": self.grimoire.get_player_role(minion_id), "player_id": minion_id, "action": f"Learned Demon is {demon_name}"})

        #first night for specific roles (Washerwoman, Librarian, Investigator, Chef, Empath, Fortune Teller)
        #these often involve the Storyteller providing info based on game setup
        #example: Washerwoman
        washerwomen = self.grimoire.get_player_ids_by_role("Washerwoman")
        if washerwomen and self.game_manager:
            ww_id = washerwomen[0]
            # Washerwoman: Learns a Townsfolk role and one of two players.
            # One is that Townsfolk, the other is not (or is also that TF if 2 are in play and picked)
            townsfolk_in_play = [pid for pid, role in self.grimoire.roles.items() if get_role_details(role)["type"] == RoleType.TOWNSFOLK and pid != ww_id]
            if townsfolk_in_play:
                target_townsfolk_role = get_role_details(self.grimoire.get_player_role(random.choice(townsfolk_in_play)))["name"]
                
                #select 2 players, one of whom IS the target_townsfolk_role
                players_with_target_role = [pid for pid in townsfolk_in_play if self.grimoire.get_player_role(pid) == target_townsfolk_role]
                other_players = [pid for pid in self.grimoire.players if pid != ww_id and pid not in players_with_target_role]

                if players_with_target_role:
                    p1_actual_tf = random.choice(players_with_target_role)
                    p2_other = random.choice(other_players) if other_players else p1_actual_tf #edge case, pick same if no other
                    
                    pair_to_show = random.sample([self.grimoire.game_state.get("player_names",{}).get(p1_actual_tf, p1_actual_tf), 
                                               self.grimoire.game_state.get("player_names",{}).get(p2_other, p2_other)], 2)
                    
                    info_text = f"One of these two players ({pair_to_show[0]}, {pair_to_show[1]}) is the {target_townsfolk_role}."
                    await self.game_manager.send_personal_message(ww_id, "PRIVATE_NIGHT_INFO", {"clues":[{"night":0, "text": info_text}]})
                    self.grimoire.log_event("ABILITY_USE", {"role": "Washerwoman", "player_id": ww_id, "info_provided": info_text})
            else:
                self.grimoire.storyteller_log.append("WW: No other townsfolk in play to give info about.")
                await self.game_manager.send_personal_message(ww_id, "PRIVATE_NIGHT_INFO", {"clues":[{"night":0, "text": "No specific townsfolk information available this game."}]})

        #todo: Implement similar logic for Librarian, Investigator, Chef, Empath (0 evil neighbors), Fortune Teller (initial ping + red herring info)
        #for Fortune Teller: needs to pick two players, or be given info about their pick and red herring.
        #the player_agent.py for FT makes a choice, this method should resolve it.
        #for now, the logic is that Storyteller *provides* info, not resolves choices for first night info roles.

        self.grimoire.log_event("FIRST_NIGHT_ABILITIES", {"status": "completed"})
        #after first night info, the game doesn't automatically transition to day.
        #the game_loop in main.py should handle this transition after a pause or all info sent.
        #for now, let's assume first night is quick and transition it here for simplicity of testing structure
        #self.transition_to_day() #moved to game loop

    def transition_to_day(self):
        self.grimoire.day_number += 1
        self.grimoire.current_phase = "DAY_CHAT"
        #reset day-specific statuses
        for player_id in self.grimoire.players:
            if self.grimoire.is_player_alive(player_id):
                self.grimoire.update_status(player_id, "nominated_today", False)
                #butler might affect this
                self.grimoire.update_status(player_id, "can_nominate", True) 
        self.grimoire.log_event("PHASE_CHANGE", {"new_phase": "DAY_CHAT", "day": self.grimoire.day_number})
        #broadcast phase change to players (done by game_manager typically)

    def process_nomination(self, nominator_id: str, nominee_id: str):
        self.grimoire.storyteller_log.append(f"Processing nomination: {nominator_id} nominates {nominee_id}")
        if not self.grimoire.is_player_alive(nominator_id) or not self.grimoire.is_player_alive(nominee_id):
            self.grimoire.log_event("INVALID_NOMINATION", {"nominator": nominator_id, "nominee": nominee_id, "reason": "Player not alive"})
            return
        
        if nominator_id == nominee_id:
            self.grimoire.log_event("INVALID_NOMINATION", {"nominator": nominator_id, "nominee": nominee_id, "reason": "Cannot nominate self"})
            return

        if not self.grimoire.get_player_status(nominator_id, "can_nominate"):
            self.grimoire.log_event("INVALID_NOMINATION", {"nominator": nominator_id, "nominee": nominee_id, "reason": "Nominator cannot nominate now (e.g. Butler effect, or already nominated)"})
            return

        #virgin rule
        nominee_role = self.grimoire.get_player_role(nominee_id)
        nominator_role_type = get_role_details(self.grimoire.get_player_role(nominator_id))["type"]
        if nominee_role == "Virgin" and not self.grimoire.get_player_status(nominee_id, "used_virgin_ability") and nominator_role_type == RoleType.TOWNSFOLK:
            self.grimoire.log_event("ABILITY_TRIGGER", {"role": "Virgin", "player_id": nominee_id, "by_player": nominator_id})
            self.grimoire.update_status(nominee_id, "used_virgin_ability", True)
            self._execute_player(nominator_id, "Executed by Virgin ability")
            #nomination does not proceed to vote
            #day continues, or if this was the only nominator, might end day voting phase
            return #execution happens, phase doesn't change to VOTING yet

        self.grimoire.log_event("NOMINATION", {"nominator": nominator_id, "nominee": nominee_id})
        self.grimoire.update_status(nominator_id, "can_nominate", False) #typically can only nominate once
        self.grimoire.current_phase = "VOTING"
        self.grimoire.game_state["current_nominee_id"] = nominee_id
        self.grimoire.log_event("PHASE_CHANGE", {"new_phase": "VOTING", "nominee": nominee_id, "nominator": nominator_id})
        #initiate vote (handled by game_manager by broadcasting new state)

    def process_votes(self, votes: Dict[str, bool]): #player_id -> True (for nominee) / False (abstain/against)
        if not self.grimoire.current_phase == "VOTING" or "current_nominee_id" not in self.grimoire.game_state:
            self.grimoire.storyteller_log.append("Error: process_votes called at wrong time.")
            return

        nominee_id = self.grimoire.game_state["current_nominee_id"]
        self.grimoire.log_event("VOTING_START", {"nominee": nominee_id, "votes_cast": votes})

        alive_voters_count = len([pid for pid in self.grimoire.get_alive_players() if self.grimoire.get_player_status(pid, "can_vote") is not False]) #todo: add can_vote status for Butler
        votes_for = sum(1 for voter_id, vote_choice in votes.items() if vote_choice and self.grimoire.is_player_alive(voter_id))
        
        outcome = "NO_EXECUTION_TIE"
        executed_player_id = None

        if votes_for > alive_voters_count / 2:
            self.grimoire.log_event("VOTING_RESULT", {"nominee": nominee_id, "outcome": "EXECUTED", "votes": votes, "votes_for": votes_for, "total_voters": alive_voters_count})
            self._execute_player(nominee_id, "Executed by majority vote")
            executed_player_id = nominee_id
            outcome = "EXECUTED"
            #check for Saint execution loss condition
            if self.grimoire.get_player_role(nominee_id) == "Saint":
                self.grimoire.log_event("GAME_END_CONDITION", {"reason": "Saint executed", "winner": RoleAlignment.EVIL.value})
                #game_manager should handle actual game end broadcast
                #for now, just log it. Victory check will pick it up.
        elif votes_for == alive_voters_count / 2 and alive_voters_count > 0: #exact tie on even number of voters
             self.grimoire.log_event("VOTING_RESULT", {"nominee": nominee_id, "outcome": "NO_EXECUTION_TIE", "votes": votes, "votes_for": votes_for, "total_voters": alive_voters_count})
             #storyteller may break ties with a ghost vote, or it's just no execution
             #TB rules: tie means no execution
             outcome = "NO_EXECUTION_TIE"
        else: #less than majority
            self.grimoire.log_event("VOTING_RESULT", {"nominee": nominee_id, "outcome": "NO_EXECUTION_MAJORITY", "votes": votes, "votes_for": votes_for, "total_voters": alive_voters_count})
            outcome = "NO_EXECUTION_MAJORITY"

        #cleanup after vote
        del self.grimoire.game_state["current_nominee_id"]
        #transition to night or next nomination/day chat
        #this logic depends on if executions are limited per day etc.
        #for TB, usually one execution then night, unless Mayor or no execution.
        if executed_player_id:
            self.transition_to_night()
        else: #no execution, back to day chat for more nominations or end day
            #todo: add logic for max nominations or if all players passed
            self.grimoire.current_phase = "DAY_CHAT" 
            self.grimoire.log_event("PHASE_CHANGE", {"new_phase": "DAY_CHAT", "day": self.grimoire.day_number, "reason": "No execution from vote"})

    def _execute_player(self, player_id: str, reason: str):
        if self.grimoire.is_player_alive(player_id):
            self.grimoire.update_status(player_id, "alive", False)
            self.grimoire.log_event("DEATH", {"player_id": player_id, "role_at_death": self.grimoire.get_player_role(player_id), "reason": reason})
            # Undertaker might get info now (or at start of night phase)
        else:
            self.grimoire.storyteller_log.append(f"Attempted to execute already dead player {player_id}")

    def transition_to_night(self):
        self.grimoire.current_phase = "NIGHT"
        self.grimoire.log_event("PHASE_CHANGE", {"new_phase": "NIGHT", "day": self.grimoire.day_number})
        #self._resolve_night_abilities() #this will be called by game loop

    async def resolve_night_actions(self, night_actions: Dict[str, Any]): # player_id -> action_details
        """Process all collected night actions in script order."""
        self.grimoire.log_event("NIGHT_ABILITIES", {"status": "processing", "actions_received": night_actions})
        #script order: Monk, Poisoner, ... Demon kill ... then Spy, Empath, Undertaker
        #this is a simplified placeholder for the script order
        
        #1. Protections (Monk)
        for player_id, action in night_actions.items():
            if self.grimoire.get_player_role(player_id) == "Monk" and action.get("action_type") == "Monk":
                target_id = action.get("targets", [None])[0]
                if target_id and self.grimoire.is_player_alive(target_id) and target_id != player_id:
                    self.grimoire.update_status(target_id, "protected_by_monk", True)
                    self.grimoire.log_event("ABILITY_USE", {"role": "Monk", "player_id": player_id, "target": target_id, "result":"protected"})
                    if self.game_manager: await self.game_manager.send_personal_message(player_id, "PRIVATE_NIGHT_INFO", {"clues":[{"night":self.grimoire.day_number, "text": f"You protected {target_id}."}]})

        #2. Poisoning (Poisoner)
        #... similar logic ...

        #3. Demon Kill (Imp)
        demon_kill_target = None
        demon_id = None
        for player_id, action in night_actions.items():
            if self.grimoire.get_player_role(player_id) == "Imp" and action.get("action_type") == "Imp":
                target_id = action.get("targets", [None])[0]
                demon_id = player_id
                if target_id: #imp can target self
                    #soldier is safe from demon
                    if self.grimoire.get_player_role(target_id) == "Soldier":
                        self.grimoire.log_event("ABILITY_INTERACTION", {"killer_role": "Imp", "target_role": "Soldier", "result": "Soldier safe"})
                        if self.game_manager: await self.game_manager.send_personal_message(player_id, "PRIVATE_NIGHT_INFO", {"clues":[{"night":self.grimoire.day_number, "text": f"Your target {target_id} was a Soldier and survived."}]})
                    elif self.grimoire.get_player_status(target_id, "protected_by_monk"):
                        self.grimoire.log_event("ABILITY_INTERACTION", {"killer_role": "Imp", "target_role": self.grimoire.get_player_role(target_id), "protector":"Monk", "result": "Target protected"})
                        if self.game_manager: await self.game_manager.send_personal_message(player_id, "PRIVATE_NIGHT_INFO", {"clues":[{"night":self.grimoire.day_number, "text": f"Your target {target_id} was protected by the Monk and survived."}]})
                    else:
                        demon_kill_target = target_id
                break #only one demon kill
        
        if demon_kill_target and demon_id:
            if demon_kill_target == demon_id: #imp suicide
                self.grimoire.log_event("DEATH", {"player_id": demon_kill_target, "role_at_death": "Imp", "reason": "Imp suicide"})
                self.grimoire.update_status(demon_kill_target, "alive", False)
                #handle scarlet woman promotion
                scarlet_women = self.grimoire.get_player_ids_by_role("Scarlet Woman")
                if scarlet_women and len(self.grimoire.get_alive_players()) >= 4: #5+ players alive BEFORE this death means 4+ after for SW
                    sw_id = scarlet_women[0]
                    if self.grimoire.is_player_alive(sw_id):
                        self.grimoire.roles[sw_id] = "Imp" #promoted
                        self.grimoire.log_event("ROLE_CHANGE", {"player_id": sw_id, "old_role": "Scarlet Woman", "new_role": "Imp"})
                        if self.game_manager: await self.game_manager.send_personal_message(sw_id, "PRIVATE_NIGHT_INFO", {"clues":[{"night":self.grimoire.day_number, "text": "The Imp killed themselves. You are now the Imp!"}]})
                        #new Imp does not act this night
                else: #no SW or not enough players, evil loses if no other demons
                    if not self.grimoire.get_player_ids_by_alignment(RoleAlignment.EVIL.value): #check if any evil players left
                         self.grimoire.log_event("GAME_END_CONDITION", {"reason": "Imp suicide, no valid promotion, no demons left.", "winner": RoleAlignment.GOOD.value})
            else:
                self._execute_player(demon_kill_target, "Killed by the Demon")
                if self.game_manager: await self.game_manager.send_personal_message(demon_id, "PRIVATE_NIGHT_INFO", {"clues":[{"night":self.grimoire.day_number, "text": f"You killed {demon_kill_target}."}]})

        #4. Information gathering (Empath, Spy, Undertaker, Ravenkeeper if died)
        #... logic for these roles to get their info ...
        #example Empath:
        empaths = self.grimoire.get_player_ids_by_role("Empath")
        if empaths and self.game_manager:
            for empath_id in empaths:
                if not self.grimoire.is_player_alive(empath_id): continue
                # Empath needs seating order to find neighbors
                player_idx = self.grimoire.players.index(empath_id)
                num_players = len(self.grimoire.players)
                left_neighbor_id = self.grimoire.players[(player_idx - 1 + num_players) % num_players]
                right_neighbor_id = self.grimoire.players[(player_idx + 1) % num_players]
                evil_neighbors = 0
                if self.grimoire.is_player_alive(left_neighbor_id) and self.grimoire.get_player_alignment(left_neighbor_id) == RoleAlignment.EVIL.value:
                    evil_neighbors +=1
                if self.grimoire.is_player_alive(right_neighbor_id) and self.grimoire.get_player_alignment(right_neighbor_id) == RoleAlignment.EVIL.value:
                    evil_neighbors +=1
                #handle drunk/poisoned for Empath - they get false info
                #for now, assume correct info
                await self.game_manager.send_personal_message(empath_id, "PRIVATE_NIGHT_INFO", {"clues":[{"night":self.grimoire.day_number, "text": f"You sensed {evil_neighbors} evil neighbors."}]})
                self.grimoire.log_event("ABILITY_USE", {"role": "Empath", "player_id": empath_id, "result": f"{evil_neighbors} evil neighbors"})

        self.grimoire.log_event("NIGHT_ABILITIES", {"status": "completed"})
        self._check_for_deaths_and_game_end() #this will update statuses based on demon kill etc.
        #transition to day is handled by game loop after night resolution

    def _check_for_deaths_and_game_end(self):
        #identify deaths from demon kill, execution, etc. (already logged by _execute_player or demon kill logic)
        #update player statuses in grimoire (already done)
        #check victory conditions
        game_over, winner = self.check_victory_conditions()
        if game_over:
            self.grimoire.log_event("GAME_OVER", {"winner": winner, "reason": "Victory condition met during check"})
            #the game_manager running the loop will pick this up and end the game.

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