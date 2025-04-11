# interpreter.py
import re
import config # May need known locations if matching improves

def interpret_and_update(agent_name, agent_location, utterance, world_state):
    """
    Parses agent's utterance, attempts world updates, and logs the action/speech
    locally using the agent's current location.
    """
    interpreted_action_desc = f"Expressed: '{utterance}' (No specific world action interpreted)" # Default
    # --- Log the raw utterance/action LOCALLY ---
    # Use 'action' scope, tied to the agent's current location.
    # Everyone in that location will perceive this event.
    world_state.log_event(utterance,
                          scope='action',
                          location=agent_location,
                          triggered_by=agent_name)
    # --- End Logging ---

    # --- Interpretation Logic ---

    # 1. Check for movement intent
    # Regex looks for action verbs + direction + destination name
    move_match = re.search(r'\b(go|move|walk|run|head)\s+(to|towards)\s+(?:the\s+)?([\w\s]+)\b', utterance, re.IGNORECASE)
    if move_match:
        destination_phrase = move_match.group(3).strip()
        # Attempt to match the phrase against known location names
        matched_location = None
        # Make matching less strict (e.g., "Forest Edge" matches "forest")
        for loc_name in world_state.location_descriptions.keys():
            if destination_phrase.lower() in loc_name.lower() or loc_name.lower() in destination_phrase.lower():
                matched_location = loc_name
                break # Use the first plausible match

        if matched_location:
            print(f"[Interpreter]: Matched move intent from '{agent_name}' to '{matched_location}' (from phrase '{destination_phrase}')")
            # world_state.move_agent handles its own logging on success
            success, reason = world_state.move_agent(agent_name, matched_location)
            if success:
                # The move itself was logged by move_agent. Interpreter confirms.
                interpreted_action_desc = f"Successfully interpreted move to {matched_location}."
            else:
                interpreted_action_desc = f"Interpreted move intent to {matched_location}, but move failed: {reason}."
                print(f"[Interpreter @ {agent_location}]: Move failed: {reason}")
        else:
             interpreted_action_desc = f"Expressed intent to move towards '{destination_phrase}', but location unknown/unmatched."
             print(f"[Interpreter @ {agent_location}]: Move intent detected for '{destination_phrase}', but couldn't match known location.")
        return interpreted_action_desc # Movement interpretation is exclusive

    # 2. Check for speech intent (targeting another agent)
    # Regex: Looks for say/tell/ask [to] AgentName [optional punctuation] "message"
    speak_match = re.search(r'\b(say|tell|ask)\s+(?:to\s+)?([A-Za-z]+)\b.*?(?:["\'`]?)(.+)(?:["\'`]?)$', utterance, re.IGNORECASE)
    if speak_match:
         target_agent = speak_match.group(2).strip().title() # Extract target agent name
         message = speak_match.group(3).strip().strip(',.!? ') # Extract message content

         target_location = world_state.agent_locations.get(target_agent)
         if target_location == agent_location:
              interpreted_action_desc = f"Interpreted speech to {target_agent} (present): '{message}'."
              print(f"[Interpreter @ {agent_location}]: Detected speech from '{agent_name}' to present agent '{target_agent}'.")
         elif target_agent in world_state.agent_locations:
              interpreted_action_desc = f"Interpreted attempt to speak to {target_agent} (elsewhere): '{message}'."
              print(f"[Interpreter @ {agent_location}]: Speech detected to '{target_agent}', but they are in different location.")
         else:
              interpreted_action_desc = f"Interpreted attempt to speak to unknown agent '{target_agent}'."
              print(f"[Interpreter @ {agent_location}]: Speech detected to '{target_agent}', but agent name not registered.")
         return interpreted_action_desc

    # 3. Check for other common action types (for interpreter feedback, logging already done)
    if re.search(r'\b(look|examine|observe|watch|see)\b', utterance, re.IGNORECASE):
         interpreted_action_desc = f"Interpreted as an observation action ('{utterance}')."
    elif re.search(r'\b(wait|pause|stay|remain)\b', utterance, re.IGNORECASE):
         interpreted_action_desc = f"Interpreted as waiting or pausing ('{utterance}')."
    elif re.search(r'\b(think|ponder|consider|wonder|feel|realize)\b', utterance, re.IGNORECASE):
         interpreted_action_desc = f"Interpreted as expressing a thought or feeling ('{utterance}')."
    # Add more verbs like 'pick up', 'use', 'give' if you add object interaction later

    # Return the final interpretation description for this utterance
    return interpreted_action_desc