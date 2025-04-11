import google.generativeai as genai
import os
import time
import random
from dotenv import load_dotenv
from collections import defaultdict # For storing messages

# --- Configuration (Same as V1) ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found. Make sure it's set in the .env file.")
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
  "temperature": 0.85, # Slightly higher for more creativity
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 120, # Allow slightly longer responses if needed
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
model = genai.GenerativeModel(model_name="gemini-1.5-flash", # Or gemini-1.5-pro
                              generation_config=generation_config,
                              safety_settings=safety_settings)

# --- Environment Class (Enhanced) ---
class Environment:
    def __init__(self, initial_weather="Sunny"):
        self.weather = initial_weather
        # Locations now include objects
        self.locations = {
            "Park": {
                "description": "A pleasant park with benches, some trees, and a small shelter nearby.",
                "occupants": [],
                "objects": {"Bench": {"description": "A simple wooden park bench.", "state": "empty"},
                            "Strange_Flower": {"description": "An unusually bright, pulsing flower.", "state": "glowing"} }
            },
            "Shelter": {
                "description": "A simple wooden shelter inside the park.",
                "occupants": [],
                "objects": {} # No objects here initially
            }
        }
        # Message queue for agents
        self.message_queue = defaultdict(list) # agent_name -> [messages]
        self.last_random_event = "None"
        print(f"Environment initialized. Weather: {self.weather}")
        print(self.get_object_state_string()) # Show initial objects

    def get_object_state_string(self):
        obj_str = "Objects in world:\n"
        for loc_name, loc_data in self.locations.items():
             obj_str += f"  In {loc_name}:\n"
             if loc_data["objects"]:
                 for obj_name, obj_data in loc_data["objects"].items():
                     obj_str += f"    - {obj_name} ({obj_data['state']})\n"
             else:
                 obj_str += "    - None\n"
        return obj_str

    def set_weather(self, new_weather):
        if new_weather != self.weather:
            change_msg = f"Weather changing from {self.weather} to {new_weather}"
            print(f"\n*** ENVIRONMENT EVENT: {change_msg} ***\n")
            self.weather = new_weather
            # Notify agents in all locations about the weather change
            for loc_data in self.locations.values():
                for agent_name in loc_data["occupants"]:
                    self.add_message(agent_name, f"System: {change_msg}")
        else:
             print(f"\n(Environment: Weather is already {self.weather})")

    def add_agent(self, agent_name, location_name):
         if location_name in self.locations:
             self.locations[location_name]["occupants"].append(agent_name)
             print(f"Environment: Added {agent_name} to {location_name}")
         else:
             print(f"Warning: Location '{location_name}' not found.")

    def move_agent(self, agent_name, old_location, new_location):
        # --- (Same logic as V1, but with better debug prints) ---
        current_loc_name = None
        # Find agent first
        for loc_name, loc_data in self.locations.items():
            if agent_name in loc_data["occupants"]:
                current_loc_name = loc_name
                break

        if current_loc_name is None:
             print(f"Warning: Agent {agent_name} not found in any location to move from.")
             # Option: Try adding agent to new location if they don't exist? Risky.
             return False # Fail if agent isn't located

        # Check if target location exists
        if new_location not in self.locations:
            print(f"Warning: Target location '{new_location}' not found for {agent_name}.")
            return False

        # Perform the move
        self.locations[current_loc_name]["occupants"].remove(agent_name)
        self.locations[new_location]["occupants"].append(agent_name)
        print(f"Environment: Moved {agent_name} from {current_loc_name} to {new_location}")
        return True


    def add_message(self, recipient_agent, message):
        """Adds a message for a specific agent to perceive later."""
        self.message_queue[recipient_agent].append(message)
        # print(f"DEBUG: Added message for {recipient_agent}: '{message}'")

    def get_and_clear_messages(self, agent_name):
        """Retrieves messages for an agent and clears them."""
        messages = self.message_queue[agent_name]
        self.message_queue[agent_name] = [] # Clear the queue
        return messages

    def handle_interaction(self, agent_name, object_name, location_name):
        """Basic logic for interacting with objects."""
        if location_name in self.locations and object_name in self.locations[location_name]["objects"]:
            obj_data = self.locations[location_name]["objects"][object_name]
            # Example interaction logic (can be expanded greatly)
            if object_name == "Strange_Flower":
                print(f"Environment: {agent_name} touches the Strange_Flower. It pulses brightly!")
                obj_data["state"] = random.choice(["glowing intensely", "dimmed slightly", "emitting soft hum"])
                # Maybe notify others?
                for occupant in self.locations[location_name]["occupants"]:
                     if occupant != agent_name:
                         self.add_message(occupant, f"System: You see {agent_name} interact with the {object_name}. It is now {obj_data['state']}.")
                return f"You touch the {object_name}. It pulses brightly and is now {obj_data['state']}."
            elif object_name == "Bench":
                 print(f"Environment: {agent_name} examines the Bench.")
                 return f"You examine the {object_name}. It's a sturdy wooden bench."
            else:
                return f"You interact with the {object_name}. Nothing much happens."
        else:
            return f"You try to interact with {object_name}, but it's not here."

    def trigger_random_event(self):
        """Small chance of a random event occurring."""
        if random.random() < 0.15: # 15% chance per step
            event_type = random.choice(["sound", "object_change"])
            if event_type == "sound":
                sound = random.choice(["a distant bird call", "a sudden rustling in the leaves", "a faint humming noise"])
                self.last_random_event = f"A random sound was heard: {sound}"
                print(f"\n*** ENVIRONMENT EVENT: {self.last_random_event} ***\n")
                # Notify all agents currently somewhere
                for loc_data in self.locations.values():
                    for agent_name in loc_data["occupants"]:
                         self.add_message(agent_name, f"System: You hear {sound}.")
            elif event_type == "object_change" and "Park" in self.locations: # Example: change object in Park
                if self.locations["Park"]["objects"]:
                     obj_to_change = random.choice(list(self.locations["Park"]["objects"].keys()))
                     old_state = self.locations["Park"]["objects"][obj_to_change]['state']
                     new_state = random.choice(["slightly damaged", "covered in dew", "strangely warm"])
                     if old_state != new_state:
                         self.locations["Park"]["objects"][obj_to_change]['state'] = new_state
                         self.last_random_event = f"The {obj_to_change} in the Park suddenly looks {new_state}"
                         print(f"\n*** ENVIRONMENT EVENT: {self.last_random_event} ***\n")
                         # Notify agents in that location
                         for agent_name in self.locations["Park"]["occupants"]:
                             self.add_message(agent_name, f"System: You notice the {obj_to_change} now looks {new_state}.")
        else:
             self.last_random_event = "None"


    def get_state_description_for_agent(self, agent_name, agent_location):
        """Generates a description including location, weather, occupants, objects, and messages."""
        if agent_location not in self.locations:
             # Handle case where agent location is somehow invalid
             base_desc = f"You seem to be lost or in an unknown place. The weather is {self.weather}."
             messages = self.get_and_clear_messages(agent_name)
             if messages:
                 base_desc += " You recall hearing/seeing recently: " + "; ".join(messages)
             return base_desc

        location_data = self.locations[agent_location]
        description = f"You are in the {agent_location}. {location_data['description']} "
        description += f"The current weather is: {self.weather}. "

        # Occupants
        occupants = location_data["occupants"]
        other_occupants = [name for name in occupants if name != agent_name]
        if other_occupants:
            description += f"You see {', '.join(other_occupants)} here. "
        else:
            description += "You are alone here. "

        # Objects
        objects = location_data["objects"]
        if objects:
            description += "Nearby objects: "
            object_descs = [f"{name} ({data['state']})" for name, data in objects.items()]
            description += ", ".join(object_descs) + ". "
        else:
            description += "There are no notable objects here. "

        # Incoming Messages (Speech, System Events)
        messages = self.get_and_clear_messages(agent_name)
        if messages:
            description += "You recall hearing/seeing recently: " + "; ".join(messages) + ". "

        return description.strip()

    def get_full_state(self):
        """Returns a snapshot of the entire environment state."""
        state = f"--- Environment State ---\nWeather: {self.weather}\n"
        state += self.get_object_state_string() # Use helper for objects
        state += "Agent Locations:\n"
        for name, data in self.locations.items():
            state += f"  - {name}: Occupants: {', '.join(data['occupants']) if data['occupants'] else 'None'}\n"
        state += f"Last Random Event: {self.last_random_event}\n"
        # You could optionally show the message queue here for debugging
        # state += f"Message Queue: {dict(self.message_queue)}\n"
        return state + "-------------------------"

# --- Agent Class (Enhanced) ---
class Agent:
    def __init__(self, name, initial_location, environment, personality="neutral"):
        self.name = name
        self.location = initial_location
        self.environment = environment
        self.personality = personality
        self.memory = "" # Simple rolling memory (could be improved)
        self.last_action_description = "None" # More descriptive than just the command
        self.llm = model

        self.environment.add_agent(self.name, self.location)
        print(f"Agent {self.name} initialized at {self.location} with personality: {self.personality}")

    def perceive(self):
        """Gets the richer environment state."""
        perception_text = self.environment.get_state_description_for_agent(self.name, self.location)
        self.memory = f"Recent memory: {self.memory[-300:]}\nLatest perception: {perception_text}" # Rolling + tagged memory
        # Keep memory from getting excessively long
        if len(self.memory) > 700:
             self.memory = self.memory[-700:]
        print(f"[{self.name} Perception]: {perception_text}")
        return perception_text

    def think(self, perception):
        """Uses LLM with richer context and slightly more flexible action prompting."""
        prompt = f"""You are {self.name}, a character in a simulation.
Personality: {self.personality}
Your current location: {self.location}

Your situation and recent perceptions:
{perception}

Your relevant memories (most recent first):
{self.memory}

Your last action was: {self.last_action_description}

Based ONLY on the information above, what is your next single, simple action? Choose ONE:
- MoveTo(Location) (Valid locations: {', '.join(self.environment.locations.keys())})
- Speak(TargetAgent, Message) (Speak to someone present)
- InteractWith(Object) (Interact with an object present in your location)
- Wait() (If nothing else seems appropriate)

Your decision (just the single action line):"""

        print(f"[{self.name} Thinking]: Sending prompt to LLM...")
        # print(f"--- DEBUG PROMPT for {self.name} ---\n{prompt}\n--------------------") # Uncomment for serious debugging

        try:
            # Make the API call
            response = self.llm.generate_content(prompt)
            action_text = response.text.strip()

            # Pre-process response: Sometimes LLMs add justifications. Try to find the action line.
            action_line = ""
            lines = action_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("MoveTo(") or line.startswith("Speak(") or \
                   line.startswith("InteractWith(") or line.startswith("Wait"):
                    action_line = line
                    break # Take the first valid action line found
            if not action_line: # If no specific line found, use the whole response (might fail parsing)
                 action_line = action_text

            print(f"[{self.name} Thinking]: LLM raw response: '{action_text}' -> Parsed action line: '{action_line}'")

            # --- Action Parsing (Improved Robustness) ---
            action_line = action_line.strip() # Ensure no leading/trailing spaces

            if action_line.startswith("MoveTo(") and action_line.endswith(")"):
                target = action_line[len("MoveTo("):-1].strip()
                # Basic validation: is the target a known location?
                if target in self.environment.locations:
                    return ("MoveTo", target)
                else:
                    print(f"[{self.name} Warning]: LLM tried to MoveTo unknown location '{target}'. Waiting instead.")
                    return ("Wait", None)

            elif action_line.startswith("Speak(") and action_line.endswith(")"):
                 content = action_line[len("Speak("):-1].strip()
                 # Find the last comma that separates agent from message
                 split_index = content.rfind(',')
                 if split_index != -1:
                     target_agent = content[:split_index].strip()
                     message = content[split_index+1:].strip().strip('"') # Remove potential quotes
                     # Basic validation: is the target agent actually here?
                     if target_agent in self.environment.locations[self.location]["occupants"]:
                         return ("Speak", target_agent, message)
                     else:
                         print(f"[{self.name} Warning]: LLM tried to Speak to {target_agent} who is not here. Waiting instead.")
                         return ("Wait", None)
                 else:
                     print(f"[{self.name} Warning]: Could not parse Speak action arguments: '{content}'. Waiting instead.")
                     return ("Wait", None)

            elif action_line.startswith("InteractWith(") and action_line.endswith(")"):
                target_object = action_line[len("InteractWith("):-1].strip()
                 # Basic validation: is the object actually here?
                if target_object in self.environment.locations[self.location]["objects"]:
                    return ("InteractWith", target_object)
                else:
                    print(f"[{self.name} Warning]: LLM tried to InteractWith {target_object} which is not here. Waiting instead.")
                    return ("Wait", None)

            elif action_line.startswith("Wait"): # Allow Wait() or just Wait
                return ("Wait", None)

            else:
                print(f"[{self.name} Warning]: LLM returned unparseable/invalid action: '{action_line}'. Defaulting to Wait.")
                return ("Wait", None) # Default action

        except Exception as e:
            print(f"[{self.name} Error]: LLM generation failed: {e}")
            # Handle potential API errors (e.g., rate limits, content safety blocks)
            if "response.prompt_feedback" in locals() and response.prompt_feedback.block_reason:
                 print(f"[{self.name} Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            return ("Wait", None) # Default action on API error


    def act(self, action_tuple):
        """Executes actions, including interaction and sending messages."""
        action_type = action_tuple[0]
        action_result_desc = "" # To store outcome for memory

        if action_type == "MoveTo":
            target_location = action_tuple[1]
            print(f"[{self.name} Action]: Attempting to move to {target_location}...")
            moved = self.environment.move_agent(self.name, self.location, target_location)
            if moved:
                 self.location = target_location
                 action_result_desc = f"Moved to {target_location}."
                 print(f"[{self.name} Action]: Successfully moved.")
            else:
                 action_result_desc = f"Tried to move to {target_location} but failed (perhaps invalid location)."
                 print(f"[{self.name} Action]: Failed to move.")

        elif action_type == "Speak":
            target_agent = action_tuple[1]
            message = action_tuple[2]
            print(f"[{self.name} Action]: Says to {target_agent}: '{message}'")
            # Send the message via the environment for the target to perceive next step
            full_message = f"{self.name} said to you: '{message}'"
            self.environment.add_message(target_agent, full_message)
            action_result_desc = f"Said '{message}' to {target_agent}."

        elif action_type == "InteractWith":
            target_object = action_tuple[1]
            print(f"[{self.name} Action]: Attempting to interact with {target_object}...")
            interaction_result = self.environment.handle_interaction(self.name, target_object, self.location)
            print(f"[{self.name} Action Result]: {interaction_result}")
            action_result_desc = f"Interacted with {target_object}. Result: {interaction_result}"

        elif action_type == "Wait":
            print(f"[{self.name} Action]: Waits.")
            action_result_desc = "Waited."

        else:
            print(f"[{self.name} Warning]: Unknown action type execution: {action_type}")
            action_result_desc = "Attempted an unknown action."

        # Update memory with a description of the action taken and its basic result
        self.last_action_description = action_result_desc
        # Add a small delay
        time.sleep(0.5)


# --- Simulation Loop (Enhanced with Random Events) ---
def run_simulation():
    print("--- Starting Simulation V2 ---")

    # 1. Initialize Environment
    environment = Environment(initial_weather="Sunny")

    # 2. Initialize Agents
    alice = Agent(name="Alice", initial_location="Park", environment=environment, personality="optimistic, easily distracted by shiny things, dislikes rain")
    bob = Agent(name="Bob", initial_location="Park", environment=environment, personality="cautious, pragmatic, notices details, prefers calm")
    agents = [alice, bob]

    # --- Simulation Steps ---
    step = 0
    max_steps = 30 # Slightly longer simulation

    while step < max_steps:
        step += 1
        print(f"\n{'='*10} Simulation Step {step} {'='*10}")

        # --- Environment Phase ---
        # Trigger potential random events *before* agents perceive
        environment.trigger_random_event()
        # Display environment state *after* potential random events but *before* agent actions
        print(environment.get_full_state())

        # --- Agent Phase ---
        # Process each agent's turn
        for agent in agents:
            if agent.location is None: # Skip agent if they are somehow lost/invalid
                print(f"Skipping {agent.name} as their location is None.")
                continue

            print(f"\n-- Processing {agent.name} (in {agent.location}) --")
            # a. Perceive (gets location description + any queued messages)
            perception = agent.perceive()
            # b. Think (LLM decides action based on perception, memory, personality)
            action_tuple = agent.think(perception)
            # c. Act (Execute action, potentially changing environment or queuing messages)
            agent.act(action_tuple)
            time.sleep(1.5) # Slightly longer pause to allow reading LLM interactions

        # --- Manual Control / End Step ---
        print("\n--- End of Step ---")
        # Display state again after all agents have acted
        print(environment.get_full_state())

        user_input = input("Press Enter for next step, 'r'/'s' for rain/sunny, 'q' to quit: ").lower()

        if user_input == 'q':
            print("Quitting simulation.")
            break
        elif user_input == 'r':
            environment.set_weather("Rainy") # Manual override / director action
        elif user_input == 's':
            environment.set_weather("Sunny") # Manual override / director action
        # Any other key (or just Enter) continues

    print("\n--- Simulation Ended ---")

# --- Run ---
if __name__ == "__main__":
    run_simulation()