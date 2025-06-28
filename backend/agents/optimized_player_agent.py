"""
Optimized Player Agent that uses memory compression and selective context loading
to reduce prompt sizes while maintaining effectiveness.
"""

from typing import Dict, List, Any, Optional
import json
from .player_agent import PlayerAgent
from .memory_compressor import MemoryCompressor
from ..config.agent_config import agent_config, AgentPromptStrategy

class OptimizedPlayerAgent(PlayerAgent):
    """Enhanced player agent with prompt optimization features"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory_compressor = MemoryCompressor()
        self.cached_summaries = {}
        
    def _build_prompt_context(self, game_state: Dict[str, Any], additional_context: str = "") -> str:
        """Build optimized prompt based on configuration strategy"""
        strategy = agent_config.get_prompt_strategy()
        
        if strategy == AgentPromptStrategy.FULL_CONTEXT:
            # Use original method
            return super()._build_prompt_context(game_state, additional_context)
        elif strategy == AgentPromptStrategy.TOOL_BASED:
            # Minimal context, rely on tools
            return self._build_minimal_prompt(game_state, additional_context)
        else:  # HYBRID
            # Smart mix of embedded and tool-based
            return self._build_hybrid_prompt(game_state, additional_context)
    
    def _build_minimal_prompt(self, game_state: Dict[str, Any], additional_context: str = "") -> str:
        """Build minimal prompt for tool-based approach"""
        phase_summary = self.memory_compressor.create_phase_summary(game_state, self.memory)
        
        prompt = f"""You are {self.player_id} ({self.get_display_name(game_state)}) in Blood on the Clocktower.
Role: {self.role} | Alignment: {self.alignment}
{phase_summary}

Key Memory: {self._get_compressed_memory_summary()}

Task: {additional_context}

Use available game queries to gather needed information, then make your decision."""
        
        return prompt
    
    def _build_hybrid_prompt(self, game_state: Dict[str, Any], additional_context: str = "") -> str:
        """Build hybrid prompt with essential context embedded and rest available via tools"""
        # Start with basic info
        prompt = f"You are {self.player_id} ({self.get_display_name(game_state)}) playing Blood on the Clocktower.\n"
        prompt += f"Role: {self.role} ({self.alignment})\n"
        prompt += f"Current Phase: {game_state.get('current_phase')} | Day: {game_state.get('day_number')}\n\n"
        
        # Add compressed memory
        prompt += "Essential Information:\n"
        prompt += self._get_essential_context(game_state) + "\n"
        
        # Add task-specific context
        if additional_context:
            prompt += f"\nTask: {additional_context}\n"
        
        # Add decision guidance
        prompt += "\nFor additional information, you can query:\n"
        prompt += "- Player statuses and voting history\n"
        prompt += "- Detailed game events and chat logs\n"
        prompt += "- Seating arrangements and neighbor information\n"
        
        return prompt
    
    def _get_compressed_memory_summary(self) -> str:
        """Get highly compressed memory summary"""
        key_obs = self.memory_compressor.extract_key_observations(self.memory)
        if key_obs:
            return " | ".join(key_obs[:5])  # Top 5 observations only
        return "No significant observations yet"
    
    def _get_essential_context(self, game_state: Dict[str, Any]) -> str:
        """Extract only the most essential context for current decision"""
        essential = []
        
        # Always include private role information
        if self.memory.get("private_info"):
            info = self.memory["private_info"]
            if "clues" in info and info["clues"]:
                essential.append(f"My clues: {json.dumps(info['clues'])}")
            if "storyteller_told_me" in info:
                essential.append(f"ST told me: {info['storyteller_told_me']}")
        
        # Phase-specific essentials
        phase = game_state.get("current_phase")
        
        if phase == "VOTING":
            # Just current nominee and maybe their recent behavior
            nominee = game_state.get("current_nominee")
            if nominee:
                essential.append(f"Voting on: {nominee}")
                # Check if we have suspicion level
                if nominee in self.memory.get("suspicions", {}):
                    level = self.memory["suspicions"][nominee]
                    essential.append(f"Suspicion of {nominee}: {level:.2f}")
        
        elif phase == "NOMINATION":
            # Who's alive and who can we nominate
            alive_count = len([p for p in game_state.get("players", []) 
                             if game_state.get("statuses", {}).get(p, {}).get("alive", False)])
            essential.append(f"{alive_count} players alive")
            
            # Our top suspicions
            if "suspicions" in self.memory:
                top_suspect = max(self.memory["suspicions"].items(), 
                                key=lambda x: x[1], default=(None, 0))
                if top_suspect[0] and top_suspect[1] > 0.5:
                    essential.append(f"Most suspicious: {top_suspect[0]} ({top_suspect[1]:.2f})")
        
        elif phase in ["FIRST_NIGHT", "NIGHT"]:
            # Night ability info
            if self.role_details.get("first_night_ability" if phase == "FIRST_NIGHT" else "other_night_ability"):
                essential.append(f"You have a night ability: {self.role_details.get('description', '')[:100]}...")
        
        # Recent critical events (deaths in last day)
        recent_deaths = [e for e in self.memory.get("events", [])[-10:] 
                        if e.get("type") == "DEATH" and e.get("day", 0) >= game_state.get("day_number", 1) - 1]
        if recent_deaths:
            death_summary = f"Recent deaths: {', '.join([e.get('player', 'Unknown') for e in recent_deaths])}"
            essential.append(death_summary)
        
        return "\n".join(essential)
    
    def summarize_memory(self) -> str:
        """Create compressed memory summary"""
        # Check if we have a cached summary
        cache_key = f"{self.memory.get('last_update', 0)}_{len(self.memory.get('events', []))}"
        if cache_key in self.cached_summaries:
            return self.cached_summaries[cache_key]
        
        # Compress events
        events = self.memory.get("events", [])
        compressed_events = self.memory_compressor.compress_events(
            events, 
            max_events=agent_config.get_memory_limit()
        )
        
        # Build summary
        summary_parts = []
        
        # Add compressed event summary
        if compressed_events["compressed"]:
            summary_parts.append(f"Events: {len(compressed_events['events'])} recent + {compressed_events['summary']['total_compressed']} compressed")
            # Add event type summary
            for event_type, info in compressed_events["summary"]["by_type"].items():
                summary_parts.append(f"  - {event_type}: {info['count']} events")
        else:
            summary_parts.append(f"Events: {len(compressed_events['events'])} total")
        
        # Add key observations
        key_obs = self.memory_compressor.extract_key_observations(self.memory)
        if key_obs:
            summary_parts.append("Key Observations:")
            for obs in key_obs[:7]:  # Limit to 7
                summary_parts.append(f"  - {obs}")
        
        # Cache the summary
        summary = "\n".join(summary_parts)
        self.cached_summaries[cache_key] = summary
        
        # Keep cache size reasonable
        if len(self.cached_summaries) > 10:
            # Remove oldest entries
            keys = sorted(self.cached_summaries.keys())
            for key in keys[:-5]:
                del self.cached_summaries[key]
        
        return summary
    
    async def decide_action(self, game_state: Dict[str, Any], action_type: str = None) -> str:
        """Decide on an action with optimized prompt"""
        if not self.llm:
            return "PASS"
        
        # Use optimized prompt building
        context = self._build_prompt_context(game_state, f"Decide your {action_type or 'next'} action")
        
        # Add efficiency instruction
        context += "\n\nProvide a concise response focusing on your action choice and brief reasoning."
        
        response = await self._rate_limited_generate(context)
        return self._parse_action_response(response.text)
    
    def _curate_memory(self) -> None:
        """Enhanced memory curation with compression"""
        # First apply memory limit
        memory_limit = agent_config.get_memory_limit()
        if "events" in self.memory and len(self.memory["events"]) > memory_limit:
            # Keep first few and recent events
            keep_first = 5
            self.memory["events"] = (
                self.memory["events"][:keep_first] + 
                self.memory["events"][-(memory_limit - keep_first):]
            )
        
        # Compress chat logs if needed
        if "chat_logs" in self.memory:
            chat_threshold = agent_config.get_chat_summarization_threshold()
            for phase, logs in self.memory["chat_logs"].items():
                if len(logs) > chat_threshold:
                    compressed = self.memory_compressor.compress_chat_log(logs, chat_threshold)
                    self.memory["chat_logs"][phase] = compressed
        
        # Run original curation if enabled
        if self.game_manager and self.game_manager.settings.memory_curator_enabled:
            super()._curate_memory()
        else:
            # Just clear the cache since memory changed
            self.cached_summaries.clear()