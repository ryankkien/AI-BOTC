"""
Configuration for agent behavior and prompt optimization strategies
"""

from typing import Dict, Any
from enum import Enum

class AgentPromptStrategy(Enum):
    """Different strategies for managing agent prompts"""
    FULL_CONTEXT = "full_context"  # Original approach - embed everything
    TOOL_BASED = "tool_based"      # New approach - use tools to query
    HYBRID = "hybrid"              # Mix of both - critical info embedded, rest via tools
    
class AgentConfig:
    """Configuration for agent behavior"""
    
    # Default settings
    DEFAULT_SETTINGS = {
        "prompt_strategy": AgentPromptStrategy.FULL_CONTEXT,
        "max_memory_events": 50,  # Limit memory to last N events
        "summarize_chat_after": 20,  # Summarize chat logs after N messages
        "use_memory_compression": True,
        "tool_usage_enabled": False,
        "max_tool_calls_per_decision": 5,
        "cache_tool_results": True,
        "cache_duration_seconds": 60
    }
    
    def __init__(self, custom_settings: Dict[str, Any] = None):
        self.settings = self.DEFAULT_SETTINGS.copy()
        if custom_settings:
            self.settings.update(custom_settings)
    
    def get_prompt_strategy(self) -> AgentPromptStrategy:
        """Get the current prompt strategy"""
        strategy_value = self.settings.get("prompt_strategy", AgentPromptStrategy.FULL_CONTEXT)
        if isinstance(strategy_value, str):
            return AgentPromptStrategy(strategy_value)
        return strategy_value
    
    def should_use_tools(self) -> bool:
        """Check if tool usage is enabled"""
        return self.settings.get("tool_usage_enabled", False)
    
    def get_memory_limit(self) -> int:
        """Get maximum number of events to keep in memory"""
        return self.settings.get("max_memory_events", 50)
    
    def get_chat_summarization_threshold(self) -> int:
        """Get number of chat messages before summarization"""
        return self.settings.get("summarize_chat_after", 20)

# Global configuration instance
agent_config = AgentConfig()

def configure_agents(settings: Dict[str, Any]):
    """Update global agent configuration"""
    global agent_config
    agent_config = AgentConfig(settings)