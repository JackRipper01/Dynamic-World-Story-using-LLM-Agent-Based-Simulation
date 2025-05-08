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
                success_str, action_type_str, params_str, llm_outcome_desc_str = parts

                current_action_type = action_type_str.strip().upper()
                
                # Initialize the result dictionary
                resolved_action = {
                    "success": success_str.upper() == "SUCCESS",
                    "action_type": action_type_str.upper(),
                    "parameters": {},  # We will populate this next
                    "outcome_description": llm_outcome_desc_str.strip(),
                    "world_state_updates": []  # We will populate this later if possible
                }

                # --- Start: Simplified Targeted Parameter Parsing ---
                action_params = {}
                text_to_parse = params_str.strip()
                action_type_upper = resolved_action["action_type"].upper()

                if text_to_parse:
                    if action_type_upper == "SPEAK":
                        # Expect: "target: <value>, message: <actual message content>"
                        # The message is everything after "message:"
                        message_key = "message:"
                        # Use find, not rfind if message is always last
                        message_idx = text_to_parse.lower().find(message_key.lower())

                        if message_idx != -1:
                            action_params["message"] = text_to_parse[message_idx +
                                                                     len(message_key):].strip()

                            # The part before "message:" is the target part
                            target_part_str = text_to_parse[:message_idx].strip(
                            )
                            target_key = "target:"
                            if target_part_str.lower().startswith(target_key.lower()):
                                # Remove the "target:" prefix and any trailing comma
                                target_value = target_part_str[len(
                                    target_key):].strip()
                                if target_value.endswith(','):
                                    target_value = target_value[:-1].strip()
                                action_params["target"] = target_value
                            # If target_part_str is not empty but doesn't start with "target:", it's unassigned.
                            # Or if the LLM only provided "message: ..."
                        else:
                            # No "message:" found. LLM didn't follow format.
                            # We could try to see if it's just a target, or just a message.
                            # For now, if "message:" is missing for SPEAK, params might be incomplete.
                            print(
                                f"[LLM Resolver Warning] SPEAK action params missing 'message:': '{text_to_parse}'")

                    elif action_type_upper == "INTERACT":
                        # Expect: "object: <value>, details: <actual details content>" (if details can have commas)
                        # Or simply "object: <value>" or "object: <value>, some_other_simple_param: <value>"
                        details_key = "details:"
                        details_idx = text_to_parse.lower().find(details_key.lower())

                        if details_idx != -1:
                            action_params["details"] = text_to_parse[details_idx +
                                                                     len(details_key):].strip()
                            object_part_str = text_to_parse[:details_idx].strip(
                            )
                            object_key = "object:"
                            if object_part_str.lower().startswith(object_key.lower()):
                                object_value = object_part_str[len(
                                    object_key):].strip()
                                if object_value.endswith(','):
                                    object_value = object_value[:-1].strip()
                                action_params["object"] = object_value
                        elif text_to_parse.lower().startswith("object:"):  # No "details:", try to get "object:"
                            # Handle cases like "object: Door" or "object: Lever, state: on"
                            # This simple logic assumes "object:" is the first param if "details:" isn't present.
                            # If there are other params after "object:" and before an unkeyed detail, this needs more.
                            # For now, let's assume if no "details:", the first key:value pair is object,
                            # or if multiple simple key:value pairs, split by comma.

                            # If "object:" is present, and maybe other simple params:
                            temp_object_params_str = text_to_parse  # Start with the full string
                            if temp_object_params_str.lower().startswith("object:"):
                                # Try to extract object first
                                remaining_after_object_key = temp_object_params_str[len(
                                    "object:"):]
                                # Find where the object value ends (e.g., at a comma for the next param)
                                comma_after_object_val = remaining_after_object_key.find(
                                    ',')
                                if comma_after_object_val != -1:
                                    action_params["object"] = remaining_after_object_key[:comma_after_object_val].strip(
                                    )
                                    # Process other simple key:value pairs after the object
                                    other_params_str = remaining_after_object_key[comma_after_object_val+1:].strip(
                                    )
                                    if other_params_str:
                                        simple_pairs = other_params_str.split(
                                            ',')
                                        for pair_str in simple_pairs:
                                            if ':' in pair_str:
                                                k, v = pair_str.split(':', 1)
                                                action_params[k.strip(
                                                )] = v.strip()
                                else:  # No comma, object value is the rest of the string
                                    action_params["object"] = remaining_after_object_key.strip(
                                    )
                        else:  # No "details:" and no "object:", try a generic split
                            if ':' in text_to_parse:
                                kv_pairs = text_to_parse.split(',')
                                for pair_str in kv_pairs:
                                    if ':' in pair_str:
                                        k, v = pair_str.split(':', 1)
                                        action_params[k.strip()] = v.strip()

                    # For simpler actions that expect a single key:value or just a value
                    elif action_type_upper == "MOVE":
                        if text_to_parse.lower().startswith("destination:"):
                            action_params["destination"] = text_to_parse[len(
                                "destination:"):].strip()
                    elif action_type_upper == "OBSERVE":
                        if text_to_parse.lower().startswith("target:"):
                            action_params["target"] = text_to_parse[len(
                                "target:"):].strip()
                        else:
                            # Assume whole string is target
                            action_params["target"] = text_to_parse
                    elif action_type_upper == "WAIT":
                        if text_to_parse.lower().startswith("duration:"):
                            action_params["duration"] = text_to_parse[len(
                                "duration:"):].strip()
                        else:
                            # Assume whole string is duration
                            action_params["duration"] = text_to_parse
                    elif action_type_upper in ["FAIL", "UNKNOWN"]:
                        if text_to_parse.lower().startswith("reason:"):
                            action_params["reason"] = text_to_parse[len(
                                "reason:"):].strip()
                        else:
                            # Assume whole string is reason
                            action_params["reason"] = text_to_parse

                    # If after all specific parsing attempts, action_params is still empty but text_to_parse is not,
                    # and it's not one of the types that can take the whole string as a default param (OBSERVE, WAIT, FAIL, UNKNOWN)
                    # it means the format was unexpected for the given action type.
                    if not action_params and text_to_parse and \
                       action_type_upper not in ["OBSERVE", "WAIT", "FAIL", "UNKNOWN", "SPEAK", "INTERACT", "MOVE"]:  # Only log if not handled by above
                        print(
                            f"[LLM Resolver Warning] Could not parse parameters for {action_type_upper}: '{text_to_parse}' using targeted logic. Trying generic split.")
                        # Generic fallback if nothing specific matched (less robust for values with commas)
                        if ':' in text_to_parse:
                            try:
                                kv_pairs = text_to_parse.split(',')
                                for pair_str in kv_pairs:
                                    if ':' in pair_str:
                                        k, v = pair_str.split(':', 1)
                                        action_params[k.strip()] = v.strip()
                            except Exception as e:
                                print(
                                    f"[LLM Resolver Error] Generic param parsing failed: {e}")

                resolved_action["parameters"] = action_params
                # --- End: Simplified Targeted Parameter Parsing ---

                # --- Refine outcome_description, especially for SPEAK actions ---
                if resolved_action["action_type"] == "SPEAK" and resolved_action["success"]:
                    # We have already parsed parameters into action_params
                    # Get the message, default to empty string if not found
                    msg = action_params.get("message", "")
                    # Get the target, could be None
                    target = action_params.get("target")

                    if msg:  # Only construct if there's a message
                        if target:
                            resolved_action["outcome_description"] = f"{agent_name} says to {target}, \"{msg}\""
                            
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

