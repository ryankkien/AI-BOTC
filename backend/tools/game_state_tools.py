"""
Game state query tools for AI agents to reduce prompt sizes.
Instead of embedding all game information in prompts, agents can call these tools as needed.
"""

from typing import Dict, List, Any, Optional
from ..storyteller.grimoire import Grimoire
from ..storyteller.roles import get_role_details, RoleDescription

class GameStateTools:
    """Tools for querying game state information on demand"""
    
    def __init__(self, grimoire: Grimoire):
        self.grimoire = grimoire
    
    def get_alive_players(self) -> List[Dict[str, str]]:
        """Get list of currently alive players with their names"""
        alive_players = []
        for player_id in self.grimoire.players:
            if self.grimoire.is_player_alive(player_id):
                name = self.grimoire.game_state.get("player_names", {}).get(player_id, player_id)
                alive_players.append({
                    "id": player_id,
                    "name": name
                })
        return alive_players
    
    def get_dead_players(self) -> List[Dict[str, Any]]:
        """Get list of dead players with death information"""
        dead_players = []
        for player_id in self.grimoire.players:
            if not self.grimoire.is_player_alive(player_id):
                name = self.grimoire.game_state.get("player_names", {}).get(player_id, player_id)
                # Find death event in game log
                death_info = self._find_death_info(player_id)
                dead_players.append({
                    "id": player_id,
                    "name": name,
                    "death_day": death_info.get("day", "unknown"),
                    "death_reason": death_info.get("reason", "unknown")
                })
        return dead_players
    
    def _find_death_info(self, player_id: str) -> Dict[str, Any]:
        """Find death information from game log"""
        for event in reversed(self.grimoire.game_log):
            if event.get("event_type") == "DEATH" and event.get("data", {}).get("player_id") == player_id:
                return {
                    "day": event.get("data", {}).get("day", "unknown"),
                    "reason": event.get("data", {}).get("reason", "unknown")
                }
        return {}
    
    def get_current_phase(self) -> Dict[str, Any]:
        """Get current game phase and day"""
        return {
            "phase": self.grimoire.current_phase,
            "day": self.grimoire.day_number
        }
    
    def get_player_neighbors(self, player_id: str) -> Dict[str, Dict[str, str]]:
        """Get the players sitting adjacent to a given player"""
        if player_id not in self.grimoire.players:
            return {"error": f"Player {player_id} not found"}
        
        player_index = self.grimoire.players.index(player_id)
        num_players = len(self.grimoire.players)
        
        left_index = (player_index - 1) % num_players
        right_index = (player_index + 1) % num_players
        
        left_player = self.grimoire.players[left_index]
        right_player = self.grimoire.players[right_index]
        
        return {
            "left": {
                "id": left_player,
                "name": self.grimoire.game_state.get("player_names", {}).get(left_player, left_player),
                "alive": self.grimoire.is_player_alive(left_player)
            },
            "right": {
                "id": right_player,
                "name": self.grimoire.game_state.get("player_names", {}).get(right_player, right_player),
                "alive": self.grimoire.is_player_alive(right_player)
            }
        }
    
    def get_nomination_history(self, day: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get nomination history for a specific day or current day"""
        if day is None:
            day = self.grimoire.day_number
            
        nominations = []
        for event in self.grimoire.game_log:
            if event.get("event_type") == "NOMINATION" and event.get("data", {}).get("day") == day:
                data = event.get("data", {})
                nominations.append({
                    "nominator": data.get("nominator"),
                    "nominee": data.get("nominee"),
                    "votes_for": data.get("votes_for", []),
                    "votes_against": data.get("votes_against", []),
                    "executed": data.get("executed", False)
                })
        return nominations
    
    def get_voting_history(self, player_id: str) -> List[Dict[str, Any]]:
        """Get voting history for a specific player"""
        votes = []
        for event in self.grimoire.game_log:
            if event.get("event_type") == "VOTING_RESULT":
                data = event.get("data", {})
                if player_id in data.get("votes_for", []):
                    votes.append({
                        "day": data.get("day"),
                        "nominee": data.get("nominee"),
                        "vote": "yes"
                    })
                elif player_id in data.get("votes_against", []):
                    votes.append({
                        "day": data.get("day"), 
                        "nominee": data.get("nominee"),
                        "vote": "no"
                    })
        return votes
    
    def get_role_ability_info(self, role_name: str) -> Dict[str, Any]:
        """Get detailed ability information for a role"""
        role_details = get_role_details(role_name)
        if not role_details:
            return {"error": f"Role {role_name} not found"}
            
        return {
            "role": role_name,
            "team": role_details["team"].value,
            "alignment": role_details["alignment"].value,
            "description": role_details["description"],
            "first_night_ability": role_details.get("first_night_ability", False),
            "other_night_ability": role_details.get("other_night_ability", False),
            "trigger_on_death": role_details.get("trigger_on_death", False),
            "modifies_setup": role_details.get("modifies_setup", False)
        }
    
    def get_public_executions(self) -> List[Dict[str, Any]]:
        """Get list of all public executions that have occurred"""
        executions = []
        for event in self.grimoire.game_log:
            if event.get("event_type") == "DEATH" and event.get("data", {}).get("reason") == "executed":
                data = event.get("data", {})
                player_id = data.get("player_id")
                executions.append({
                    "player_id": player_id,
                    "player_name": self.grimoire.game_state.get("player_names", {}).get(player_id, player_id),
                    "day": data.get("day"),
                    "votes_for": data.get("votes_for", []),
                    "votes_against": data.get("votes_against", [])
                })
        return executions
    
    def check_player_status(self, player_id: str, status_key: str) -> Any:
        """Check a specific status for a player (e.g., 'poisoned', 'protected_by_monk')"""
        if player_id not in self.grimoire.statuses:
            return {"error": f"Player {player_id} not found"}
            
        return self.grimoire.statuses[player_id].get(status_key, False)
    
    def get_seating_order(self) -> List[Dict[str, str]]:
        """Get the complete seating order with player names"""
        seating = []
        for i, player_id in enumerate(self.grimoire.players):
            seating.append({
                "position": i,
                "id": player_id,
                "name": self.grimoire.game_state.get("player_names", {}).get(player_id, player_id),
                "alive": self.grimoire.is_player_alive(player_id)
            })
        return seating