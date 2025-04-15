import google.generativeai as genai  # Keep LLM import here if resolver uses it
import json
import re
from abc import ABC, abstractmethod
from world import WorldState

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
                "reasoning": str, # Explanation (optional)
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
    "reasoning": "Brief explanation.",
    "outcome_description": "Short sentence of what an observer sees.",
    "world_state_updates": [ // OPTIONAL: List of ['attribute', 'target', 'new_value'] tuples
        // e.g., ["agent_location", "{agent_name}", "Park"], ["location_property", "Shelter", "door_locked", false]
    ]
}}

Example (Move success): {{"success": true, "action_type": "MOVE", "parameters": {{"destination": "Park"}}, "reasoning": "Path is clear.", "outcome_description": "{agent_name} walks towards the Park.", "world_state_updates": [["agent_location", "{agent_name}", "Park"]] }}
Example (Move fail): {{"success": false, "action_type": "MOVE", "parameters": {{"destination": "Shelter"}}, "reasoning": "Door is locked.", "outcome_description": "{agent_name} tries the Shelter door, but it's locked.", "world_state_updates": [] }}
Example (Speak): {{"success": true, "action_type": "SPEAK", "parameters": {{"target": "Bob", "message": "Hello"}}, "reasoning": "Bob is present.", "outcome_description": "{agent_name} says to Bob, 'Hello'.", "world_state_updates": [] }}

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
                    "reasoning": "Failed to interpret action via LLM.",
                    "outcome_description": f"{agent_name} does something unclear or fails ('{action_output}').",
                    "world_state_updates": []
                    }

        except Exception as e:
            print(f"[LLM Resolver Error]: LLM call or processing failed: {e}")
            return {  # Generic failure dictionary
                "success": False, "action_type": "FAIL", "parameters": {"raw_output": action_output},
                "reasoning": f"LLM exception: {e}",
                "outcome_description": f"{agent_name}'s action ('{action_output}') causes confusion or fails.",
                "world_state_updates": []
            }

    # Add the _parse_llm_output helper method here (copied from your interpreter)
    def _parse_llm_output(self, raw_output):
        try:
            json_match = re.search(r'```json\s*([\s\S]+?)\s*```', raw_output)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = raw_output
            data = json.loads(json_str)
            # Add more validation if needed
            return data
        except json.JSONDecodeError as e:
            print(f"[LLM Resolver Error]: JSON Decode failed: {e}. Raw output: {raw_output}")
            return None
        except Exception as e:
            print(f"[LLM Resolver Error]: Unexpected parsing error: {e}")
            return None
