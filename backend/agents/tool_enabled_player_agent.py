"""
Tool-enabled Player Agent that uses on-demand queries instead of embedding all context in prompts.
This significantly reduces token usage and allows for more focused reasoning.
"""

from typing import Dict, List, Any, Optional
import json
from .base_agent import BaseAgent
from ..tools.game_state_tools import GameStateTools
from ..llm_providers import UnifiedLLMClient, global_rate_limit

class ToolEnabledPlayerAgent(BaseAgent):
    """Player agent that uses tools to query game state instead of large prompts"""
    
    def __init__(self, player_id: str, role: str, alignment: str, 
                 api_key: str = None, game_manager: Any = None,
                 provider_type: str = None, model: str = None):
        super().__init__(player_id, role, alignment)
        
        # Initialize LLM and tools
        self.game_manager = game_manager
        self.tools = None  # Will be set when grimoire is available
        
        # Same LLM initialization as original PlayerAgent
        if api_key:
            from ..llm_providers import LLMFactory
            provider = LLMFactory.create_provider(
                provider_type=provider_type,
                api_key=api_key,
                model=model
            )
            self.llm = UnifiedLLMClient(provider, game_manager)
            self.llm.set_agent_id(player_id)
        else:
            self.llm = None
    
    def set_tools(self, grimoire):
        """Initialize tools with grimoire reference"""
        self.tools = GameStateTools(grimoire)
    
    def _build_compact_prompt(self, task_type: str, additional_context: str = "") -> str:
        """Build a compact prompt that relies on tool usage instead of embedding all context"""
        prompt = f"""You are {self.player_id} playing Blood on the Clocktower.
Role: {self.role} ({self.alignment})
Current Task: {task_type}

You have access to the following tools to query game state:
- get_alive_players(): List all living players
- get_dead_players(): List all dead players with death info
- get_current_phase(): Current game phase and day
- get_player_neighbors(player_id): Get adjacent players
- get_nomination_history(day): Get nominations for a day
- get_voting_history(player_id): Get a player's voting record
- get_public_executions(): List all executions
- check_player_status(player_id, status): Check player status

Your Memory Summary:
{self._get_memory_summary()}

{additional_context}

Think step-by-step:
1. What information do you need to make this decision?
2. Use tools to gather that information
3. Reason based on the information
4. Make your decision

Respond with your reasoning and final decision."""
        
        return prompt
    
    def _get_memory_summary(self) -> str:
        """Get a brief summary of key memories"""
        summary_parts = []
        
        # Private info
        if self.memory.get("private_info"):
            summary_parts.append(f"Private Info: {json.dumps(self.memory['private_info'])}")
        
        # Recent events (last 3)
        recent_events = self.memory.get("events", [])[-3:]
        if recent_events:
            summary_parts.append(f"Recent Events: {len(recent_events)} events")
        
        # Key observations
        if self.memory.get("key_observations"):
            summary_parts.append(f"Key Observations: {', '.join(self.memory['key_observations'][:3])}")
        
        return "\n".join(summary_parts) if summary_parts else "No significant memories yet."
    
    async def decide_action_with_tools(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make a decision using tool queries instead of full context"""
        if not self.llm or not self.tools:
            return {"action_type": "PASS", "reason": "No LLM or tools available"}
        
        # Build compact prompt
        prompt = self._build_compact_prompt(action_type, json.dumps(context))
        
        # Create a conversation that includes tool usage
        messages = [
            {"role": "system", "content": self._get_tool_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        # Simulate tool usage conversation
        tool_calls_made = []
        max_tool_calls = 5  # Prevent infinite loops
        
        for _ in range(max_tool_calls):
            # Get LLM response
            await global_rate_limit()
            response = await self.llm.generate_content_async(
                json.dumps(messages),
                response_format="json"
            )
            
            # Parse response
            try:
                response_data = json.loads(response.text)
                
                # Check if it wants to use a tool
                if response_data.get("tool_call"):
                    tool_name = response_data["tool_call"]["name"]
                    tool_args = response_data["tool_call"].get("args", {})
                    
                    # Execute tool
                    tool_result = self._execute_tool(tool_name, tool_args)
                    tool_calls_made.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": tool_result
                    })
                    
                    # Add to conversation
                    messages.append({
                        "role": "assistant",
                        "content": json.dumps(response_data)
                    })
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(tool_result)
                    })
                    
                elif response_data.get("final_decision"):
                    # Agent has made a decision
                    return response_data["final_decision"]
                    
            except json.JSONDecodeError:
                # Fallback to simple decision
                return {"action_type": "PASS", "reason": "Failed to parse response"}
        
        # Fallback if too many tool calls
        return {"action_type": "PASS", "reason": "Decision process took too long"}
    
    def _get_tool_system_prompt(self) -> str:
        """System prompt for tool usage"""
        return """You are an AI agent playing Blood on the Clocktower. You can use tools to query game state.

To use a tool, respond with:
{
    "tool_call": {
        "name": "tool_name",
        "args": {"arg1": "value1"}
    },
    "thinking": "Why I'm using this tool"
}

When ready to make a decision, respond with:
{
    "final_decision": {
        "action_type": "YOUR_ACTION",
        "target": "player_id" (if applicable),
        "reason": "Your reasoning"
    },
    "thinking": "My thought process"
}"""
    
    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool and return its result"""
        if not self.tools:
            return {"error": "Tools not initialized"}
        
        # Map tool names to methods
        tool_methods = {
            "get_alive_players": self.tools.get_alive_players,
            "get_dead_players": self.tools.get_dead_players,
            "get_current_phase": self.tools.get_current_phase,
            "get_player_neighbors": self.tools.get_player_neighbors,
            "get_nomination_history": self.tools.get_nomination_history,
            "get_voting_history": self.tools.get_voting_history,
            "get_public_executions": self.tools.get_public_executions,
            "check_player_status": self.tools.check_player_status,
            "get_role_ability_info": self.tools.get_role_ability_info,
            "get_seating_order": self.tools.get_seating_order
        }
        
        if tool_name not in tool_methods:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            # Call the tool with appropriate arguments
            method = tool_methods[tool_name]
            if tool_name in ["get_player_neighbors", "get_voting_history"]:
                return method(args.get("player_id"))
            elif tool_name == "get_nomination_history":
                return method(args.get("day"))
            elif tool_name == "check_player_status":
                return method(args.get("player_id"), args.get("status"))
            elif tool_name == "get_role_ability_info":
                return method(args.get("role"))
            else:
                return method()
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}