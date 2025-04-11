# world.py
import config # Import settings from config.py

class WorldState:
    def __init__(self, locations):
        self.agent_locations = {} # agent_name -> location_name
        self.location_descriptions = locations
        self.global_context = {"weather": "Clear"}
        self.recent_events = [] # List of strings describing what happened
        print("WorldState initialized.")

    def add_agent(self, agent_name, location_name):
        if location_name in self.location_descriptions:
            self.agent_locations[agent_name] = location_name
            # Don't log event here, let the simulation loop decide when to log appearance
            # self.log_event(f"{agent_name} appears in the {location_name}.")
            print(f"World: Registered {agent_name} at {location_name}")
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
            event_desc = f"{agent_name} moved from {old_location} to {new_location}."
            self.log_event(event_desc) # Log move after it happens
            return True, event_desc
        return False, "Agent already at destination" # Didn't actually move

    def get_agents_at(self, location_name):
        return [name for name, loc in self.agent_locations.items() if loc == location_name]

    def log_event(self, event_description):
        """Logs an event and makes it visible in the world context."""
        # Avoid duplicate consecutive logs if possible (simple check)
        if not self.recent_events or self.recent_events[-1] != event_description:
             print(f"[World Event]: {event_description}")
             self.recent_events.append(event_description)
             # Keep event log from growing infinitely
             if len(self.recent_events) > config.MAX_RECENT_EVENTS:
                 self.recent_events.pop(0)

    def get_context_for_agent(self, agent_name):
        """Provides the contextual information an agent perceives."""
        if agent_name not in self.agent_locations:
            # This case should ideally be prevented by the simulation loop
            return "You are currently disconnected from the world."

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
             # Show last N events relevant to the agent's perception
             visible_events = self.recent_events[-(config.MAX_RECENT_EVENTS // 2):] # Show recent half
             if visible_events:
                description += "Recent happenings you observed or might know about:\n - " + "\n - ".join(visible_events)

        return description.strip()

    def get_full_state_string(self):
        """For debugging/observer view."""
        state = f"--- World State ---\n"
        state += f"Global Context: {self.global_context}\n"
        state += f"Agent Locations: {self.agent_locations}\n"
        state += f"Recent Events Log ({len(self.recent_events)} total):\n"
        # Display the most recent events clearly
        display_events = self.recent_events[-config.MAX_RECENT_EVENTS:] # Show up to max
        for event in display_events:
            state += f"  - {event}\n"
        return state + "-------------------"