"""
Memory compression utilities to reduce the amount of information in agent prompts
"""

from typing import Dict, List, Any, Optional
import json
from collections import defaultdict
from datetime import datetime

class MemoryCompressor:
    """Compress and summarize agent memories to reduce prompt sizes"""
    
    @staticmethod
    def compress_events(events: List[Dict[str, Any]], max_events: int = 20) -> Dict[str, Any]:
        """Compress a list of events into a summary"""
        if len(events) <= max_events:
            return {"events": events, "compressed": False}
        
        # Keep first few and last few events in full
        keep_first = 3
        keep_last = 5
        
        full_events = events[:keep_first] + events[-keep_last:]
        middle_events = events[keep_first:-keep_last]
        
        # Summarize middle events by type
        event_summary = defaultdict(list)
        for event in middle_events:
            event_type = event.get("type", "unknown")
            event_summary[event_type].append(event)
        
        # Create compressed summary
        compressed = {
            "events": full_events,
            "compressed": True,
            "summary": {
                "total_compressed": len(middle_events),
                "by_type": {}
            }
        }
        
        for event_type, type_events in event_summary.items():
            compressed["summary"]["by_type"][event_type] = {
                "count": len(type_events),
                "sample": type_events[0] if type_events else None
            }
        
        return compressed
    
    @staticmethod
    def compress_chat_log(chat_messages: List[Dict[str, Any]], threshold: int = 20) -> Dict[str, Any]:
        """Compress chat logs into a summary"""
        if len(chat_messages) <= threshold:
            return {"messages": chat_messages, "compressed": False}
        
        # Group messages by sender
        sender_messages = defaultdict(list)
        for msg in chat_messages:
            sender = msg.get("sender_name", msg.get("sender", "Unknown"))
            sender_messages[sender].append(msg.get("text", ""))
        
        # Create summary
        summary = {
            "compressed": True,
            "total_messages": len(chat_messages),
            "message_counts": {},
            "recent_messages": chat_messages[-10:],  # Keep last 10 messages
            "key_topics": []
        }
        
        # Count messages per sender
        for sender, messages in sender_messages.items():
            summary["message_counts"][sender] = len(messages)
        
        # Extract key topics (simple keyword extraction)
        all_text = " ".join([msg.get("text", "") for msg in chat_messages])
        key_words = ["nominate", "vote", "evil", "good", "demon", "imp", "trust", "suspicious", "claim", "role"]
        
        for word in key_words:
            if word.lower() in all_text.lower():
                count = all_text.lower().count(word.lower())
                if count > 2:  # Only include if mentioned multiple times
                    summary["key_topics"].append(f"{word} (mentioned {count} times)")
        
        return summary
    
    @staticmethod
    def extract_key_observations(memory: Dict[str, Any]) -> List[str]:
        """Extract key observations from memory to create a brief summary"""
        observations = []
        
        # Extract role-specific clues
        if "private_info" in memory:
            private_info = memory["private_info"]
            if "clues" in private_info:
                for clue in private_info["clues"]:
                    observations.append(f"Clue: {clue}")
            if "storyteller_told_me" in private_info:
                observations.append(f"ST info: {private_info['storyteller_told_me']}")
        
        # Extract voting patterns
        if "voting_history" in memory:
            votes = memory["voting_history"]
            if len(votes) > 0:
                observations.append(f"Voted in {len(votes)} nominations")
        
        # Extract death observations
        if "observed_deaths" in memory:
            deaths = memory["observed_deaths"]
            for death in deaths[-3:]:  # Last 3 deaths
                observations.append(f"{death['player']} died on day {death['day']}")
        
        # Extract suspicions
        if "suspicions" in memory:
            top_suspicions = sorted(
                memory["suspicions"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            for player, level in top_suspicions:
                if level > 0.7:
                    observations.append(f"Highly suspicious of {player}")
                elif level > 0.5:
                    observations.append(f"Somewhat suspicious of {player}")
        
        return observations[:10]  # Limit to 10 key observations
    
    @staticmethod
    def create_phase_summary(game_state: Dict[str, Any], memory: Dict[str, Any]) -> str:
        """Create a brief summary appropriate for the current phase"""
        phase = game_state.get("current_phase", "UNKNOWN")
        day = game_state.get("day_number", 0)
        
        summary_parts = [f"Day {day}, Phase: {phase}"]
        
        if phase == "DAY_CHAT":
            # Focus on social deduction
            alive_count = len([p for p in game_state.get("players", []) if game_state.get("statuses", {}).get(p, {}).get("alive", False)])
            summary_parts.append(f"{alive_count} players alive")
            
            # Recent executions
            if "recent_executions" in memory:
                recent = memory["recent_executions"][-1:]
                for exe in recent:
                    summary_parts.append(f"Recently executed: {exe['player']}")
        
        elif phase == "NOMINATION":
            # Focus on nomination strategy
            if "can_nominate" in memory:
                summary_parts.append("You can nominate" if memory["can_nominate"] else "Already nominated")
            if "nomination_targets" in memory:
                targets = memory["nomination_targets"][:3]
                summary_parts.append(f"Consider nominating: {', '.join(targets)}")
        
        elif phase == "VOTING":
            # Focus on current vote
            if "current_nominee" in game_state:
                summary_parts.append(f"Voting on: {game_state['current_nominee']}")
            if "nominee_suspicion" in memory:
                level = memory["nominee_suspicion"]
                summary_parts.append(f"Suspicion level: {level}")
        
        elif phase in ["FIRST_NIGHT", "NIGHT"]:
            # Focus on night action
            if "night_ability_available" in memory:
                summary_parts.append("Night ability available" if memory["night_ability_available"] else "No night ability")
            if "priority_targets" in memory:
                targets = memory["priority_targets"][:2]
                summary_parts.append(f"Priority targets: {', '.join(targets)}")
        
        return " | ".join(summary_parts)