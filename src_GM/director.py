# src/director.py
import google.generativeai as genai
import config
import random # For potential randomness or choosing not to act

class Director:
    """
    Observes the world state, considers a narrative goal, and uses an LLM
    to suggest and enact *indirect* environmental interventions.
    Inspired by the Game Master concept.
    """
    def __init__(self, world_state, model, narrative_goal):
        self.world = world_state # Reference to the world state
        self.llm = model         # The LLM instance for decision making
        self.narrative_goal = narrative_goal
        self.intervention_cooldown = 0 # Steps until next potential intervention
        self.steps_since_last_intervention = 0
        print(f"Director initialized with goal: '{self.narrative_goal}'")

    def observe(self):
        """Gathers the necessary information from the world state for the LLM."""
        # Get a concise summary of the current state
        agent_locations = self.world.agent_locations
        recent_events = self.world.recent_events[-5:] # Last 5 events
        weather = self.world.global_context.get('weather', 'unknown')

        observation = f"Current State Summary:\n"
        observation += f"- Weather: {weather}\n"
        observation += f"- Agent Locations: {agent_locations}\n"
        observation += f"- Recent Events:\n"
        if recent_events:
            for event in recent_events:
                 prefix = f"[{event.scope} @ {event.location or 'Global'}]"
                 observation += f"    - {prefix} {event.description}\n"
        else:
            observation += "    - Nothing noteworthy recently.\n"

        # Add goal progress check (simple example: are agents together?)
        agents_in_same_location = False
        if len(agent_locations) > 1:
            first_loc = next(iter(agent_locations.values()))
            if all(loc == first_loc for loc in agent_locations.values()):
                agents_in_same_location = True
        observation += f"- Goal Status ({self.narrative_goal}): Agents currently {'together' if agents_in_same_location else 'apart'}.\n"

        return observation.strip()

    def think(self, observation):
        """Uses the LLM to decide on an environmental intervention."""

        # Simple cooldown mechanism
        if self.steps_since_last_intervention < self.intervention_cooldown:
             self.steps_since_last_intervention += 1
             print("[Director Thinking]: Cooldown active.")
             return "ACTION: Do nothing" # Skip thinking

        prompt = f"""You are the Director/Game Master of a simulation.
Your objective is to subtly guide the narrative towards: '{self.narrative_goal}'.
You do this *only* by manipulating the environment or introducing external events.
You CANNOT directly control agents, read their minds, or change their internal states.

Current Simulation State:
{observation}

Allowed Actions:
1. Change weather: Specify the new weather condition (e.g., Sunny, Rainy, Windy, Foggy, Stormy).
2. Create ambient event: Describe a sensory event (e.g., a distant sound, a strange smell, a sudden chill).
3. Do nothing: If the situation doesn't require intervention or is progressing well.

Based on the current state and your objective, suggest ONE action from the allowed list to subtly nudge things towards the goal. Be concise and use the format 'ACTION: [Your chosen action description]'. If doing nothing, use 'ACTION: Do nothing'.

Example suggestions:
ACTION: Change weather to Rainy
ACTION: Create ambient event 'A faint birdsong is heard from the Forest Edge.'
ACTION: Do nothing

Your suggestion:"""

        print("[Director Thinking...]")
        # print(f"--- DEBUG PROMPT for Director ---\n{prompt}\n--------------------") # Optional

        try:
            response = self.llm.generate_content(prompt)
            suggestion = response.text.strip()

            if not suggestion.startswith("ACTION:"):
                print("[Director Warning]: LLM response malformed. Defaulting to 'Do nothing'. Response:", suggestion)
                return "ACTION: Do nothing"

            print(f"[Director Suggests]: {suggestion}")
            # Reset cooldown if an action is suggested (or consider resetting only on non-'Do nothing' actions)
            if "Do nothing" not in suggestion:
                 self.steps_since_last_intervention = 0
                 self.intervention_cooldown = random.randint(2, 4) # Wait a few steps after acting
                 print(f"[Director Info]: Intervention suggested. Setting cooldown to {self.intervention_cooldown} steps.")
            else:
                 self.steps_since_last_intervention += 1 # Increment even if thinking 'do nothing' this time
            return suggestion

        except Exception as e:
            print(f"[Director Error]: LLM generation failed: {e}")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                 print(f"[Director Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            return "ACTION: Do nothing" # Fail safe

    def act(self, suggestion):
        """Parses the LLM's suggestion and applies it to the world state."""
        action_part = suggestion.replace("ACTION:", "").strip()

        if action_part.lower() == "do nothing":
            print("[Director Action]: No intervention taken.")
            return

        # Parse specific actions
        if action_part.lower().startswith("change weather to "):
            new_weather = action_part[len("change weather to "):].strip().title()
            if new_weather:
                print(f"[Director Action]: Attempting to change weather to {new_weather}")
                self.world.set_weather(new_weather, triggered_by="Director")
            else:
                print("[Director Action Error]: Invalid weather condition specified.")

        elif action_part.lower().startswith("create ambient event "):
            event_description = action_part[len("create ambient event "):].strip()
            # Add quotes or formatting for clarity if needed
            if not event_description.startswith("'"): event_description = f"'{event_description}'"

            if event_description:
                scope = 'global'
                print(f"[Director Action]: Creating {scope} ambient event at '{'Global'}': {event_description}")
                self.world.log_event(f"[Ambient]: {event_description}",
                                       scope=scope,
                                       location='Global',
                                       triggered_by="Director")
            else:
                print("[Director Action Error]: Invalid ambient event description.")
        else:
            print(f"[Director Action Warning]: Could not parse suggested action: '{action_part}'")

    def step(self):
        """Perform one cycle of the Director's operation."""
        print("\n--- Director Phase ---")
        observation = self.observe()
        suggestion = self.think(observation)
        self.act(suggestion)
        print("--- End Director Phase ---")