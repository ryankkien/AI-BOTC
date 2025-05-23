#backend/agents/player_agent.py
import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent
from ..storyteller.roles import ROLES_DATA, RoleAlignment
from ..llm_providers import LLMFactory, UnifiedLLMClient, global_rate_limit
import time
import asyncio

load_dotenv()

#global variables for rate limiting across all playeragent instances
_last_global_llm_call_time: float = None
_llm_rate_limit_lock = asyncio.Lock()

class PlayerAgent(BaseAgent):
    def __init__(self, player_id: str, role: str, alignment: str, api_key: Optional[str] = None, game_manager: Optional[Any] = None, provider_type: Optional[str] = None, model: Optional[str] = None):
        super().__init__(player_id, role, alignment)
        self.llm = None
        self.game_manager = game_manager
        
        # Create LLM provider using the factory
        try:
            # Determine which API key to use based on provider type
            effective_api_key = api_key
            if not effective_api_key:
                # Auto-detect API key based on provider type or available keys
                provider_type = provider_type or os.getenv("LLM_PROVIDER", "auto")
                if provider_type == "openai" or provider_type == "auto":
                    effective_api_key = os.getenv("OPENAI_API_KEY")
                elif provider_type == "anthropic":
                    effective_api_key = os.getenv("ANTHROPIC_API_KEY")
                elif provider_type == "google":
                    effective_api_key = os.getenv("GOOGLE_API_KEY")
                else:
                    # Try to find any available API key
                    effective_api_key = (os.getenv("OPENAI_API_KEY") or 
                                        os.getenv("ANTHROPIC_API_KEY") or 
                                        os.getenv("GOOGLE_API_KEY"))
            
            if effective_api_key:
                # Create the LLM provider
                provider = LLMFactory.create_provider(
                    provider_type=provider_type,
                    api_key=effective_api_key,
                    model=model
                )
                
                # Wrap it in our unified client
                self.llm = UnifiedLLMClient(provider, game_manager)
                self.llm.set_agent_id(player_id)
                
                print(f"Initialized LLM for {player_id} using {type(provider).__name__} with model {provider.model}")
            else:
                print(f"Warning: No API key found for PlayerAgent {player_id}. LLM will not be initialized.")
                self.llm = None
                
        except Exception as e:
            print(f"Failed to initialize LLM for {player_id}: {e}")
            self.llm = None
            
        self.role_details = ROLES_DATA.get(self.role, {})
        # Ensure memory is initialized as a dictionary
        if not hasattr(self, 'memory') or self.memory is None:
            self.memory = {
                "private_info": None,
                "public_chat_log": [], # Should be updated by GameManager or via an update_memory method
                "private_chat_logs": {}, # Dict keyed by other player_id
                "observations": [],
                "actions_taken": [],
                "important_events": []
            }

        # ensure we track important curated events
        self.memory.setdefault("important_events", [])

    def _build_prompt_context(self, game_state: Dict[str, Any], additional_context: str = "") -> str:
        prompt = self.get_persona_summary() + "\n"
        prompt += "Current Game State:\n"
        prompt += f"  Day: {game_state.get('day_number', 0)}\n"
        prompt += f"  Phase: {game_state.get('current_phase', 'Unknown')}\n"
        
        all_player_details = game_state.get('all_players_details', []) # Expects a list of dicts: {'id':pid, 'name':pname, 'is_alive':bool}
        if not all_player_details and 'players' in game_state: # Fallback to older structure if needed
            all_player_details = [{'id': p['id'], 'name': p.get('name', p['id']), 'is_alive': p.get('isAlive', True)} for p in game_state.get('players', [])]

        alive_players = [p for p in all_player_details if p['is_alive']]
        dead_players = [p for p in all_player_details if not p['is_alive']]

        prompt += f"  Players alive: {len(alive_players)}/{len(all_player_details)}\n"
        
        alive_player_names_str = ", ".join([p['name'] for p in alive_players])
        prompt += f"  Alive players by name: {alive_player_names_str if alive_player_names_str else 'None'}\n"
        
        dead_player_names_str = ", ".join([p['name'] for p in dead_players])
        if dead_player_names_str:
            prompt += f"  Dead players by name: {dead_player_names_str}\n"

        # Own status (assuming self.status is updated, e.g. by storyteller)
        prompt += f"  Your current status (alive, poisoned, drunk, etc.): {self.status}\n" 
        prompt += "\nMemory Summary (Your private knowledge and observations):\n"
        prompt += self.summarize_memory() + "\n"
        
        # Use full daily chat log passed from GameManager
        daily_chat_log = game_state.get("daily_chat_log", [])
        prompt += "\nFull Chat History for current day/phase (or relevant recent history):\n"
        # For extremely long games, this might need summarization or a more sophisticated context window.
        if daily_chat_log:
            for msg in daily_chat_log: # Iterate over the passed log
                sender_name = msg.get('sender_name', msg.get('sender', 'System'))
                prompt += f"  {sender_name}: {msg.get('text', '')}\n"
        else:
            prompt += "  (No chat history available for this phase yet.)\n"
            
        # Include summary of private chats
        if self.memory.get("private_chat_logs"):
            prompt += "\nSummary of recent Private Conversations (if any):\n"
            for partner_id, logs in self.memory["private_chat_logs"].items():
                partner_name = game_state.get("player_names", {}).get(partner_id, partner_id)
                prompt += f"  With {partner_name}:\n"
                for log_entry in logs[-3:]: # Last 3 messages from each private chat
                    log_sender = log_entry.get("sender_name", log_entry.get("sender"))
                    prompt += f"    {log_sender}: {log_entry.get('text')}\n"
            prompt += "----\n"
        #include available actions if provided
        available_actions = game_state.get("available_actions")
        if available_actions:
            prompt += "\navailable actions:\n"
            prompt += f"  {', '.join(available_actions)}\n"
        if additional_context:
            prompt += "\nSpecific Task Context:\n"
            prompt += additional_context + "\n"
        return prompt

    async def _rate_limited_generate(self, *args, **kwargs):
        """Generate content with rate limiting using the new unified LLM system"""
        # Use the global rate limiting from the new LLM system
        await global_rate_limit()
        
        # The UnifiedLLMClient already handles debug logging, so we just call it directly
        response = await self.llm.generate_content_async(*args, **kwargs)
        return response

    async def get_night_action(self, game_state: Dict[str, Any], alive_player_ids_with_names: List[Dict[str,str]]) -> Optional[Dict[str, Any]]:
        if not self.llm or not self.status["alive"]:
            return None

        role_info = self.role_details
        is_first_night = game_state.get("current_phase") == "FIRST_NIGHT"
        needs_active_choice = False
        
        #determine if an active choice is needed based on role ability for current night phase
        if is_first_night and role_info.get("first_night_ability"):
            #roles like Washerwoman, Librarian, Investigator, Chef, Empath (FN) get passive info from Storyteller
            #roles like Fortune Teller (FN), Monk (FN, if allowed), Poisoner (FN, if allowed), Imp (FN) make choices
            if self.role not in ["Washerwoman", "Librarian", "Investigator", "Chef"]:
                 #empath first night is passive usually (0,1,2 from ST)
                 if self.role == "Empath" and is_first_night:
                     needs_active_choice = False 
                 else: 
                    needs_active_choice = True
        elif not is_first_night and role_info.get("other_night_ability"):
            #roles like Monk, Poisoner, Imp, Fortune Teller, Empath (other nights), Butler, Spy, Undertaker
            #some of these are info (Spy, Undertaker, Empath), others are choices
            if self.role not in ["Spy", "Undertaker"]:
                #Empath on other nights is passive info based on neighbors
                if self.role == "Empath" and not is_first_night:
                    needs_active_choice = False
                else:
                    needs_active_choice = True

        if not needs_active_choice:
            #this signals to the Storyteller that this agent expects passive info or has no choice ability this night.
            #the Storyteller is responsible for sending info to roles like Washerwoman, Empath, Spy, Undertaker.
            print(f"{self.player_id} ({self.role}) has no active choice this night or expects passive info.")
            return {"action_type": "PASSIVE_OR_NO_ACTION", "player_id": self.player_id, "role": self.role}

        #construct list of available targets (player names and IDs for the prompt)
        #exclude self for roles that cannot target self (e.g. Monk)
        #this is a general list; role description should guide LLM if self-target is invalid/valid
        targetable_players_info = [
            f"{p['name']}(ID:{p['id']})" for p in alive_player_ids_with_names
            #add self if Imp or other self-targetable roles, else filter out self.player_id
            #for now, keeping it simple and letting role description in prompt guide the LLM
        ]
        if self.role == "Imp": #Imp can target self
             targetable_players_info.append(f"Yourself (ID:{self.player_id})")
        else: #most roles cannot target self
            targetable_players_info = [p_info for p_info in targetable_players_info if f"(ID:{self.player_id})" not in p_info]

        action_prompt = (
            f"It is {game_state.get('current_phase')}. Review your role, abilities, and the game state carefully.\n"
            f"Your role: {self.role}. Ability: {role_info.get('description')}\n"
            f"Alive players you can consider targeting: {', '.join(targetable_players_info) if targetable_players_info else 'None (or ability does not require target)'}.\n"
            f"Think step-by-step about your objectives and the best strategic move. Consider all information you have.\n"
            f"If you need to choose one player, respond with: CHOOSE_ONE: [PlayerID]\n"
            f"If you need to choose two players (e.g., for Librarian, Investigator), respond with: CHOOSE_TWO: [PlayerID1, PlayerID2]\n"
            f"If your ability does not require a choice now, you wish to pass (if allowed by your role), or your role is passive this night (e.g. Empath first night), respond with: PASS\n"
            f"Ensure PlayerIDs are exact from the provided list. If no players are targetable for your ability, you should PASS."
        )

        full_prompt = self._build_prompt_context(game_state, additional_context=action_prompt)
        full_prompt += "\nCarefully consider your role, objectives, and available information. Then, provide your decision in the specified format."

        try:
            response = await self._rate_limited_generate(full_prompt)
            choice_text = response.text.strip()
            print(f"{self.player_id} ({self.role}) Night Action LLM Raw Response: {choice_text}")

            targets = []
            action_taken = "PASS" #default

            if choice_text.startswith("CHOOSE_ONE:"):
                target_str = choice_text.split("CHOOSE_ONE:")[1].strip().replace("[","").replace("]","")
                #validate if target_str is one of the actual IDs (alive_player_ids_with_names has {'id':..., 'name':...})
                valid_ids = [p['id'] for p in alive_player_ids_with_names] + ([self.player_id] if self.role == "Imp" else [])
                if target_str in valid_ids:
                    targets = [target_str]
                    action_taken = self.role #use role name as action type for now
                else:
                    print(f"LLM Parse Warning for {self.player_id}: Invalid target ID {target_str}")
                    action_taken = "FAILED_PARSE"
            elif choice_text.startswith("CHOOSE_TWO:"):
                target_list_str = choice_text.split("CHOOSE_TWO:")[1].strip().replace("[","").replace("]","")
                chosen_ids = [t.strip() for t in target_list_str.split(",")]
                valid_ids = [p['id'] for p in alive_player_ids_with_names]
                validated_targets = [tid for tid in chosen_ids if tid in valid_ids]
                if len(validated_targets) == len(chosen_ids) and len(validated_targets) > 0: #ensure all parsed are valid
                    targets = validated_targets
                    action_taken = self.role
                else:
                    print(f"LLM Parse Warning for {self.player_id}: Invalid target IDs in {chosen_ids}")
                    action_taken = "FAILED_PARSE"
            elif choice_text == "PASS":
                action_taken = "PASS"
            else:
                print(f"LLM Parse Warning for {self.player_id}: Could not parse action: {choice_text}")
                action_taken = "FAILED_PARSE" #or "UNKNOWN_ACTION"

            return {"action_type": action_taken, "player_id": self.player_id, "role": self.role, "targets": targets, "raw_response": choice_text}

        except Exception as e:
            print(f"Error during LLM call for {self.player_id} night action: {e}")
            return {"action_type": "ERROR", "player_id": self.player_id, "role": self.role, "targets": [], "error_message": str(e)}

    async def generate_chat_message(self, game_state: Dict[str, Any], chat_history: List[Dict[str, str]]) -> Optional[str]: # chat_history param might be redundant if game_state contains daily_chat_log
        if not self.llm or not self.status["alive"]:
            return None

        chat_prompt_intro = "You are in a game of Blood on the Clocktower. It is the Day phase. You need to decide what to say in the public chat."
        
        # Persona and Goal specific context
        persona_summary = self.get_persona_summary() # This now includes more detailed goals.
        
        chat_prompt_task = (
            "Consider the full chat history provided, your role, your private knowledge, and your team's objectives.\n"
            "What is your current theory about who is good and who is evil? Why?\n"
            "What do you want other players to believe right now?\n"
            "What specific information, if any, are you trying to elicit or subtly convey?\n"
            "Encourage transparency: if you have pertinent information or reasoning, share it publicly.\n"
            "If any player has been notably silent or hasn't explained their thoughts, consider politely calling out their silence as suspicious.\n"
            "Based on all this, formulate your chat message. It should be in character.\n"
            "If you genuinely have nothing to add or prefer to remain silent, respond with the exact word: SILENT.\n"
            "If the discussion has stalled or no one has contributed new information for a while, consider explicitly revealing your role and provide supporting evidence by describing your ability and any private clues you have to prove your claim.\n"
        )

        # _build_prompt_context will use game_state["daily_chat_log"] which should be comprehensive
        full_prompt = self._build_prompt_context(game_state, additional_context=f"{chat_prompt_intro}\n{persona_summary}\n{chat_prompt_task}")
        full_prompt += "\nReturn ONLY your chat message text, or SILENT."
        
        try:
            response = await self._rate_limited_generate(full_prompt)
            message = response.text.strip()
            if message.upper() == "SILENT":
                return None # Indicate no message
            return message
        except Exception as e:
            print(f"Error during LLM call for {self.player_id} chat: {e}")
            # Fallback message to indicate AI is still present but had an issue.
            return "(Pauses thoughtfully, considering the situation...)"

    async def decide_nomination(self, game_state: Dict[str, Any], alive_player_ids_with_names: List[Dict[str,str]], previous_nominations: List[Dict]) -> Optional[str]:
        if not self.llm or not self.status["alive"]:
            return None

        eligible_to_nominate_info = [f"{p['name']}(ID:{p['id']})" for p in alive_player_ids_with_names if p['id'] != self.player_id]

        if not eligible_to_nominate_info:
            return None #cannot nominate if no one else is alive

        nom_prompt = f"It is your turn to nominate someone for execution. Review the game state, chat, and your private information.\n"
        nom_prompt += f"Alive players you can nominate (excluding yourself): {', '.join(eligible_to_nominate_info) if eligible_to_nominate_info else 'None'}.\n"
        if not eligible_to_nominate_info:
             print(f"{self.player_id} ({self.role}) cannot nominate as no one else is eligible.")
             return None

        nom_prompt += f"Previous nominations today: {previous_nominations if previous_nominations else 'None yet'}.\n"
        nom_prompt += "Think step-by-step: What are your strategic reasons for nominating someone? Who is most suspicious and why? How does this nomination align with your team's goals?\n"
        nom_prompt += "After your reasoning (internal thought process), provide your choice.\n"
        nom_prompt += f"Format your response as: NOMINATE: [PlayerID]"

        full_prompt = self._build_prompt_context(game_state, additional_context=nom_prompt)
        full_prompt += "\nThink step-by-step. Then, provide your nomination choice in the specified format, ensuring PlayerID is exact."

        try:
            response = await self._rate_limited_generate(full_prompt)
            choice_text = response.text.strip()
            print(f"{self.player_id} ({self.role}) Nomination LLM Raw Response: {choice_text}")
            if choice_text.startswith("NOMINATE:"):
                target_id = choice_text.split("NOMINATE:")[1].strip().replace("[","").replace("]","")
                valid_ids = [p['id'] for p in alive_player_ids_with_names if p['id'] != self.player_id]
                if target_id in valid_ids:
                    return target_id
                else:
                    print(f"LLM Parse Warning for {self.player_id} Nomination: Invalid target ID {target_id}")
            return None 
        except Exception as e:
            print(f"Error during LLM call for {self.player_id} nomination: {e}")
            return None

    async def decide_vote(self, game_state: Dict[str, Any], nominee_id: str, nominee_name: str) -> Optional[bool]:
        if not self.llm or not self.status["alive"]:
            return None # Cannot vote if not alive or LLM not available
        
        # Get nominee's role if known publicly (e.g., from a claim or previous reveal)
        # This would require game_state to potentially include public role claims.
        # For now, we'll rely on the AI's memory and deduction.

        vote_prompt = f"Player {nominee_name}(ID:{nominee_id}) has been nominated for execution. You must decide to vote YES (execute) or NO (do not execute).\n"
        vote_prompt += "Review all information: game state, chat history, your private knowledge, and your role's objectives.\n"
        vote_prompt += "Think step-by-step: Is the nominee likely evil or good? What are the risks/benefits of executing them (e.g., Saint, unknown powerful role)? How does your vote serve your team's goals?\n"
        vote_prompt += "After your reasoning (internal thought process), provide your vote.\n"
        vote_prompt += "Format your response as: VOTE: [YES/NO]"

        full_prompt = self._build_prompt_context(game_state, additional_context=vote_prompt)
        full_prompt += "\nThink step-by-step. Then, provide your vote choice in the specified format."

        try:
            response = await self._rate_limited_generate(full_prompt)
            choice_text = response.text.strip().upper()
            print(f"{self.player_id} ({self.role}) Vote LLM Raw Response: {choice_text}")
            if choice_text == "VOTE: YES":
                return True
            elif choice_text == "VOTE: NO":
                return False
            print(f"LLM Parse Warning for {self.player_id} Vote: Invalid response {response.text}")
            return False #safer default if parsing fails
        except Exception as e:
            print(f"Error during LLM call for {self.player_id} vote: {e}")
            return False #safer default

    async def _curate_memory(self, event_type: str, data: Any):
        # use LLM to decide if an event is worth remembering long-term
        if not self.llm or not self.status.get("alive", False):
            return
        # craft a simple curator prompt
        prompt = (
            f"You are a memory curator for {self.player_id}.\n"
            f"Decide whether to KEEP or DISCARD the following game event.\n"
            f"Event type: {event_type}\n"
            f"Data: {data}\n"
            "If it is strategically important, reply KEEP; otherwise reply DISCARD."
        )
        try:
            response = await self._rate_limited_generate(prompt)
            decision = response.text.strip().upper()
            if "KEEP" in decision:
                self.memory.setdefault("important_events", []).append({"type": event_type, "data": data})
        except Exception:
            pass

    def update_memory(self, event_type: str, data: Any):
        #this should be called by GameManager when events occur
        #ensure data format is consistent for what is appended
        if event_type == "CHAT_MESSAGE": #expecting data = {"sender", "text", "timestamp"}
            self.memory["public_chat_log"].append(data)
        elif event_type == "VOTE_RESULT": #expecting data = {"nominee", "outcome", "votes"}
            self.memory["votes"].append(data)
        elif event_type == "NOMINATION_EVENT": #expecting data = {"nominator", "nominee"}
            self.memory["nominations"].append(data)
        elif event_type == "PRIVATE_NIGHT_INFO" or event_type == "PRIVATE_CLUE": #expecting data = {"text"} or structured clue
            self.memory["private_clues"].append(data)
        elif event_type == "STATUS_UPDATE": #expecting data = partial status dict e.g. {"poisoned": True}
            self.status.update(data)
        elif event_type == "ROLE_DESCRIPTION": # Storyteller gives full role desc on game start
            self.memory["known_info"].append({"type": "ROLE_INFO", "description": data})
        # schedule curation of this event
        asyncio.create_task(self._curate_memory(event_type, data))

    def get_persona_summary(self) -> str:
        # Base persona string
        persona = f"You are playing Blood on the Clocktower. Your Player ID is {self.player_id}.\n"
        persona += f"Your assigned role is: {self.role}.\n"
        persona += f"Your alignment is: {self.alignment}.\n"

        role_data = ROLES_DATA.get(self.role, {})
        description = role_data.get("description", "No specific description found for your role.")
        first_night_ability = role_data.get("first_night_ability", False)
        other_night_ability = role_data.get("other_night_ability", False)
        day_ability = role_data.get("day_ability", False) # Assuming ROLES_DATA might have this

        persona += f"Role Description: {description}\n"
        if first_night_ability:
            persona += "You have an ability on the First Night.\n"
        if other_night_ability:
            persona += "You have an ability on Other Nights.\n"
        if day_ability: # If you add day abilities to ROLES_DATA
            persona += "You have an ability that can be used during the Day.\n"

        # General goals based on alignment
        if self.alignment == RoleAlignment.GOOD.value or self.alignment == "Townsfolk" or self.alignment == "Outsider": # Accommodate string value if enum not directly used everywhere
            persona += ("Team Goal: You are on the GOOD team. Your primary goal is to identify and help execute the Demon. "
                        "Secondary goals include protecting valuable good players and using your information wisely. "
                        "Be truthful with players you trust, but be wary of deception from evil players. "
                        "Communication and deduction are key to your victory.\n")
            if self.role == "Drunk": # Specific advice for Drunk
                 persona += ("Special Note (Drunk): You THINK you are a different Townsfolk role, but you are the Drunk. "
                             "Your information from the Storyteller might be incorrect or misleading. Try to act like the role you think you are, "
                             "but be aware that your perceptions might be skewed. Your true value might come from drawing attention or confusing evil players.\n")
        elif self.alignment == RoleAlignment.EVIL.value or self.alignment == "Minion" or self.alignment == "Demon":
            persona += ("Team Goal: You are on the EVIL team. Your primary goal is for the Demon to survive until evil players "
                        "outnumber or equal good players, or another evil win condition is met. "
                        "You should try to deceive good players, protect your Demon (if you are a Minion), "
                        "and cause chaos and misdirection. Lying, bluffing, and manipulation are your tools. "
                        "Identify and eliminate (or discredit) powerful good roles.\n")
            if self.role == "Poisoner": # Specific advice
                 persona += ("Strategic Note (Poisoner): Your poisoning ability is powerful for disrupting information. "
                             "Consider poisoning players who provide information (like Investigators, Fortune Tellers) to make them seem unreliable, "
                             "or players who are strong voices for the good team. Be subtle about your choices.\n")
            if self.role == "Imp": # Specific advice
                 persona += ("Strategic Note (Imp): As the Demon, your survival is paramount. Choose your night kills carefully to eliminate threats or sow distrust. "
                             "You can self-target to 'starpass' to a Minion if you are about to be executed, but only if a Minion is still alive. "
                             "Blend in, act like a Townsfolk, and use your Minions to help you control the game.\n")
        
        persona += "Always consider your role's specific abilities and how they interact with the game state and other players.\n"
        return persona

    def summarize_memory(self) -> str:
        # Basic memory summarization. Can be expanded.
        summary = "Known facts and observations:\n"
        if not self.memory:
            return summary + "  (No specific memories recorded yet.)\n"

        if self.memory.get("private_info"):
            summary += f"  Storyteller told me (private info): {self.memory['private_info']}\n"
        if self.memory.get("private_clues"):
            summary += f"  Private clues: {self.memory['private_clues']}\n"
        if self.memory.get("votes"):
            summary += f"  Recorded votes: {self.memory['votes']}\n"
        if self.memory.get("nominations"):
            summary += f"  Nominations made: {self.memory['nominations']}\n"
        if self.memory.get("important_events"):
            summary += f"  Important events: {self.memory['important_events']}\n"
        # Include a note about private chat if it exists
        if self.memory.get("private_chat_logs"):
            summary += "  You have had private conversations.\n"
        return summary

    async def decide_communication(self, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.llm or not self.status["alive"]:
            return {"type": "SILENT"} # Default to silent if no LLM or not alive

        persona_summary = self.get_persona_summary()
        
        # Create a list of other living AI players for private chat options
        other_living_ai_players = []
        if game_state.get('all_players_details'):
            for p_detail in game_state['all_players_details']:
                if p_detail['id'] != self.player_id and p_detail['is_alive'] and p_detail['id'].startswith("AIPlayer"):
                    other_living_ai_players.append(f"{p_detail['name']}(ID:{p_detail['id']})")

        comm_prompt = (
            f"{persona_summary}\n"
            "It is the Day phase. You need to decide on your communication strategy now.\n"
            "Options:\n"
            "1. PUBLIC_CHAT: Send a message to everyone. Format: PUBLIC_CHAT: [Your message here]\n"
            "2. PRIVATE_CHAT: Send a private message to one other living AI player. Format: PRIVATE_CHAT_TO: [RecipientPlayerID_from_list_below]\n[Your private message here on a new line]\n"
            "3. SILENT: Say nothing this round. Format: SILENT\n"
            f"Other living AI players available for private chat: {', '.join(other_living_ai_players) if other_living_ai_players else 'None'}.\n"
            "Think step-by-step: What are your goals? Who do you trust/suspect? Is public or private communication better now? What message will best achieve your aims?\n"
            "After your reasoning, provide your communication choice in ONE of the formats specified above."
        )

        full_prompt = self._build_prompt_context(game_state, additional_context=comm_prompt)

        try:
            response = await self._rate_limited_generate(full_prompt)
            raw_response_text = response.text.strip()
            print(f"{self.player_id} ({self.role}) Communication LLM Raw Response: {raw_response_text}")

            if raw_response_text.upper() == "SILENT":
                return {"type": "SILENT"}
            
            if raw_response_text.startswith("PUBLIC_CHAT:"):
                message = raw_response_text.split("PUBLIC_CHAT:", 1)[1].strip()
                return {"type": "PUBLIC_CHAT", "text": message}
            
            if raw_response_text.startswith("PRIVATE_CHAT_TO:"):
                lines = raw_response_text.split('\n', 1)
                recipient_line = lines[0].split("PRIVATE_CHAT_TO:", 1)[1].strip()
                message_text = lines[1].strip() if len(lines) > 1 else ""
                
                # Extract recipient_id (assuming format like "AIPlayerN(ID:AIPlayerN)" or just "AIPlayerN")
                recipient_id = recipient_line
                if "(ID:" in recipient_line and ")" in recipient_line:
                     recipient_id = recipient_line[recipient_line.find("(ID:")+4 : recipient_line.find(")")]
                
                valid_recipient_ids = [p_info.split('(ID:')[1][:-1] for p_info in other_living_ai_players if '(ID:' in p_info]
                if recipient_id in valid_recipient_ids and message_text:
                    return {"type": "PRIVATE_CHAT", "recipient_id": recipient_id, "text": message_text}
                else:
                    print(f"LLM Parse Warning for {self.player_id} Private Chat: Invalid recipient ({recipient_id}) or empty message ({message_text}).")
                    fallback_text = message_text if message_text else f"(Tried to send a private message but failed to specify recipient: {recipient_line})"
                    return {"type": "PUBLIC_CHAT", "text": fallback_text } 

            # Fallback if no clear action parsed: treat as public chat or log error
            print(f"LLM Parse Warning for {self.player_id} Communication: Could not parse intent. Treating as public chat. Raw: {raw_response_text}")
            return {"type": "PUBLIC_CHAT", "text": raw_response_text } # Default to public chat if unclear

        except Exception as e:
            print(f"Error during LLM call for {self.player_id} communication: {e}")
            return {"type": "SILENT", "error_message": str(e)} # Default to silent on error

    async def receive_private_message(self, sender_id: str, sender_name: str, message_text: str):
        """Stores a received private message in the agent's memory."""
        if "private_chat_logs" not in self.memory:
            self.memory["private_chat_logs"] = {}
        if sender_id not in self.memory["private_chat_logs"]:
            self.memory["private_chat_logs"][sender_id] = []
        
        # Get current game phase and day for timestamping/context
        # This assumes game_manager and grimoire are available and populated
        timestamp_detail = "Unknown Time"
        if self.game_manager and self.game_manager.grimoire:
            current_phase = self.game_manager.grimoire.current_phase
            day_number = self.game_manager.grimoire.day_number
            timestamp_detail = f"Day {day_number}, Phase {current_phase}"

        self.memory["private_chat_logs"][sender_id].append({
            "sender": sender_id,
            "sender_name": sender_name, 
            "text": message_text, 
            "timestamp": timestamp_detail
        })
        print(f"Agent {self.player_id} recorded private message from {sender_name} ({sender_id}).")
        # Future: Trigger agent's internal reasoning/reaction to the private message if needed immediately. 