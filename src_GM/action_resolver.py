import time
from django import conf
import google.generativeai as genai  # Keep LLM import here if resolver uses it
import json
import re
from abc import ABC, abstractmethod
from world import WorldState
import config
try:
    # Also catch general API errors
    from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
except ImportError:
    # Provide fallback or raise an error if the necessary library is not installed
    print("Warning: google-api-core not installed. API error handling may not work correctly.")

    class ResourceExhausted(Exception):
        pass  # Define a dummy exception if import fails

    class GoogleAPICallError(Exception):
        pass  # Define a dummy exception if import fails


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

    def resolve(self, agent_name: str, agent_location: str, action_output: str, world_state: WorldState) -> dict:
        if config.SIMULATION_MODE == 'debug' or config.SIMULATION_MODE == 'only_resolver':
            print(
                f"[LLM Resolver @ {agent_location}]: Resolving for {agent_name}: '{action_output}'\n")

        # 1. Craft Prompt (Similar to old Interpreter prompt, but focused on resolution)
        prompt = f"""You are the Action Resolver for a simulation.
Agent '{agent_name}' at location '{agent_location}' intends to: "{action_output}"

This is what the agent '{agent_name}' senses about the world:
{world_state.get_static_context_for_agent(agent_name)}

Analyze the agent's intent. 
Is it possible? 
What is the most plausible outcome?
Your task is to determine if the action is successful, what type of action it is, any key parameters, and a description of what a close observer would see or hear or both.

Output your analysis as a single line of text with exactly four parts, separated by " | " (a pipe symbol with spaces around it):
1.  Success Status: Either "SUCCESS" or "FAILURE".
2.  Action Type: One of MOVE, SPEAK, INTERACT, OBSERVE, WAIT, FAIL, UNKNOWN.
3.  Parameters: Key details for the action.
    - For MOVE: "destination: <location_name>"
    - For SPEAK: "target: <character_name>, message: <text_of_message>" (Very important here to put in the message field the exact words the agent is saying)
    - For INTERACT: "object: <object_name>, state: <new_state_of_object_after_interaction>" (If FAILURE, 'state' should reflect the current unchanged state that caused failure, e.g., 'state: locked')
    - For OBSERVE: "target: <what_is_observed>"
    - For WAIT: "duration: <e.g., a moment, briefly>"
    - For FAIL or UNKNOWN: This part can be a brief reason for failure/unknown, or left empty if the reason is clear from the outcome description.
4.  Outcome Description: A sentence describing what an observer sees happen.

Examples of the single-line output format:
Intent: "go to the park" -> SUCCESS | MOVE | destination: Park | {agent_name} walks towards the Park.
Intent: "unlock the lab door with a key" (if key is present and door is lockable) -> SUCCESS | INTERACT | object: Lab Door, state: unlocked | {agent_name} unlocks the Lab Door.
Intent: "try to open shelter door" (if door is locked) -> FAILURE | INTERACT | object: Shelter Door, state: locked | {agent_name} tries the Shelter door, but it's locked.
Intent: "say hello to Bob waiving my hand" -> SUCCESS | SPEAK | target: Bob, message: "Waiving my hand to Bob, I say Hello" | {agent_name} says to Bob, 'Hello', waving her hand.
Intent: "look around" -> SUCCESS | OBSERVE | target: surroundings | {agent_name} looks around.
Intent: "wait a moment" -> SUCCESS | WAIT | duration: a moment | {agent_name} waits.
Intent: "fly to the moon" (if impossible) -> FAILURE | FAIL | reason: impossible action | {agent_name} attempts an impossible action.

Ensure your output is a single line in this exact format:
SUCCESS_STATUS | ACTION_TYPE | PARAMETERS | OUTCOME_DESCRIPTION
Your single-line output:
"""

        # 2. Call LLM & Parse
        try:
            response = self.llm.generate_content(prompt)
            raw_output = response.text.strip()

            if config.SIMULATION_MODE == 'debug' or config.SIMULATION_MODE == 'only_resolver':
                print(f"[LLM Resolver Raw Output]: '{raw_output}'\n")

            parts = raw_output.split(" | ")
            if len(parts) == 4:
                success_str, action_type_str, params_str, llm_outcome_desc_str = parts

                # Initialize the result dictionary
                resolved_action = {
                    "success": success_str.upper() == "SUCCESS",
                    "action_type": action_type_str.strip().upper(),  # Ensure stripped and upper
                    "parameters": {},
                    "outcome_description": llm_outcome_desc_str.strip(),
                    "world_state_updates": []
                }

                # --- Start: Simplified Targeted Parameter Parsing ---
                action_params = {}
                text_to_parse = params_str.strip()
                # action_type_upper is already set in resolved_action["action_type"]

                # (Existing parameter parsing logic - condensed for brevity)
                if text_to_parse:
                    # Use the one from resolved_action
                    current_action_type_for_param_parsing = resolved_action["action_type"]
                    if current_action_type_for_param_parsing == "SPEAK":
                        message_key = "message:"
                        message_idx = text_to_parse.lower().find(message_key.lower())
                        if message_idx != -1:
                            action_params["message"] = text_to_parse[message_idx +
                                                                     len(message_key):].strip()
                            target_part_str = text_to_parse[:message_idx].strip(
                            )
                            target_key = "target:"
                            if target_part_str.lower().startswith(target_key.lower()):
                                target_value = target_part_str[len(
                                    target_key):].strip()
                                if target_value.endswith(','):
                                    target_value = target_value[:-1].strip()
                                action_params["target"] = target_value
                        else:
                            print(
                                f"[LLM Resolver Warning] SPEAK action params missing 'message:': '{text_to_parse}'")
                    elif current_action_type_for_param_parsing == "INTERACT":
                        state_key = "state:"
                        state_idx = text_to_parse.lower().find(state_key.lower())
                        if state_idx != -1:
                            action_params["state"] = text_to_parse[state_idx +
                                                                     len(state_key):].strip()
                            object_part_str = text_to_parse[:state_idx].strip(
                            )
                            object_key = "object:"
                            if object_part_str.lower().startswith(object_key.lower()):
                                object_value = object_part_str[len(
                                    object_key):].strip()
                                if object_value.endswith(','):
                                    object_value = object_value[:-1].strip()
                                action_params["object"] = object_value
                        elif text_to_parse.lower().startswith("object:"):
                            remaining_after_object_key = text_to_parse[len(
                                "object:"):]
                            comma_after_object_val = remaining_after_object_key.find(
                                ',')
                            if comma_after_object_val != -1:
                                action_params["object"] = remaining_after_object_key[:comma_after_object_val].strip(
                                )
                                other_params_str = remaining_after_object_key[comma_after_object_val+1:].strip(
                                )
                                if other_params_str:
                                    simple_pairs = other_params_str.split(',')
                                    for pair_str in simple_pairs:
                                        if ':' in pair_str:
                                            k, v = pair_str.split(':', 1)
                                            action_params[k.strip()
                                                          ] = v.strip()
                            else:
                                action_params["object"] = remaining_after_object_key.strip(
                                )
                        elif ':' in text_to_parse:  # Generic split for INTERACT if no "details:" or "object:"
                            kv_pairs = text_to_parse.split(',')
                            for pair_str in kv_pairs:
                                if ':' in pair_str:
                                    k, v = pair_str.split(':', 1)
                                    action_params[k.strip()] = v.strip()
                    elif current_action_type_for_param_parsing == "MOVE":
                        if text_to_parse.lower().startswith("destination:"):
                            action_params["destination"] = text_to_parse[len(
                                "destination:"):].strip()
                    elif current_action_type_for_param_parsing == "OBSERVE":
                        if text_to_parse.lower().startswith("target:"):
                            action_params["target"] = text_to_parse[len(
                                "target:"):].strip()
                        else:
                            action_params["target"] = text_to_parse
                    elif current_action_type_for_param_parsing == "WAIT":
                        if text_to_parse.lower().startswith("duration:"):
                            action_params["duration"] = text_to_parse[len(
                                "duration:"):].strip()
                        else:
                            action_params["duration"] = text_to_parse
                    elif current_action_type_for_param_parsing in ["FAIL", "UNKNOWN"]:
                        if text_to_parse.lower().startswith("reason:"):
                            action_params["reason"] = text_to_parse[len(
                                "reason:"):].strip()
                        else:
                            action_params["reason"] = text_to_parse

                    if not action_params and text_to_parse and \
                       current_action_type_for_param_parsing not in ["OBSERVE", "WAIT", "FAIL", "UNKNOWN", "SPEAK", "INTERACT", "MOVE"]:
                        print(
                            f"[LLM Resolver Warning] Could not parse parameters for {current_action_type_for_param_parsing}: '{text_to_parse}' using targeted logic. Trying generic split.")
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

                # --- START: Specific Action Validation and World State Update Generation ---
                action_type_upper = resolved_action["action_type"]
                
                # Cache LLM's initial assessment
                llm_says_move_successful = resolved_action["success"]
                
                if action_type_upper == "MOVE":
                    destination = action_params.get("destination")

                    if not destination:
                        resolved_action["success"] = False
                        resolved_action["outcome_description"] = f"{agent_name} intends to move, but no destination was specified in the parameters."
                        # world_state_updates remains empty for the move
                    elif destination == agent_location:
                        resolved_action["success"] = True
                    elif destination not in world_state.location_descriptions:
                        objects_in_destination = world_state.get_location_property(
                            agent_location, "contains")
                        if config.SIMULATION_MODE == 'debug':
                            print(f"[LLM Resolver Debug]: Checking if '{destination}' is an object in {agent_location}") 
                            print(f"[LLM Resolver Debug]: Objects in {agent_location}: {objects_in_destination}")
                        
                        destination_is_object = False
                        #check if destination is a object in the agent's location where objects_in_destination is a list of dictionaries 
                        # e.g [{'object': 'sofas and chairs', 'state': 'occupied by suspects', 'optional_description': 'Plush velvet sofas and armchairs where the remaining occupants of the manor are gathered.'}, {'object': 'coffee table', 'state': 'scattered tea cups', 'optional_description': 'A round]
                        #your code goes here
                        if isinstance(objects_in_destination, list):
                            for item_data in objects_in_destination:
                                if isinstance(item_data, dict) and item_data.get("object") == destination:
                                    destination_is_object = True
                                    break
                        # If destination is not a known location and not an object in the current location
                        if destination_is_object is False:
                            resolved_action["success"] = False
                            resolved_action["outcome_description"] = f"{agent_name} tries to move to '{destination}', but it is not a known location."
                        else:
                            resolved_action["success"] = True
                            
                        # world_state_updates remains empty for the move
                    elif destination not in world_state.get_reachable_locations(agent_location):
                        resolved_action["success"] = False
                        resolved_action["outcome_description"] = f"{agent_name} tries to move to '{destination}' from {agent_location}, but there is no direct path."
                        # world_state_updates remains empty for the move
                    else:
                        # Destination is valid, known, and reachable.
                        # Proceed with the move only if the LLM *also* considered it a success.
                        if llm_says_move_successful:
                            # Confirm/ensure success
                            resolved_action["success"] = True
                            resolved_action["world_state_updates"].append(
                                ('agent_location', agent_name, destination)
                            )
                        else:
                            pass  # No changes needed, LLM's failure stands

                elif action_type_upper == "INTERACT":
                    if llm_says_move_successful:  # Only process if LLM thinks it's a success
                        object_name = action_params.get("object")
                        # LLM should provide the *new* state
                        new_object_state = action_params.get("state")

                        if not object_name:
                            resolved_action["success"] = False
                            resolved_action["outcome_description"] = f"{agent_name} intends to interact, but no object was specified in parameters."
                        elif new_object_state is None:  # Check for None, empty string is a valid state
                            resolved_action["success"] = True
                        else:
                            # Verify the object exists in the agent's current location
                            current_location_items = world_state.get_location_property(
                                agent_location, "contains")
                            item_found_in_location = False
                            if isinstance(current_location_items, list):
                                for item_data in current_location_items:
                                    if isinstance(item_data, dict) and item_data.get("object") == object_name:
                                        item_found_in_location = True
                                        # Object found, create update for its state
                                        resolved_action["world_state_updates"].append(
                                            ('item_state', agent_location,
                                            object_name, new_object_state)
                                        )
                                        # LLM's outcome_description is generally used.
                                        # Optionally, refine if needed:
                                        # resolved_action["outcome_description"] = f"{agent_name} interacts with {object_name}, changing its state to '{new_object_state}'."
                                        break  # Item found and update added

                            if not item_found_in_location:
                                resolved_action["success"] = True
                                # resolved_action[
                                #     "outcome_description"] = f"{agent_name} tries to interact with '{object_name}', but it's not found at their current location ({agent_location})."
                                # Clear any pending updates if item not found
                                resolved_action["world_state_updates"] = []
                    # If llm_says_action_successful was False, we keep it as False.
                    # The outcome_description from the LLM should explain why (e.g., "object: Door, state: locked").
                    # No world_state_updates for item_state if LLM initially said FAILURE
                    
                # --- END: Specific Action Validation ---

                # --- Refine outcome_description, especially for SPEAK actions (AFTER MOVE validation) ---
                if resolved_action["action_type"] == "SPEAK" and resolved_action["success"]:
                    msg = action_params.get("message", "")
                    target_agent = action_params.get(
                        "target")  # Renamed to avoid conflict

                    if msg:
                        if target_agent:
                            if target_agent in world_state.get_agents_at(agent_location):
                                resolved_action["outcome_description"] = f"{agent_name} to {target_agent}, \"{msg}\""
                            else: # Optional: if LLM gives message but no target
                                resolved_action["outcome_description"] = f"{agent_name} (if talking to an existing character then it is not in range to hear {agent_name}) : \"{msg}\""
                            
                        

                print(f"[LLM Resolver Final Output]: {resolved_action}")
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
        except ResourceExhausted as e:
            print(
                f"[{self.name} Error]: LLM generation failed: {e}. Waiting 10 seconds and retrying...")
            time.sleep(10)
            return self.resolve(agent_name, agent_location, action_output, world_state)
        
        except Exception as e:
            print(f"[LLM Resolver Error]: LLM call or processing failed: {e}")
            # Check for response object and prompt feedback if available
            feedback_info = ""
            if 'response' in locals() and hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                feedback_info = f" (Safety Feedback: {response.prompt_feedback})"

            return {
                "success": False, "action_type": "FAIL", "parameters": {"raw_output": action_output, "error": str(e)},
                "outcome_description": f"{agent_name}'s action ('{action_output}') causes confusion or fails.{feedback_info}",
                "world_state_updates": []
            }
