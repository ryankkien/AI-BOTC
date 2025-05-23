#backend/storyteller/grimoire.py
from typing import List, Dict, Any, Optional

class Grimoire:
    def __init__(self):
        self.game_state: Dict[str, Any] = {} #generic game state like player names, etc.
        self.players: List[str] = [] #list of player_ids in seating order
        self.roles: Dict[str, str] = {} #player_id -> role_name
        self.alignments: Dict[str, str] = {} #player_id -> alignment_str
        self.statuses: Dict[str, Dict[str, Any]] = {} #player_id -> {alive: bool, poisoned: bool, ...}
        self.game_log: List[Dict[str, Any]] = []
        # self.seating_order is effectively self.players after setup
        self.day_number: int = 0
        self.current_phase: Optional[str] = None #e.g., "FIRST_NIGHT", "DAY_CHAT", "NOMINATION", "VOTING", "NIGHT"
        self.demon_bluffs: List[str] = [] #list of 3 role names given to the demon as bluffs
        self.fortune_teller_red_herring_player_id: Optional[str] = None #player_id picked as red herring
        self.current_demon_player_id: Optional[str] = None # Tracks the current demon
        self.baron_added_outsiders: List[str] = [] # Stores names of Outsider roles added by Baron
        self.storyteller_log: List[str] = [] #internal log for storyteller/debug
        self.private_clues: Dict[str, List[Any]] = {} #player_id -> list of private clues

    def add_player(self, player_id: str, role: str, alignment: str):
        if player_id not in self.players:
            self.players.append(player_id) #initial add, seating order fixed later
        self.roles[player_id] = role
        self.alignments[player_id] = alignment
        self.statuses[player_id] = {
            "alive": True,
            "poisoned": False, # Confirmed: Initialized to False
            "is_drunk": False, # For the Drunk role
            "thinks_is_role": None, # For the Drunk role - stores false Townsfolk role
            "thinks_is_alignment": None, # For the Drunk role - stores false alignment
            "misregisters_as_role": None, # For the Recluse - stores false role they register as
            "misregisters_as_alignment": None, # For the Recluse - stores false alignment they register as
            "protected_by_monk": False,
            "nominated_today": False, #has this player been nominated today
            "can_nominate": True, #can this player nominate others today
            "used_virgin_ability": False, # Confirmed: Initialized to False
            "used_slayer_ability": False, # Confirmed: Initialized to False
            #add other relevant statuses here
        }
        # initialize private clues list for this player
        self.private_clues[player_id] = []
        self.log_event("PLAYER_ADDED", {"player_id": player_id, "role": role, "alignment": alignment})

    def update_status(self, player_id: str, status_key: str, value: Any):
        if player_id in self.statuses and status_key in self.statuses[player_id]:
            self.statuses[player_id][status_key] = value
            self.log_event("STATUS_UPDATE", {"player_id": player_id, "status": status_key, "new_value": value})
        else:
            self.storyteller_log.append(f"Warning: Could not update status {status_key} for player {player_id}. Player or status key not found.")
            print(f"Warning: Could not update status {status_key} for player {player_id}")

    def log_event(self, event_type: str, data: Dict[str, Any]):
        #event_type: e.g., "CHAT", "NOMINATION", "VOTE", "ABILITY_USE", "DEATH", "PHASE_CHANGE"
        #data: dictionary with event-specific details
        #todo: use a proper timestamp library or pass from main.py if synchronized time is critical
        timestamp = "#placeholder_timestamp#" #datetime.utcnow().isoformat()
        log_entry = {"timestamp": timestamp, "event_type": event_type, "data": data}
        self.game_log.append(log_entry)
        #self.storyteller_log.append(f"Event: {event_type} - {data}") #more verbose for internal log
        print(f"Event Logged: {log_entry}") #for now, print to console
        #update phase and day_number in grimoire
        if event_type == "PHASE_CHANGE":
            phase = data.get("phase") or data.get("new_phase")
            if phase:
                self.current_phase = phase
            if "day_number" in data:
                self.day_number = data["day_number"]

    def get_player_role(self, player_id: str) -> Optional[str]:
        return self.roles.get(player_id)

    def get_player_alignment(self, player_id: str) -> Optional[str]:
        return self.alignments.get(player_id)

    def is_player_alive(self, player_id: str) -> bool:
        return self.statuses.get(player_id, {}).get("alive", False)
    
    def get_player_status(self, player_id: str, status_key: str) -> Any:
        return self.statuses.get(player_id, {}).get(status_key)

    def get_all_player_info_for_observer(self) -> List[Dict[str, Any]]:
        """Returns comprehensive info for all players, for observer mode or Spy."""
        all_info = []
        for player_id in self.players:
            info = {
                "id": player_id,
                "name": self.game_state.get("player_names", {}).get(player_id, player_id),
                "role": self.roles.get(player_id),
                "alignment": self.alignments.get(player_id),
                "status": self.statuses.get(player_id, {}).copy() #send a copy
            }
            all_info.append(info)
        return all_info

    def get_public_player_info(self) -> List[Dict[str, Any]]:
        """Returns info visible to all players (name, alive status)."""
        public_info = []
        for player_id in self.players:
            info = {
                "id": player_id,
                "name": self.game_state.get("player_names", {}).get(player_id, player_id),
                "isAlive": self.is_player_alive(player_id)
                #could add more public info like who they voted for if that becomes public
            }
            public_info.append(info)
        return public_info

    def get_player_ids_by_role(self, role_name: str) -> List[str]:
        return [pid for pid, r_name in self.roles.items() if r_name == role_name]

    def get_player_ids_by_alignment(self, alignment_val: str) -> List[str]:
        return [pid for pid, align in self.alignments.items() if align == alignment_val]
    
    def get_alive_players(self) -> List[str]:
        return [pid for pid in self.players if self.is_player_alive(pid)]

    def add_private_clue(self, player_id: str, clue: Any):
        """Record a private clue for a player."""
        if player_id not in self.private_clues:
            self.private_clues[player_id] = []
        self.private_clues[player_id].append(clue)
        # also log the private info event in game log
        self.log_event("PRIVATE_INFO", {"player_id": player_id, "clue": clue})

    def get_private_clues(self, player_id: str) -> List[Any]:
        """Retrieve all private clues that have been recorded for a player."""
        return self.private_clues.get(player_id, [])

    #add more getter/setter methods as needed for game state management 