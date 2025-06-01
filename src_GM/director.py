# File: src_GM/director.py

import re
import time
import google.generativeai as genai
import config
import random
from agent.memory import BaseMemory  # Assuming BaseMemory is in agent/memory.py
from logs import append_to_log_file
from world import Event  # For creating event objects to dispatch

from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError



class Director:
    def __init__(self, world_state_ref, planning_llm_model: genai.GenerativeModel, narrative_goal: str, memory_module: BaseMemory, event_dispatcher_ref):
        self.world = world_state_ref         # Reference to the WorldState
        self.llm = planning_llm_model      # LLM for planning interventions
        self.narrative_goal = narrative_goal
        self.memory = memory_module        # Director's own memory module
        self.event_dispatcher = event_dispatcher_ref

        # Attributes for memory system (e.g., ShortLongTMemory)
        self.name = "The Director"  # Unique name for logging, memory, and as a trigger_by
        self.goals = [f"Fulfill narrative goal: {self.narrative_goal}"]
        self.personality = "Subtle, insightful, and orchestrating."  
        self.background = "An unseen force shaping the narrative flow of this world." 
        self.gender = "entity"  
        self.identity= f"You are the Director, an unseen force guiding the narrative of this world. Your goal is to subtly influence the story's direction without direct intervention in order to fulfill the following narrative goal: {self.narrative_goal}."

        self.is_initial_prompt = False  # For debugging the first prompt

        if config.SIMULATION_MODE == 'debug':
            print(
                f"Director '{self.name}' initialized with goal: '{self.narrative_goal}', memory: {type(self.memory).__name__}, and dispatcher.")

    def perceive(self, event: Event):
        """
        The Director perceives ALL events logged in the world.
        This method will be called by the main loop for every event.
        """
        # The Director's perception is simple: it just stores the event description in its memory.
        # It doesn't need complex filtering like individual agents based on location.
        perception_text = f"You just perceived in step {event.step} of the simulation the following event at {event.location} by {event.triggered_by}: {event.description}"
        self.memory.add_observation(
            perception_text)
        if config.SIMULATION_MODE == 'debug':
            # Keep this log concise as it will happen for every event
            print(
                f"DEBUG [{self.name} PerceivedEvent]: {event.description[:70]}...")

    def plan_intervention(self): 
        """
        Uses its memory, goals, and an LLM to decide on an environmental intervention.
        Returns a string describing the intended intervention.
        """
        current_step = self.world.current_step

        # Get Director's memory context
        # Adjust parameters as needed for the Director's memory scope
        director_memory_context = self.memory.get_memory_context(
            max_short_term_entries=80, max_context_length=16000)

        # Get a concise world state summary for the prompt
        # This can be different from what individual agents get; it's for the Director's "god view."
        world_summary_for_prompt = self._get_world_summary_for_planning()

        # --- PROMPT ENGINEERING FOR DIRECTOR (same as before, ensures consistency) ---
        prompt = f"""You are '{self.name}', the Director of this simulated world.
Your primary narrative goal is: '{self.narrative_goal}'.
Your role is to very subtly guide the narrative by making changes to the environment if necessary.

Current World State Summary (as of Step {current_step}):
{world_summary_for_prompt}

Your Past Interventions and Reflections (from your memory):
{director_memory_context}

Based on your narrative goal, the current world state and  your past actions (and their outcomes from memory), what single environmental intervention will you enact next? You can change the weather or add a new object to a location, the objects must be inanimate.
Your actions are powerful but should be used judiciously to nudge the story and select carefully what action to take cause there is a limit to the amount of actions you can do.
Choose ONE action from the list below. Be precise with parameters.

Allowed Environmental Actions & Format:
1.  CHANGE_WEATHER: <new_weather_condition>
2.  ADD_OBJECT: object: <object_name>(leave details to description field) , state: <initial_state> , description: <text_desc> , location: <object_location_name>(ONLY ONE of the Existing Locations listed above)
(e.g ADD_OBJECT: object: Ancient Key , state: rusty , description: An old, rusty key with intricate engravings inside under the table. , location: Library) 
3.  DO_NOTHING: No intervention is needed right now.

Output your chosen action in the format: ACTION_TYPE: parameters

Your chosen environmental intervention (single line):"""

        if not self.is_initial_prompt and (config.SIMULATION_MODE == 'debug' or config.SIMULATION_MODE == 'only_resolver'):
            print(
                f"\n--- DIRECTOR ({self.name}) FIRST PLANNING PROMPT (Step {current_step}) ---")
            print(prompt)
            print("--------------------------------------------------------------\n")
            self.is_initial_prompt = True

        if config.SIMULATION_MODE == 'debug':
            print(f"[{self.name} Planning Intervention... Step {current_step}]")

        intervention_intent = "DO_NOTHING"  # Default
        try:
            gen_config = config.DIRECTOR_GEN_CONFIG if hasattr(
                config, 'DIRECTOR_GEN_CONFIG') else None
            response = self.llm.generate_content(
                prompt, generation_config=gen_config)
            llm_output = response.text.strip()

            known_actions = ["CHANGE_WEATHER", "CREATE_AMBIENT_EVENT",
                            "ADD_OBJECT", "DO_NOTHING"]
            if llm_output and any(llm_output.upper().startswith(action_prefix) for action_prefix in known_actions):
                intervention_intent = llm_output
            else:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"[{self.name} Warning]: LLM response '{llm_output}' not a known action. Defaulting to DO_NOTHING.")
                intervention_intent = "DO_NOTHING"

            if config.SIMULATION_MODE == 'debug':
                print(f"[{self.name} Plans To]: {intervention_intent}")

            return intervention_intent
        
        except ResourceExhausted as e:
            print(
                f"[{self.name} Error]: LLM generation failed: {e}. Waiting 10 seconds and retrying...")
            time.sleep(10)
            return self.plan_intervention()
        except Exception as e:
            print(
                f"[{self.name} Error]: LLM generation for intervention plan failed: {e}")
            if 'response' in locals() and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:  # Check if response exists
                print(
                    f"[{self.name} Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            return "DO_NOTHING"  # Fail safe

    def _get_world_summary_for_planning(self) -> str:
        """Helper to create a concise summary of the world for the Director's planning prompt."""
        summary = f"Weather: {self.world.global_context.get('weather', 'unknown')}\n"
        summary += f"Agent Locations:\n"
        for agent_name in self.world.agent_locations:
            summary += f"  - {agent_name} is in {self.world.agent_locations.get(agent_name,'Unknown')}\n"
        summary += f"Existing Locations:\n"
        for loc_name in self.world.location_descriptions:
            summary += f"  - {loc_name}\n"
        summary += "Location Details:\n"
        for loc_name in self.world.location_descriptions:
            summary += f"  - {loc_name}:\n"
            summary += f"    Description: {self.world.location_descriptions.get(loc_name, 'N/A')}\n"
            summary += f"    Exits: {self.world.location_connectivity.get(loc_name, [])}\n"
            summary += "Key Items/Objects:\n"
            items_in_loc = self.world.location_properties.get(loc_name, {}).get("contains", [])
            if items_in_loc:
                summary += f"  In {loc_name}:\n"
                for item in items_in_loc:
                    if isinstance(item, dict):
                        summary += f"    - {(item.get('optional_description') or '')}({item.get('object', 'Unnamed Object')}): {item.get('state', 'unknown state')}\n"
            else:
                summary += f"  In {loc_name}: No specific items of note.\n"
            summary += f"    Agents Here: {self.world.get_agents_at(loc_name)}\n"

        return summary.strip()

    def act(self, intervention_action_string: str):
        """
        Parses the planned intervention and DIRECTLY applies it to the world state.
        It then creates Event objects for these changes and uses the EventDispatcher
        to notify agents.
        """
        current_step = self.world.current_step
        if not intervention_action_string or intervention_action_string.upper() == "DO_NOTHING":
            if config.SIMULATION_MODE == 'debug':
                print(f"[{self.name} Acting]: No intervention taken (DO_NOTHING).")
            return

        if config.SIMULATION_MODE == 'debug':
            print(
                f"[{self.name} Acting]: Attempting to enact: {intervention_action_string}")

        action_parts = intervention_action_string.split(":", 1)
        action_type = action_parts[0].strip().upper()
        params_str = action_parts[1].strip() if len(action_parts) > 1 else ""

        # --- Perform World Modification & Prepare Event for Dispatch ---
        # The Director's `act` method will create and dispatch the event.

        event_to_dispatch: Event = None
        action_succeeded = False  # Tracks if the world modification itself was successful

        try:
            if action_type == "CHANGE_WEATHER":
                new_weather = params_str.title()
                if new_weather:
                    old_weather = self.world.global_context.get(
                        "weather", "unknown")
                    # WorldState.set_weather should just update the state and return success/failure
                    # For now, let's assume direct modification here and event creation.
                    if old_weather != new_weather:
                        self.world.global_context["weather"] = new_weather
                        action_succeeded = True
                        event_description = f"The weather changes from {old_weather} to {new_weather}."
                        event_to_dispatch = Event(
                            event_description, "Global", "global", current_step,None)
                        if config.SIMULATION_MODE == 'debug':
                            print(f"  Weather changed to {new_weather}.")
                    else:
                        if config.SIMULATION_MODE == 'debug':
                            print(f"  Weather is already {new_weather}.")
                        action_succeeded = True  # No change, but not a failure of the Director's intent

            elif action_type == "CREATE_AMBIENT_EVENT":
                params = self._parse_params(params_str)  # Use the new parser
                event_description_param = params.get("description")
                event_location_param = params.get("location")

                if event_location_param.lower() != "global":
                    scope = "local"

                if event_description_param:
                    action_succeeded = True
                    event_description = event_description_param
                    event_to_dispatch = Event(
                        event_description, event_location_param if scope == "local" else "Unknown", scope, current_step, None)
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"  Ambient event prepared: {event_description} at {event_location_param if scope == 'local' else 'Unknown'}."
                        )
                else:
                    event_description = f"Failed to create ambient event: Missing parameters in '{params_str}'. Required: description, location."
                    if config.SIMULATION_MODE == 'debug':
                        print(f"  {event_description} Parsed: {params}")

            elif action_type == "ADD_OBJECT":
                params = self._parse_params(params_str)  
                obj_name = params.get("object")
                obj_state = params.get("state")
                obj_desc = params.get("description")
                obj_location = params.get("location")

                if obj_name and obj_state and obj_desc and obj_location:
                    item_added_to_world = self.world.add_item_to_location(
                        obj_location, obj_name, obj_state, obj_desc, triggered_by=self.name)
                    if item_added_to_world:
                        action_succeeded = True
                        event_description = f"'{obj_name}' (described as: {obj_desc}, state: {obj_state}) appears in {obj_location}."
                        event_to_dispatch = Event(
                            event_description, obj_location, "local", current_step, None)
                        if config.SIMULATION_MODE == 'debug':
                            print(
                                f"  Object '{obj_name}' added to '{obj_location}'.")
                    else:
                        if config.SIMULATION_MODE == 'debug':
                            print(
                                f"  Failed to add object '{obj_name}' to '{obj_location}' (world method reported failure).")
                else:
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"  Failed to add object: Missing parameters in '{params_str}'.")
            else:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"[{self.name} Acting Warning]: Unknown or unhandled action type: '{action_type}'")

            # --- Log to Director's Memory & Dispatch Event ---
            if action_succeeded:
                self.memory.add_observation(
                    f"Action Succeeded: Enacted '{intervention_action_string}'."
                )
                if event_to_dispatch:
                    # Log the event to the world's central log first
                    if action_type != "ADD_OBJECT":
                        self.world.log_event(event_to_dispatch.description,event_to_dispatch.scope,event_to_dispatch.location,event_to_dispatch.triggered_by)
                    # Then dispatch it
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"[{self.name} Dispatching Event]: {event_to_dispatch.description[:70]}...")
                    if action_type != "ADD_OBJECT":
                        self.event_dispatcher.dispatch_event(
                            event_to_dispatch, self.world.registered_agents, self.world.agent_locations)
                    append_to_log_file(
                        "simulation_logs_with_director_logs.txt", f"""Director:\n {event_to_dispatch.description}\n\n""")
            elif action_type != "DO_NOTHING":
                self.memory.add_observation(
                    f"Action Failed: Attempted '{intervention_action_string}', but it could not be applied."
                )

        except Exception as e:
            if config.SIMULATION_MODE == 'debug':
                print(
                    f"[{self.name} Acting Error]: Exception during enacting '{intervention_action_string}': {e}")
            self.memory.add_observation(
                f"Action Error: Exception while trying to enact '{intervention_action_string}': {e}",
                step=current_step, type="InterventionError"
            )

    def _parse_params(self, params_str: str) -> dict:
        """
        Parses a comma-separated string of "key: value" pairs into a dictionary.
        - Splits pairs by commas that are followed by a 'key:' pattern.
        - For each value, if it's enclosed in double quotes, the quotes are stripped.
        """
        parsed_params = {}
        if not params_str:
            return parsed_params

        # Regex to split by: a comma (\s*,\s*)
        # IF AND ONLY IF it's followed by a key pattern (\w+\s*:)
        # Keys are assumed to be word characters (\w+).
        param_pairs = re.split(r'\s*,\s*(?=\w+\s*:)', params_str)

        for pair_str in param_pairs:
            pair_str_cleaned = pair_str.strip()
            if not pair_str_cleaned:
                continue

            parts = pair_str_cleaned.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                # raw_value_component is the string part after the first colon, stripped of its own leading/trailing whitespace.
                raw_value_component = parts[1].strip()

                # Check if the raw_value_component is entirely enclosed in double quotes
                if len(raw_value_component) >= 2 and \
                   raw_value_component.startswith('"') and \
                   raw_value_component.endswith('"'):
                    # If quoted, strip the outer quotes.
                    # The content inside the quotes is the actual value.
                    value = raw_value_component[1:-1]
                    # If unescaping of characters like \" or \\ within the quoted string is needed,
                    # it would be done here. E.g.:
                    # value = value.replace('\\"', '"').replace('\\\\', '\\')
                else:
                    # If not quoted (or not properly fully quoted), use the stripped string as is.
                    value = raw_value_component

                parsed_params[key] = value
            else:
                # This branch is hit if a segment (after splitting by comma-key pattern) doesn't contain a colon.
                if hasattr(self, 'config') and self.config.SIMULATION_MODE == 'debug':
                    print(
                        f"[{self.name} Parsing Warning]: Malformed parameter segment: '{pair_str_cleaned}' in '{params_str}'. Expected 'key: value' format.")
        return parsed_params
    
    def _parse_key_value_params(self, params_str: str) -> dict:
        """Helper to parse 'key="value", key2="value2"' style parameters."""
        params = {}
        # Regex to find key="value" pairs, handling quotes
        import re
        pattern = re.compile(r'([a-zA-Z0-9_]+)\s*=\s*"([^"]*)"')
        matches = pattern.findall(params_str)
        for key, value in matches:
            params[key] = value

        # Fallback for unquoted simple values if regex fails or for simple params
        if not params and "=" in params_str:
            try:
                for pair in params_str.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        params[key.strip()] = value.strip().strip('"')
            except ValueError:  # Handle cases where split fails badly
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"[{self.name} Parameter Parsing]: Could not fully parse '{params_str}' with simple split.")

        if not params and config.SIMULATION_MODE == 'debug' and params_str:
            print(f"[{self.name} Parameter Parsing]: Could not parse parameters from '{params_str}' using key=\"value\" or simple k=v. Returning raw.")
            # As a last resort for very simple single params like CHANGE_WEATHER: Rainy
            if ":" not in params_str and "=" not in params_str and "," not in params_str:
                # e.g. for CHANGE_WEATHER: Rainy, params_str = "Rainy"
                return {"value": params_str}
        return params

    # Renamed from 'step' to avoid confusion if we make it a true agent subclass
    def director_step(self):
        """Perform one cycle of the Director's operation: plan, act."""
        # Perception now happens for ALL events, so it's not tied to the director's "turn" to act.
        # The director's "turn" is just for planning and acting.
        if config.SIMULATION_MODE == 'debug':
            print(f"\n--- {self.name}'s Turn (Plan & Act) ---")

        planned_intervention = self.plan_intervention()
        self.act(planned_intervention)

        if config.SIMULATION_MODE == 'debug':
            print(f"--- End {self.name}'s Turn ---\n")
