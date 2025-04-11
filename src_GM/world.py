# src/world.py
import config
from collections import namedtuple

# Define a structure for events for clarity
Event = namedtuple("Event", ["description", "location", "scope", "step"]) # Add step number

class WorldState:
    def __init__(self, locations):
        self.agent_locations = {} # agent_name -> location_name
        self.location_descriptions = locations
        self.global_context = {"weather": "Clear"}
        self.recent_events = [] # Now stores Event tuples
        self.current_step = 0 # Track simulation step
        print("WorldState initialized.")

    def advance_step(self):
        self.current_step += 1

    def add_agent(self, agent_name, location_name):
        if location_name in self.location_descriptions:
            self.agent_locations[agent_name] = location_name
            print(f"World: Registered {agent_name} at {location_name}")
            # Log appearance locally
            self.log_event(f"{agent_name} appears.",
                           scope='local',
                           location=location_name,
                           triggered_by="Setup")
        else:
            print(f"Warning: Cannot add {agent_name} to unknown location '{location_name}'")
    
    def move_agent(self, agent_name, new_location):
        if agent_name not in self.agent_locations:
            print(f"Warning: Cannot move unknown agent '{agent_name}'")
            return False, "Agent not found"
        if new_location not in self.location_descriptions:
            print(f"Warning: Cannot move {agent_name} to unknown location '{new_location}'")
            return False, "Destination not found"

        old_location = self.agent_locations[agent_name]
        if old_location != new_location:
            self.agent_locations[agent_name] = new_location
            # Log departure from old location and arrival at new location
            # Departure event
            self.log_event(f"{agent_name} departs towards {new_location}.",
                           scope='local', # Or 'action'? Let's use 'local' for observation focus
                           location=old_location,
                           triggered_by=agent_name)
            # Arrival event
            self.log_event(f"{agent_name} arrives from {old_location}.",
                           scope='local',
                           location=new_location,
                           triggered_by=agent_name)
            return True, f"Moved from {old_location} to {new_location}"
        return False, "Agent already at destination"

    def get_agents_at(self, location_name):
        return [name for name, loc in self.agent_locations.items() if loc == location_name]

    def log_event(self, event_description, scope='local', location=None, triggered_by="Simulation"):
        """Logs a structured event with scope and location."""
        log_prefix = f"[{triggered_by} @ {location or 'Global'}/{scope}]"

        new_event = Event(description=event_description, location=location, scope=scope, step=self.current_step)

        # Avoid exact duplicate events in the same step if needed (optional)
        # if self.recent_events and self.recent_events[-1] == new_event: return

        print(f"{log_prefix}: {event_description}")
        self.recent_events.append(new_event)

        # Keep event log from growing infinitely
        if len(self.recent_events) > config.MAX_RECENT_EVENTS * 2: # Store a bit more history internally
            self.recent_events.pop(0)

    def set_weather(self, new_weather, triggered_by="Simulation"):
        """Changes the weather and logs the event."""
        old_weather = self.global_context.get('weather', 'unknown')
        if old_weather != new_weather:
            self.global_context['weather'] = new_weather
            # Log weather change as a GLOBAL event
            self.log_event(f"The weather changes from {old_weather} to {new_weather}.",
                           scope='global',
                           location=None, # Global event has no specific location
                           triggered_by=triggered_by)
            return True
        return False

    def get_context_for_agent(self, agent_name):
        """Provides filtered contextual information based on agent's location."""
        if agent_name not in self.agent_locations:
            return "You are currently disconnected from the world."

        agent_location = self.agent_locations[agent_name]
        description = f"You ({agent_name}) are in the {agent_location}. Description: {self.location_descriptions.get(agent_location, 'An unknown area.')}\n"
        description += f"Current conditions: Weather is {self.global_context.get('weather', 'unknown')}.\n"

        other_agents = [name for name in self.get_agents_at(agent_location) if name != agent_name]
        if other_agents:
            description += f"Others present: {', '.join(other_agents)}.\n"
        else:
            description += "You are alone here.\n"

        # Filter recent events based on scope and location
        visible_events_descriptions = []
        # Look back through recent events relevant to perception (e.g., last N steps or total events)
        relevant_event_history = self.recent_events[-(config.MAX_RECENT_EVENTS):] # Look at last ~15 events total

        for event in relevant_event_history:
            # Always perceive global events
            if event.scope == 'global':
                visible_events_descriptions.append(event.description)
            # Perceive local/action events happening at the agent's current location
            elif event.location == agent_location and event.scope in ['local', 'action']:
                 # Avoid showing agent its own action description if memory already handles it?
                 # Let's include it for now, signifies observability by others.
                 # Prefix might be useful: e.g., "Here: Someone arrives from Park."
                 visible_events_descriptions.append(f"(Here) {event.description}") # Add context marker

        if visible_events_descriptions:
             description += "Recent happenings you observed or might know about:\n - " + "\n - ".join(visible_events_descriptions)
        else:
             description += "Nothing noteworthy seems to have happened recently."


        return description.strip()


    def get_full_state_string(self):
        """For debugging/observer view. Shows structured events."""
        state = f"--- World State (Step: {self.current_step}) ---\n"
        state += f"Global Context: {self.global_context}\n"
        state += f"Agent Locations: {self.agent_locations}\n"
        state += f"Recent Events Log ({len(self.recent_events)} total, showing last {config.MAX_RECENT_EVENTS}):\n"
        display_events = self.recent_events[-config.MAX_RECENT_EVENTS:]
        for event in display_events:
            state += f"  - Step {event.step}: [{event.scope} @ {event.location or 'Global'}] {event.description}\n"
        return state + "-------------------"