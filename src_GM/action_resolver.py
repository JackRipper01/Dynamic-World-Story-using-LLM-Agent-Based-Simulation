import google.generativeai as genai  # Keep LLM import here if resolver uses it
import json
import re
from abc import ABC, abstractmethod
from world import WorldState
import config

class BaseActionResolver(ABC):
    """
    Abstract Base Class for interpreting an agent's intended action output
    and determining its outcome within the world state.
    Different implementations will represent different validation/resolution strategies.
    """
    @abstractmethod
    def resolve(self, agent_name: str, agent_location: str, action_output: str, world_state) -> dict:
        """
        Takes the agent's raw output and the current world state,
        determines the actual outcome, and returns a structured result.

        Args:
            agent_name: Name of the agent attempting the action.
            agent_location: Location of the agent when attempting the action.
            action_output: The raw output from the agent's thinking module.
            world_state: Reference to the current WorldState.

        Returns:
            A dictionary containing resolution details, e.g.:
            {
                "success": bool,
                "action_type": "MOVE" | "SPEAK" | "INTERACT" | "OBSERVE" | "WAIT" | "FAIL" | "UNKNOWN",
                "parameters": dict, # Action specific details derived by the resolver
                "outcome_description": str, # What an observer sees happen
                # List of direct state changes, e.g., [('agent_location', agent_name, 'NewLoc'), ('lock_state', 'ShelterDoor', False)]
                "world_state_updates": list,
            }
            Return None or a dict with success=False if resolution fails severely.
        """
        pass

# --- Concrete Implementation (Moves logic from LLMInterpreter) ---

class LLMActionResolver(BaseActionResolver):
    """
    Uses an LLM to interpret natural language action output, validate it
    against world rules (potentially simplified), and generate an outcome.
    (Based on the original LLMInterpreter logic)
    """

    def __init__(self, model, world_state_ref_for_prompting_rules=None):
        self.llm = model
        # Might need a way to get *some* world info for the prompt,
        # but avoid passing the full mutable state if possible.
        # Maybe pass specific rule functions or data? For now, keep it simple.
        self.world_ref = world_state_ref_for_prompting_rules  # Use carefully

    def resolve(self, agent_name: str, agent_location: str, action_output: str, world_state:WorldState) -> dict:
        if config.SIMULATION_MODE == 'debug' or config.SIMULATION_MODE == 'only_resolver':
            print(
                f"[LLM Resolver @ {agent_location}]: Resolving for {agent_name}: '{action_output}'")

        # 1. Gather Context (Simplified example - adapt as needed)
        # This part needs careful design - what *minimal* context does the resolver need?
        # Avoid giving it the full dynamic event history if possible.
        # rules = f"Rules: Shelter door currently {world_state.get_location_property('Shelter', 'door_locked')}."
        connectivity = f"From {agent_location}, exits lead to: {world_state.get_reachable_locations(agent_location)}."
        agents_present = world_state.get_agents_at(agent_location)
        others_present = [
            name for name in agents_present if name != agent_name]
        state_summary = f"Others present: {others_present if others_present else 'None'}."

        # 2. Craft Prompt (Similar to old Interpreter prompt, but focused on resolution)
        prompt = f"""You are the Action Resolver for a simulation.
Agent '{agent_name}' at location '{agent_location}' intends to: "{action_output}"

Relevant world state and rules:
{connectivity}
{state_summary}
Weather: {world_state.global_context.get('weather', 'Clear')}

Analyze the agent's intent. Is it possible? What is the most plausible outcome?
Your task is to determine if the action is successful, what type of action it is, any key parameters, and a brief description of what an observer would see.

Output your analysis as a single line of text with exactly four parts, separated by " | " (a pipe symbol with spaces around it):
1.  Success Status: Either "SUCCESS" or "FAILURE".
2.  Action Type: One of MOVE, SPEAK, INTERACT, OBSERVE, WAIT, FAIL, UNKNOWN.
3.  Parameters: Key details for the action.
    - For MOVE: "destination: <location_name>"
    - For SPEAK: "target: <character_name>, message: <text_of_message>"
    - For INTERACT: "object: <object_name>, details: <brief_description_of_interaction>"
    - For OBSERVE: "target: <what_is_observed>"
    - For WAIT: "duration: <e.g., a moment, briefly>"
    - For FAIL or UNKNOWN: This part can be a brief reason for failure/unknown, or left empty if the reason is clear from the outcome description.
4.  Outcome Description: A short sentence describing what an observer sees happen.

Examples of the single-line output format:
Intent: "go to the park" -> SUCCESS | MOVE | destination: Park | {agent_name} walks towards the Park.
Intent: "try to open shelter door" (if door is locked) -> FAILURE | INTERACT | object: Shelter Door, details: attempt open | {agent_name} tries the Shelter door, but it's locked.
Intent: "say hello to Bob" -> SUCCESS | SPEAK | target: Bob, message: Hello | {agent_name} says to Bob, 'Hello'.
Intent: "look around" -> SUCCESS | OBSERVE | target: surroundings | {agent_name} looks around.
Intent: "wait a moment" -> SUCCESS | WAIT | duration: a moment | {agent_name} waits.
Intent: "fly to the moon" (if impossible) -> FAILURE | FAIL | reason: impossible action | {agent_name} attempts an impossible action.

Ensure your output is a single line in this exact format:
SUCCESS_STATUS | ACTION_TYPE | PARAMETERS | OUTCOME_DESCRIPTION
Your single-line output:
"""

        # 3. Call LLM & Parse
        try:
            response = self.llm.generate_content(prompt)
            raw_output = response.text.strip()

            if config.SIMULATION_MODE == 'debug' or config.SIMULATION_MODE == 'only_resolver':
                print(f"[LLM Resolver Raw Output]: '{raw_output}'")

            parts = raw_output.split(" | ")
            if len(parts) == 4:
                success_str, action_type_str, params_str, outcome_desc_str = parts

                # Initialize the result dictionary
                resolved_action = {
                    "success": success_str.upper() == "SUCCESS",
                    "action_type": action_type_str.upper(),
                    "parameters": {},  # We will populate this next
                    "outcome_description": outcome_desc_str.strip(),
                    "world_state_updates": []  # We will populate this later if possible
                }

                # --- Start: Parse Parameters String ---
                action_params = {}
                if params_str.strip():  # Only parse if params_str is not empty
                    # General parsing for "key: value, key2: value2" format
                    param_pairs = params_str.split(',')
                    for pair in param_pairs:
                        pair = pair.strip()
                        if ':' in pair:
                            key, value = pair.split(':', 1)
                            action_params[key.strip()] = value.strip()
                        elif resolved_action["action_type"] in ["FAIL", "UNKNOWN"] and not action_params.get("reason"):
                            # For FAIL/UNKNOWN, if no key:value, assume the whole string is a reason
                            action_params["reason"] = pair
                        elif resolved_action["action_type"] == "OBSERVE" and not action_params.get("target"):
                            # For OBSERVE, if it's just a value, assume it's the target
                            action_params["target"] = pair

                resolved_action["parameters"] = action_params
                # --- End: Parse Parameters String ---

                return resolved_action
            else:
                print(
                    f"[LLM Resolver Error]: LLM output not in expected format (SUCCESS | TYPE | PARAMS | OUTCOME_DESC). Output: {raw_output}"
                )
                return {
                    "success": False,
                    "action_type": "FAIL",
                    "parameters": {"raw_output": action_output, "llm_response": raw_output},
                    "outcome_description": f"{agent_name} provides an unclear response ('{raw_output}').",
                    "world_state_updates": []
                }

        except Exception as e:
            print(f"[LLM Resolver Error]: LLM call or processing failed: {e}")
            return {  # Generic failure dictionary
                "success": False, "action_type": "FAIL", "parameters": {"raw_output": action_output},
                "outcome_description": f"{agent_name}'s action ('{action_output}') causes confusion or fails.",
                "world_state_updates": []
            }

