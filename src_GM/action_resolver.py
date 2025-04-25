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
Output a JSON object describing the outcome:
{{
    "success": true | false,
    "action_type": "MOVE | SPEAK | INTERACT | OBSERVE | WAIT | FAIL | UNKNOWN",
    "parameters": {{ // e.g., "destination": "X", "target": "Y", "message": "..." }},
    "outcome_description": "Short sentence of what an observer sees.",
    "world_state_updates": [ // OPTIONAL: List of ['attribute', 'target', 'new_value'] tuples
        // e.g., ["agent_location", "{agent_name}", "Park"], ["location_property", "Shelter", "door_locked", false]
    ]
}}

Example (Move success): {{"success": true, "action_type": "MOVE", "parameters": {{"destination": "Park"}}, "outcome_description": "{agent_name} walks towards the Park.", "world_state_updates": [["agent_location", "{agent_name}", "Park"]] }}
Example (Move fail): {{"success": false, "action_type": "MOVE", "parameters": {{"destination": "Shelter"}}, "outcome_description": "{agent_name} tries the Shelter door, but it's locked.", "world_state_updates": [] }}
Example (Speak): {{"success": true, "action_type": "SPEAK", "parameters": {{"target": "Bob", "message": "Hello"}}, "outcome_description": "{agent_name} says to Bob, 'Hello'.", "world_state_updates": [] }}

Your JSON Output:
```json
"""

    # 3. Call LLM & Parse (Similar parsing logic as before)
        try:
            # Add JSON mode if available/needed
            response = self.llm.generate_content(
                prompt)  # Assuming self.llm is configured
            raw_output = response.text
            # Parse JSON (reuse robust parsing logic from your interpreter)
            parsed_json = self._parse_llm_output(raw_output)

            if parsed_json and 'success' in parsed_json and 'outcome_description' in parsed_json:
                # Basic validation passed
                # Ensure 'world_state_updates' is a list, default to empty if missing
                parsed_json['world_state_updates'] = parsed_json.get(
                    'world_state_updates', [])
                return parsed_json
            else:
                print(
                    f"[LLM Resolver Error]: Failed to parse or validate LLM output: {raw_output}")
                    # Return a generic failure dictionary
                return {
                        "success": False,
                    "action_type": "FAIL",
                    "parameters": {"raw_output": action_output},
                    "outcome_description": f"{agent_name} does something unclear or fails ('{action_output}').",
                    "world_state_updates": []
                    }

        except Exception as e:
            print(f"[LLM Resolver Error]: LLM call or processing failed: {e}")
            return {  # Generic failure dictionary
                "success": False, "action_type": "FAIL", "parameters": {"raw_output": action_output},
                "outcome_description": f"{agent_name}'s action ('{action_output}') causes confusion or fails.",
                "world_state_updates": []
            }

    def _parse_llm_output(self, raw_output):
        json_str = raw_output # Start with the raw output
        try:
            # Attempt to extract JSON from markdown code block first
            json_match = re.search(r'```json\s*([\s\S]+?)\s*```', raw_output, re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # If no markdown block, assume the whole output might be JSON (or needs fixing)
                # Find the first '{' and last '}' to potentially isolate JSON-like content
                start_brace = raw_output.find('{')
                end_brace = raw_output.rfind('}')
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    json_str = raw_output[start_brace:end_brace+1].strip()
                # else: keep raw_output as json_str if no braces found

            # First attempt to parse the extracted/raw string
            data = json.loads(json_str)
            
            # Ensure all required fields are present
            if 'success' in data and 'action_type' in data:
                # Add default outcome_description if missing
                if 'outcome_description' not in data:
                    agent_name = "the agent"  # Default fallback
                    action_type = data.get('action_type', 'UNKNOWN')
                    if action_type == "SPEAK" and 'parameters' in data and 'message' in data['parameters']:
                        data['outcome_description'] = f"{agent_name} says, '{data['parameters']['message']}'"
                    else:
                        data['outcome_description'] = f"{agent_name} performs a {action_type.lower()} action."
                
                # Ensure world_state_updates is a list
                if 'world_state_updates' not in data:
                    data['world_state_updates'] = []
                    
            return data

        except json.JSONDecodeError as e:
            print(f"[LLM Resolver Warning]: Initial JSON Decode failed: {e}. Attempting LLM fix...")
            print(f"--- Faulty JSON String ---\n{json_str}\n------------------------")

            # --- LLM Fix Attempt using a specialized model ---
            try:
                # Configure and instantiate a dedicated model for JSON fixing
                # Lower temperature for more deterministic output
                fixer_generation_config = {
                    "temperature": 0.1, # Low temperature for focused fixing
                    "top_p": 0.95,
                    "top_k": 50,
                    "max_output_tokens": 1024, # Allow potentially larger fixed JSON
                }
                # Assuming config.MODEL_NAME and config.SAFETY_SETTINGS are accessible
                # You might need to import 'config' if not already done in this file
                fixer_model = genai.GenerativeModel(
                    model_name=config.MODEL_NAME, # Or a specific model if desired
                    generation_config=fixer_generation_config,
                )

                # Slightly relaxed prompt, still discouraging extra text
                fix_prompt = f"""The following text is supposed to be a valid JSON object, but it failed parsing due to syntax errors. Please correct the syntax errors and output ONLY the corrected JSON object. Aim to output *only* the raw, valid JSON object itself. Do not include any explanations or apologies.

Broken JSON string:
{json_str}

Corrected JSON object:""" # Removed the explicit "Do not include ... ```json ... ```"

                # Use the specialized fixer_model
                fix_response = fixer_model.generate_content(fix_prompt)
                fixed_json_raw = fix_response.text.strip()

                # Handle potential markdown block in the fixer's response
                final_json_str = fixed_json_raw
                fixed_json_match = re.search(r'```json\s*([\s\S]+?)\s*```', fixed_json_raw, re.IGNORECASE)
                if fixed_json_match:
                     final_json_str = fixed_json_match.group(1).strip()
                # else: use the stripped raw response if no markdown block found

                print(f"--- LLM Fixer Model Suggestion ---\n{final_json_str}\n--------------------------------")
                fixed_data = json.loads(final_json_str) # Parse the potentially extracted string
                print("[LLM Resolver Info]: Successfully parsed LLM-fixed JSON.")
                return fixed_data

            except json.JSONDecodeError as fix_e:
                print(f"[LLM Resolver Error]: LLM fix failed - JSON Decode failed again: {fix_e}. Fixed attempt: {final_json_str}")
                return None
            except Exception as fix_e:
                # Catch errors during fixer model instantiation or generation
                print(f"[LLM Resolver Error]: LLM fix attempt failed with exception: {fix_e}")
                return None
            # --- End LLM Fix Attempt ---

        except Exception as e:
            # Catch any other unexpected errors during initial processing
            print(f"[LLM Resolver Error]: Unexpected parsing error before fix attempt: {e}. Raw output: {raw_output}")
            return None
