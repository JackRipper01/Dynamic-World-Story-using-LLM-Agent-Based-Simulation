# src/world.py
import config
from collections import namedtuple

# Define a structure for events for clarity
Event = namedtuple(
    "Event", ["description", "location", "scope", "step", "triggered_by"])


class WorldState:
    def __init__(self, locations):
        self.agent_locations = {}  # agent_name -> location_name
        self.location_descriptions = locations
        self.location_connectivity = {  # Defines possible direct movements
            "Park": ["Shelter", "Forest Edge"],
            "Shelter": ["Park"],
            "Forest Edge": ["Park"]
            # Add more connections as locations are added
        }
        self.location_properties = {  # Defines states/features of locations
            "Park": {"ground": "grassy"},
            # Example: Shelter door starts unlocked
            "Shelter": {"door_locked": False, "contains": []},
            "Forest Edge": {"terrain": "uneven"}
        }
        self.global_context = {"weather": "Clear"}
        self.event_log = []  # Now stores Event tuples
        self.current_step = 0  # Track simulation step

        # agent_name -> agent_object (for dispatch)
        self.registered_agents = {}
        
        print("WorldState initialized.")

    def register_agent(self, agent):
        """Registers an agent to receive events."""
        if agent.name not in self.registered_agents:
            self.registered_agents[agent.name] = agent
            print(
                f"[World Event Dispatch]: Registered {agent.name} for events.")
    
    def unregister_agent(self, agent_name):
        """Unregisters an agent."""
        if agent_name in self.registered_agents:
            del self.registered_agents[agent_name]
            print(f"[World Event Dispatch]: Unregistered {agent_name}.")

    def advance_step(self):
        self.current_step += 1

    # --- NEW: Helper methods to access rules ---
    def get_reachable_locations(self, from_location):
        """Returns list of locations directly reachable from the given one."""
        return self.location_connectivity.get(from_location, [])

    def get_location_property(self, location, prop_name):
        """Safely gets a property of a location."""
        return self.location_properties.get(location, {}).get(prop_name, None)

    def set_location_property(self, location, prop_name, value, triggered_by="System"):
        """Sets a property, potentially logging an event via log_event."""
        if location not in self.location_properties:
            print(
                f"[World State Warning]: Location '{location}' not found for setting property.")
            return False
        if prop_name not in self.location_properties[location]:
            print(
                f"[World State Warning]: Property '{prop_name}' doesn't exist for '{location}'. Adding it.")
            # Decide if dynamic property creation is allowed or should error

        old_value = self.location_properties[location].get(prop_name, 'None')
        if old_value != value:
            self.location_properties[location][prop_name] = value
            # Log the change as an event? Depends on granularity needed.
            # Example: log the *effect* rather than the state change itself.
            # e.g., if setting door_locked=False, the event might be "The shelter door unlocks"
            print(
                f"[World State Update]: Property '{prop_name}' of '{location}' changed to '{value}' (Trigger: {triggered_by}).")
            return True
        return False
    
    # --- End NEW Helpers ---

    def add_agent_to_location(self, agent_name, location_name, triggered_by="Setup"):
        """Adds agent and updates location state if needed."""
        if location_name in self.location_descriptions:
            old_location = self.agent_locations.get(agent_name)
            self.agent_locations[agent_name] = location_name
            print(f"World: Agent {agent_name} now at {location_name}")

            # Update 'contains' property if location has it
            if old_location and old_location != location_name:
                if 'contains' in self.location_properties.get(old_location, {}):
                    if agent_name in self.location_properties[old_location]['contains']:
                        self.location_properties[old_location]['contains'].remove(
                            agent_name)

            if 'contains' in self.location_properties.get(location_name, {}):
                if agent_name not in self.location_properties[location_name]['contains']:
                    self.location_properties[location_name]['contains'].append(
                        agent_name)

            # Log the arrival event (could be refined based on triggered_by)
            if triggered_by != "Setup":  # Don't log redundant 'appears' if moving
                self.log_event(f"{agent_name} arrives.", scope='local',
                                location=location_name, triggered_by=triggered_by)
            elif not old_location:  # Log initial appearance
                self.log_event(f"{agent_name} appears in the {location_name}.",
                                scope='local', location=location_name, triggered_by=triggered_by)
        else:
            print(
                f"Warning: Cannot move {agent_name} to unknown location '{location_name}'")

    def get_agents_at(self, location_name):
        # Add simple check if location exists
        if location_name not in self.location_descriptions:
            return []
        return [name for name, loc in self.agent_locations.items() if loc == location_name]

    def log_event(self, description, scope='local', location=None, triggered_by="Simulation", dispatch=True):
        """Logs an event and dispatches it to relevant registered agents."""
        new_event = Event(description=description, location=location,
                          scope=scope, step=self.current_step, triggered_by=triggered_by)
        self.event_log.append(new_event)
        log_prefix = f"[Event Log Step {self.current_step}][{triggered_by} @ {location or 'Global'}/{scope}]"
        print(f"{log_prefix}: {description}")

        # Trim log if needed
        if len(self.event_log) > config.MAX_RECENT_EVENTS * 2:  # Keep a longer internal log
            self.event_log.pop(0)

        # --- Event Dispatch Logic ---
        if dispatch and config.EVENT_PERCEPTION_MODEL == "DirectDispatch":
            dispatched_to = []
            for agent_name, agent_obj in self.registered_agents.items():
                agent_current_loc = self.agent_locations.get(agent_name)
                should_perceive = False
                # Global events are perceived by everyone
                if scope == 'global':
                    should_perceive = True
                # Local events are perceived by agents at that location
                elif scope == 'local' and location == agent_current_loc:
                    should_perceive = True
                # Action outcomes might be perceived by others at the location
                elif scope == 'action_outcome' and location == agent_current_loc:
                    # Avoid agent perceiving echo of their own action description? Maybe filter here.
                    # if triggered_by != agent_name:  # Simple filter: don't dispatch action outcome to self
                    #     should_perceive = True
                    # Or let agent memory handle duplicates? Simpler for now.
                    should_perceive = True

                if should_perceive:
                    try:
                        agent_obj.perceive(new_event)
                        dispatched_to.append(agent_name)
                    except Exception as e:
                        print(
                            f"[Dispatch Error]: Failed to dispatch event to {agent_name}: {e}")
            if dispatched_to:
                print(
                    f"[World Event Dispatch]: Event dispatched to: {dispatched_to}")


    def set_weather(self, new_weather, triggered_by="Simulation"):
        """Changes the weather and logs the event."""
        old_weather = self.global_context.get('weather', 'unknown')
        if old_weather != new_weather:
            self.global_context['weather'] = new_weather
            # Log weather change as a GLOBAL event
            self.log_event(f"The weather changes from {old_weather} to {new_weather}.",
                           scope='global',
                           location=None,  # Global event has no specific location
                           triggered_by=triggered_by)
            return True
        return False

    def get_static_context_for_agent(self, agent_name):
         """Provides minimal, relatively static context."""
         location = self.agent_locations.get(agent_name)
         if not location: return "You are lost."

         context = f"Current Location: {location} ({self.location_descriptions.get(location, 'Unknown')}).\n"
         context += f"Current Weather: {self.global_context.get('weather', 'Unknown')}.\n"
         exits = self.get_reachable_locations(location)
         context += f"Visible Exits: {exits if exits else 'None'}.\n"
         # Add other static elements if needed (e.g., visible objects)
         return context

    def get_full_state_string(self):
        """For debugging - shows more structured log."""
        state = f"--- World State (Step: {self.current_step}) ---\n"
        state += f"Global Context: {self.global_context}\n"
        state += f"Agent Locations: {self.agent_locations}\n"
        state += f"Location Properties: {self.location_properties}\n"
        # Show who listens
        state += f"Registered Agents: {list(self.registered_agents.keys())}\n"
        state += f"Event Log ({len(self.event_log)} total, showing last {config.MAX_RECENT_EVENTS}):\n"
        display_events = self.event_log[-config.MAX_RECENT_EVENTS:]
        for event in display_events:
            state += f"  - St{event.step} [{event.triggered_by}@{event.location or 'Global'}/{event.scope}] {event.description}\n"
        return state + "-------------------"

    def apply_state_updates(self, updates: list, triggered_by: str):
        """Applies a list of state changes suggested by the Action Resolver."""
        if not updates:
            return

        print(
            f"[World State Apply]: Applying {len(updates)} updates triggered by {triggered_by}.")
        for update in updates:
            try:
                update_type = update[0]
                target = update[1]
                value = update[2]

                if update_type == "agent_location":
                    # Value is the new location name
                    self.add_agent_to_location(
                        agent_name=target, location_name=value, triggered_by=triggered_by)
                elif update_type == "location_property":
                    # Target is location name, value is prop_name, need 4th element for prop_value
                    if len(update) == 4:
                        prop_name = value
                        prop_value = update[3]
                        self.set_location_property(
                            location=target, prop_name=prop_name, value=prop_value, triggered_by=triggered_by)
                    else:
                        print(
                            f"[World State Apply Error]: Invalid format for location_property update: {update}")
                # Add more update types here (e.g., global context, agent inventory)
                else:
                    print(
                        f"[World State Apply Warning]: Unknown update type '{update_type}'")

            except IndexError as e:
                print(
                    f"[World State Apply Error]: Malformed update tuple {update}: {e}")
            except Exception as e:
                print(
                    f"[World State Apply Error]: Failed to apply update {update}: {e}")
