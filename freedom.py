import google.generativeai as genai
import os
import time
import re 
from dotenv import load_dotenv
from collections import defaultdict

# --- Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found. Make sure it's set in the .env file.")
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
  "temperature": 1,         
  "top_p": 0.95,
  "top_k": 50,               
  "max_output_tokens": 150,   
}
safety_settings = [ # Keep safety settings
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
model = genai.GenerativeModel(model_name="gemini-2.0-flash-lite", 
                              generation_config=generation_config,
                              safety_settings=safety_settings)

# --- World State ---
class WorldState:
    def __init__(self):
        self.agent_locations = {} # agent_name -> location_name
        self.location_descriptions = { # Basic descriptions
            "Park": "A wide open park area with some trees.",
            "Shelter": "A simple wooden shelter.",
            "Forest Edge": "The edge of a dark forest."
        }
        self.global_context = {"weather": "Clear"}
        # Store recent events/utterances for context
        self.recent_events = [] # List of strings describing what happened

    def add_agent(self, agent_name, location_name):
        if location_name in self.location_descriptions:
            self.agent_locations[agent_name] = location_name
            self.log_event(f"{agent_name} appears in the {location_name}.")
        else:
            print(f"Warning: Cannot add {agent_name} to unknown location '{location_name}'")

    def move_agent(self, agent_name, new_location):
        if agent_name not in self.agent_locations:
            print(f"Warning: Cannot move unknown agent '{agent_name}'")
            return False
        if new_location not in self.location_descriptions:
            print(f"Warning: Cannot move {agent_name} to unknown location '{new_location}'")
            return False

        old_location = self.agent_locations[agent_name]
        if old_location != new_location:
            self.agent_locations[agent_name] = new_location
            self.log_event(f"{agent_name} moved from {old_location} to {new_location}.")
            return True
        return False # Didn't actually move

    def get_agents_at(self, location_name):
        return [name for name, loc in self.agent_locations.items() if loc == location_name]

    def log_event(self, event_description):
        print(f"[World Event]: {event_description}")
        self.recent_events.append(event_description)
        # Keep event log from growing infinitely
        if len(self.recent_events) > 15:
            self.recent_events.pop(0)

    def get_context_for_agent(self, agent_name):
        if agent_name not in self.agent_locations:
            return "You are currently nowhere." # Should not happen ideally

        location = self.agent_locations[agent_name]
        description = f"You ({agent_name}) are in the {location}. Description: {self.location_descriptions.get(location, 'An unknown area.')}\n"
        description += f"Current conditions: Weather is {self.global_context.get('weather', 'unknown')}.\n"

        other_agents = [name for name in self.get_agents_at(location) if name != agent_name]
        if other_agents:
            description += f"Others present: {', '.join(other_agents)}.\n"
        else:
            description += "You are alone here.\n"

        # Add recent relevant events 
        if self.recent_events:
             description += "Recent happenings:\n - " + "\n - ".join(self.recent_events[-5:]) # Show last 5 events

        return description.strip()

    def get_full_state_string(self):
        state = f"--- World State ---\n"
        state += f"Global Context: {self.global_context}\n"
        state += f"Agent Locations: {self.agent_locations}\n"
        state += f"Recent Events ({len(self.recent_events)}):\n"
        for event in self.recent_events[-5:]: # Show last 5
            state += f"  - {event}\n"
        return state + "-------------------"

# --- Agent Class ---
class FreeAgent:
    def __init__(self, name, world_state, personality="a typical person"):
        self.name = name
        self.world = world_state # Reference to the single world state object
        self.personality = personality
        self.memory = "" # Simple short-term memory buffer
        self.last_utterance = "None"
        self.llm = model

    def perceive_and_think(self):
        """Get context, format prompt, call LLM for natural language action/thought."""
        current_context = self.world.get_context_for_agent(self.name)

        # Update memory (very basic)
        self.memory = f"Last thought/action: {self.last_utterance}\nCurrent situation: {current_context}"
        if len(self.memory) > 600: # Limit memory length
            self.memory = self.memory[-600:]

        prompt = f"""You are {self.name}, a character in a simulated world.
Your personality: {self.personality}.

Your current situation:
{current_context}

Brief memory of your last action and situation:
{self.memory}

Based *only* on the above, what do you think, say, or do next?
Describe your action, thought, or utterance in a single, short, natural sentence.
Examples:
- I walk towards the Forest Edge.
- I say to Bob, "What was that noise?"
- I look around the park nervously.
- I think about finding shelter.
- I wait and observe.

Your response (one sentence):"""

        print(f"\n[{self.name} is thinking...]")
        # print(f"--- DEBUG PROMPT for {self.name} ---\n{prompt}\n--------------------")

        try:
            response = self.llm.generate_content(prompt)
            utterance = response.text.strip().split('\n')[0] # Take first line if multiple
            # Basic check for empty/invalid response
            if not utterance or len(utterance) < 5:
                 print(f"[{self.name} Warning]: LLM gave short/empty response: '{utterance}'. Will wait.")
                 utterance = f"{self.name} waits silently." # Default to waiting description
            else:
                 print(f"[{self.name} decides]: {utterance}")
            self.last_utterance = utterance # Store the exact LLM output
            return utterance

        except Exception as e:
            print(f"[{self.name} Error]: LLM generation failed: {e}")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                 print(f"[{self.name} Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            self.last_utterance = f"{self.name} pauses due to an error."
            return self.last_utterance # Return error description

# --- Simulation Loop (Interpreter Focus) ---
def interpret_and_update(agent_name, utterance, world_state):
    """Very basic interpretation of the LLM's natural language utterance."""

    # 1. Log the raw utterance as an event visible to others
    # Prepend agent name for clarity in logs, unless already stated
    log_msg = utterance
    if not utterance.lower().startswith(f"{agent_name.lower()} "):
         log_msg = f"{agent_name}: \"{utterance}\""
    # Avoid logging simple waiting statements unless necessary
    if "wait" not in utterance.lower() and "observe" not in utterance.lower() and "think" not in utterance.lower():
       world_state.log_event(log_msg) # Log speech/actions, but maybe not pure thoughts/waiting

    # 2. Check for movement intent (very basic keywords)
    # Regex to find patterns like "go to X", "move to Y", "walk towards Z" etc.
    # It captures the destination name.
    move_match = re.search(r'\b(go|move|walk|head)\s+(to|towards)\s+the\s+([A-Za-z\s]+)\b', utterance, re.IGNORECASE)
    if move_match:
        destination = move_match.group(3).strip().title() # Get the captured group, trim spaces, title case
        # Check if destination is a known location
        known_locations = world_state.location_descriptions.keys()
        # Basic fuzzy matching (e.g., handle "Forest Edge" vs "Forest") - optional enhancement
        matched_location = None
        for loc in known_locations:
            if destination in loc or loc in destination: # Simple substring check
                matched_location = loc
                break

        if matched_location:
            print(f"[Interpreter]: Detected move intent from '{agent_name}' to '{matched_location}' (from '{destination}')")
            world_state.move_agent(agent_name, matched_location)
        else:
            print(f"[Interpreter]: Move intent detected for '{destination}', but it's not a known location.")
        # Even if move fails, the utterance was logged, so we don't need further action here.
        return # Don't process other actions if move was detected

    # 3. Check for speech intent (basic: "say to X", "tell Y")
    # Regex captures the target agent name and the message content
    speak_match = re.search(r'\b(say|tell)\s+(to\s+)?([A-Za-z]+)\s*[:,]?\s*["\']?(.*?)["\']?$', utterance, re.IGNORECASE)
    # Simpler regex might just log anything that doesn't look like a move:
    # if not move_match and ("say" in utterance.lower() or "ask" in utterance.lower() or "tell" in utterance.lower()):
    #    world_state.log_event(f"{agent_name} says: \"{utterance}\"") # Log speech more explicitly

    if speak_match:
         target_agent = speak_match.group(3).strip().title()
         message = speak_match.group(4).strip()
         print(f"[Interpreter]: Detected speech from '{agent_name}' to '{target_agent}': '{message}'")
         # In this simple model, speech is already logged by log_event.
         # A more complex model could queue messages specifically.
         return

    # 4. Other actions (look, think, wait) are implicitly handled by logging the utterance.
    # The effect is that others might perceive "{Agent} looks around" or "{Agent} waits".

def run_simulation():
    print("--- Starting Simplified Free Agent Simulation ---")

    # 1. Initialize World State
    world = WorldState()
    world.global_context['weather'] = "Misty" # Start with something atmospheric

    # 2. Initialize Agents
    agents = [
        FreeAgent("Alice", world, personality="curious, slightly anxious, observant"),
        FreeAgent("Bob", world, personality="calm, pragmatic, speaks plainly")
    ]
    world.add_agent("Alice", "Park")
    world.add_agent("Bob", "Park")

    # --- Simulation Steps ---
    step = 0
    max_steps = 30

    while step < max_steps:
        step += 1
        print(f"\n{'='*10} Simulation Step {step} {'='*10}")
        print(world.get_full_state_string()) # Show world state at start

        # --- Agent Phase ---
        agent_utterances = {} # Store what each agent decided in this step
        for agent in agents:
            utterance = agent.perceive_and_think()
            agent_utterances[agent.name] = utterance
            time.sleep(1.5) # Pause for readability

        # --- Interpretation and Update Phase ---
        print("\n--- Interpreting Actions & Updating World ---")
        for agent_name, utterance in agent_utterances.items():
             interpret_and_update(agent_name, utterance, world)
             time.sleep(0.5) # Small delay between interpretations

        # --- Manual Control / End Step ---
        print("\n--- End of Step ---")
        print(world.get_full_state_string()) # Show world state after updates

        user_input = input("Enter for next step, 'w <condition>' (e.g. w Sunny) to change weather, 'q' to quit: ").lower()

        if user_input == 'q':
            print("Quitting simulation.")
            break
        elif user_input.startswith('w '):
            new_weather = user_input[2:].strip().title()
            if new_weather:
                old_weather = world.global_context['weather']
                world.global_context['weather'] = new_weather
                world.log_event(f"The weather suddenly changes from {old_weather} to {new_weather}.")
            else:
                print("Please specify weather condition after 'w '.")
        # Any other key (or just Enter) continues

    print("\n--- Simulation Ended ---")

# --- Run ---
if __name__ == "__main__":
    run_simulation()