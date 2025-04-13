# interpreter.py
import re
import google.generativeai as genai
import json  # For parsing LLM output
import config


class LLMInterpreter:  
     def __init__(self, model, world_state):
          self.llm = model
          self.world = world_state  # Need world to get rules/state for prompt

     def interpret_and_resolve_action(self, agent_name, agent_location, utterance):
          """
               Uses LLM to understand intent, check feasibility, determine outcome,
               and return structured results including the event description.
               """
          print(
               f"[LLM Interpreter @ {agent_location}]: Resolving action for {agent_name}: '{utterance}'")

          # 1. Gather Context for Prompt
          world_rules, current_state_summary = self._get_relevant_world_context(
               agent_location)

          # 2. Craft the Prompt
          prompt = self._build_resolver_prompt(
               agent_name, agent_location, utterance, world_rules, current_state_summary
          )

          # 3. Call LLM
          try:
               # Configure LLM to ideally return JSON
               # Add JSON mode if available/needed
               response = self.llm.generate_content(prompt)
               raw_output = response.text

               # 4. Parse LLM Output
               result = self._parse_llm_output(raw_output)

               # 5. Log the Outcome Event (This is what others perceive)
               if result and result.get("outcome_description"):
                    # Log the LLM-generated outcome
                    self.world.log_event(
                    result["outcome_description"],
                    scope='action_outcome',  # New scope? Or keep 'action'?
                    location=agent_location,  # Or potentially new location if move succeeded
                    triggered_by=agent_name
                    )
               else:
                    # Log a failure to interpret if parsing failed
                    self.world.log_event(
                         f"{agent_name} does something unclear ('{utterance}').",
                    scope='action_outcome',
                    location=agent_location,
                    triggered_by=agent_name
                    )
                    print(
                         f"[LLM Interpreter Error]: Failed to parse LLM output: {raw_output}")
                    return None  # Indicate failure

               # 6. Apply Direct World State Changes (if specified by LLM)
               self._apply_state_updates(
                    agent_name, result.get("world_state_update"))

               return result  # Return the full structured result for logging/debugging

          except Exception as e:
               print(f"[LLM Interpreter Error]: LLM call or parsing failed: {e}")
               # Log generic failure event
               self.world.log_event(
                    f"{agent_name}'s action ('{utterance}') seems to fail or cause confusion.",
                    scope='action_outcome',
                    location=agent_location,
                    triggered_by=agent_name
               )
               return None


     def _get_relevant_world_context(self, location):
          # Fetch rules, connectivity, properties relevant to the location
          # Example:
          rules = f"Rules: Shelter door is currently {'locked' if self.world.location_properties.get('Shelter', {}).get('door_locked') else 'unlocked'}."
          connectivity = f"From {location}, you can reach: {self.world.location_connectivity.get(location, [])}."
          # Simplified
          state_summary = f"Others present: {self.world.get_agents_at(location)}."
          # Combine relevant parts
          return rules, f"{connectivity}\n{state_summary}"

     def _build_resolver_prompt(self, agent_name, location, utterance, rules, state_summary):
          # Construct the detailed prompt asking for JSON output
          # (This needs careful design based on desired capabilities)
          prompt = f"""You are the Action Resolver for a simulation.
     Agent '{agent_name}' is at location '{location}'.
     Their intended action is: "{utterance}"

     Relevant world state and rules:
     {rules}
     {state_summary}

     Analyze the agent's intended action based on the world state. Determine if it's possible.
     Output a JSON object describing the outcome:
     {{
     "action_type": "MOVE | SPEAK | INTERACT | OBSERVE | WAIT | FAIL",
     "parameters": {{ // action-specific details, e.g., "destination": "X", "target": "Y" }},
     "success": true | false,
     "reasoning": "Brief explanation of why it succeeded or failed.", // For debugging
     "outcome_description": "A short sentence describing what actually happened as an observer would see it.",
     "world_state_update": {{ // OPTIONAL: Direct changes needed, e.g., "agent_location": "NewLoc" }}
     }}

     Example Outcome (Move success): {{"action_type": "MOVE", "parameters": {{"destination": "Park"}}, "success": true, "reasoning": "Path to Park is clear.", "outcome_description": "{agent_name} walks towards the Park.", "world_state_update": {{"agent_location": "Park"}} }}
     Example Outcome (Move fail): {{"action_type": "MOVE", "parameters": {{"destination": "Shelter"}}, "success": false, "reasoning": "Shelter door is locked.", "outcome_description": "{agent_name} tries the Shelter door, but it's locked.", "world_state_update": null }}
     Example Outcome (Speak): {{"action_type": "SPEAK", "parameters": {{"target": "Bob", "message": "Hello"}}, "success": true, "reasoning": "Bob is present.", "outcome_description": "{agent_name} says to Bob, 'Hello'.", "world_state_update": null }}

     Your JSON Output:
     ```json
     """ # Expect JSON within ```json ... ``` block
          # Note: Using ```json block helps LLM format correctly
          return prompt

     def _parse_llm_output(self, raw_output):
          try:
               # Extract JSON from potential markdown code blocks
               json_match = re.search(r'```json\s*([\s\S]+?)\s*```', raw_output)
               if json_match:
                    json_str = json_match.group(1)
               else:
                    # Assume raw output might be JSON directly if no block found
                    json_str = raw_output

               data = json.loads(json_str)
               # Basic validation (add more checks as needed)
               if 'action_type' in data and 'success' in data and 'outcome_description' in data:
                    return data
               else:
                    print("[LLM Interpreter Warning]: Parsed JSON missing required keys.")
                    return None
          except json.JSONDecodeError as e:
               print(
                    f"[LLM Interpreter Error]: JSON Decode failed: {e}. Raw output: {raw_output}")
               return None
          except Exception as e:
               print(f"[LLM Interpreter Error]: Unexpected parsing error: {e}")
               return None


     def _apply_state_updates(self, agent_name, updates):
          if not updates:
               return
          print(
               f"[LLM Interpreter]: Applying state updates for {agent_name}: {updates}")
          if "agent_location" in updates:
               new_loc = updates["agent_location"]
               # Directly update, assuming LLM validated reachability
               if new_loc in self.world.location_descriptions:
                    self.world.agent_locations[agent_name] = new_loc
                    # Note: We might need adjustment if move_agent had other side effects
               else:
                    print(
                         f"[LLM Interpreter Error]: LLM suggested moving {agent_name} to invalid location '{new_loc}'!")
          # Add handlers for other potential updates (e.g., inventory changes)
