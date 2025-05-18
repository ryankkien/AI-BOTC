#backend/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseAgent(ABC):
    def __init__(self, player_id: str, role: str, alignment: str):
        self.player_id = player_id
        self.role = role
        self.alignment = alignment
        self.memory = {
            "public_chat_log": [],
            "votes": [],
            "nominations": [],
            "private_clues": [],
            "known_info": [] #e.g., learned from abilities
        }
        self.status = {"alive": True, "poisoned": False, "drunk": False}

    @abstractmethod
    async def get_night_action(self, game_state: Dict[str, Any], alive_players: List[str]) -> Dict[str, Any]:
        """Determine the agent's night action based on their role and the game state."""
        pass

    @abstractmethod
    async def generate_chat_message(self, game_state: Dict[str, Any], chat_history: List[str]) -> str:
        """Generate a natural language chat message."""
        pass

    @abstractmethod
    async def decide_nomination(self, game_state: Dict[str, Any], alive_players: List[str], previous_nominations: List[Dict]) -> str:
        """Decide who to nominate for execution."""
        pass

    @abstractmethod
    async def decide_vote(self, game_state: Dict[str, Any], nominee: str) -> bool:
        """Decide whether to vote for the current nominee."""
        pass

    def update_memory(self, event_type: str, data: Any):
        if event_type == "CHAT":
            self.memory["public_chat_log"].append(data)
        elif event_type == "VOTE_RESULT":
            self.memory["votes"].append(data)
        elif event_type == "NOMINATION":
            self.memory["nominations"].append(data)
        elif event_type == "PRIVATE_NIGHT_INFO":
            self.memory["private_clues"].append(data)
        elif event_type == "STATUS_UPDATE":
            self.status.update(data)
        #can add more specific memory updates

    def get_persona_summary(self) -> str:
        return f"You are {self.player_id}, the {self.role} ({self.alignment}). Your objective is to {'help Good win by finding the Demon' if self.alignment == 'Good' else 'help Evil win by protecting the Demon and sowing confusion'}."

    #placeholder for summarizing key facts for the agent
    def summarize_memory(self) -> str:
        #this would be more sophisticated, used to feed into LLM prompts
        summary = "Key facts:\n"
        summary += f"  Private clues: {self.memory['private_clues']}\n"
        summary += f"  Observed votes: {len(self.memory['votes'])} recorded.\n"
        summary += f"  Chat snippets: {len(self.memory['public_chat_log'])} messages in log."
        return summary 