# src/world.py
from typing import Dict, List, Any  # Added List and Any
import config
from collections import namedtuple
from agent.agent import Agent

# Define a structure for events for clarity
Event = namedtuple(
    "Event", ["description", "location", "scope", "step", "triggered_by"]
)


class WorldState:
    # Modified signature
    def __init__(self, known_locations_data: Dict[str, Dict[str, Any]]):
        # agent_name -> location_name
        self.agent_locations: Dict[str, str] = {}

        self.location_descriptions: Dict[str, str] = {}
        self.location_connectivity: Dict[str, List[str]] = {}
        self.location_properties: Dict[str, Dict[str, Any]] = {}

        for loc_name, loc_data in known_locations_data.items():
            self.location_descriptions[loc_name] = loc_data.get(
                "description", "An undescribed location.")
            self.location_connectivity[loc_name] = loc_data.get("exits_to", [])

            # Initialize properties, ensuring "contains" (for items) exists
            props = loc_data.get("properties", {})
            if "contains" not in props:
                # Ensure 'contains' for items is always a list
                props["contains"] = []
            self.location_properties[loc_name] = props

        if config.SIMULATION_MODE == 'debug':
            print(
                f"[World Init] Locations initialized: {list(self.location_descriptions.keys())}")
            print(f"[World Init] Connectivity: {self.location_connectivity}")
            print(f"[World Init] Properties: {self.location_properties}")

        self.global_context: Dict[str, Any] = {"weather": "Clear"}
        self.event_log: List[Event] = []  # Now stores Event tuples
        self.current_step: int = 0  # Track simulation step

        self.registered_agents: Dict[str, Agent] = {}

    def register_agent(self, agent: Agent):
        """Registers an agent to receive events."""
        if agent.name not in self.registered_agents:
            self.registered_agents[agent.name] = agent
            if config.SIMULATION_MODE == 'debug':  # Added debug print
                print(
                    f"[World Event Update]: Registered {agent.name} for events.")

    def unregister_agent(self, agent_name: str):
        """Unregisters an agent."""
        if agent_name in self.registered_agents:
            del self.registered_agents[agent_name]
            if config.SIMULATION_MODE == 'debug':  # Added debug print
                print(f"[World Event Update]: Unregistered {agent_name}.")

    def advance_step(self):
        self.current_step += 1

    def get_reachable_locations(self, from_location: str) -> List[str]:
        """Returns list of locations directly reachable from the given one."""
        return self.location_connectivity.get(from_location, [])

    def get_location_property(self, location: str, prop_name: str) -> Any:
        """Safely gets a property of a location."""
        return self.location_properties.get(location, {}).get(prop_name, None)

    def set_location_property(self, location: str, prop_name: str, value: Any, triggered_by: str = "System") -> bool:
        """Sets a property, potentially logging an event via log_event."""
        if location not in self.location_properties:
            # This should ideally not happen if locations are well-defined in config
            # Create location properties if missing
            self.location_properties[location] = {}
            print(
                f"[World State Warning]: Location '{location}' properties not found, created. Consider defining it in config."
            )
            # Ensure 'contains' is initialized if we are creating the location properties on the fly
            if "contains" not in self.location_properties[location]:
                self.location_properties[location]["contains"] = []

        # Allow adding new properties dynamically if they don't exist
        if prop_name not in self.location_properties[location]:
            print(
                f"[World State Info]: Property '{prop_name}' doesn't exist for '{location}'. Adding it."
            )

        old_value = self.location_properties[location].get(
            prop_name)  # Simpler get
        if old_value != value:
            self.location_properties[location][prop_name] = value
            if config.SIMULATION_MODE == 'debug':  # Added debug print
                print(
                    f"[World State Update]: Property '{prop_name}' of '{location}' changed from '{old_value}' to '{value}' (Trigger: {triggered_by})."
                )
            
            return True
        return False

    def add_agent_to_location(self, agent_name: str, location_name: str, triggered_by: str = "Setup"):
        """Adds agent to a location. Agent presence is tracked in self.agent_locations."""
        if location_name in self.location_descriptions:
            old_location = self.agent_locations.get(agent_name)
            self.agent_locations[agent_name] = location_name

            if config.SIMULATION_MODE == 'debug':  # Added debug print
                print(
                    f"[World State Update]: Agent {agent_name} moved from {old_location or 'None'} to {location_name} (Trigger: {triggered_by})")

            # Agent presence is NOT tracked in location_properties["contains"] anymore.
            # That key is for objects/items within the location.

            # Log the arrival event
            if triggered_by != "Setup":
                # Optionally, log departure from old location
                if old_location and old_location != location_name:
                    self.log_event(
                        f"{agent_name} departs from the {old_location}.",
                        scope="local",
                        location=old_location,
                        triggered_by=triggered_by
                    )
                # If moving, log arrival at new location
                self.log_event(
                    # Made description more specific
                    f"{agent_name} arrives at the {location_name}.",
                    scope="local",
                    location=location_name,
                    triggered_by=triggered_by,
                )
            elif not old_location:  # Log initial appearance only if no prior location
                self.log_event(
                    f"{agent_name} appears in the {location_name}.",
                    scope="local",
                    location=location_name,
                    triggered_by=triggered_by,
                )
        else:
            print(
                f"[World State Error]: Cannot move {agent_name} to unknown location '{location_name}'"
            )

    def get_agents_at(self, location_name: str) -> List[str]:
        if location_name not in self.location_descriptions:
            if config.SIMULATION_MODE == 'debug':
                print(
                    f"[World State Warning]: Tried to get agents at unknown location '{location_name}'")
            return []
        return [
            name for name, loc in self.agent_locations.items() if loc == location_name
        ]

    def log_event(
        self,
        description: str,
        scope: str = "local",
        location: str = None,
        triggered_by: str = "Simulation",
        # dispatch parameter removed, dispatching is handled by main loop calling dispatcher
    ):
        """Logs an event to the world's event log."""
        new_event = Event(
            description=description,
            location=location,
            scope=scope,
            step=self.current_step,
            triggered_by=triggered_by,
        )
        self.event_log.append(new_event)

        # Optional detailed logging for debug mode
        if config.SIMULATION_MODE == "debug":
            log_prefix = f"[Event Logged S{self.current_step}][{triggered_by} @ {location or 'Global'}/{scope}]"
            print(f"{log_prefix}: {description}")

        if len(self.event_log) > config.MAX_RECENT_EVENTS * 2:
            self.event_log.pop(0)

    def set_weather(self, new_weather: str, triggered_by: str = "Simulation") -> bool:
        """Changes the weather and logs the event."""
        old_weather = self.global_context.get("weather", "unknown")
        if old_weather != new_weather:
            self.global_context["weather"] = new_weather
            self.log_event(
                f"The weather changes from {old_weather} to {new_weather}.",
                scope="global",
                location=None,
                triggered_by=triggered_by,
            )
            if config.SIMULATION_MODE == 'debug':  # Added debug print
                print(
                    f"[World State Update]: Weather changed to {new_weather} (Trigger: {triggered_by})")
            return True
        return False

    def get_static_context_for_agent(self, agent_name: str) -> str:
        """Provides minimal, relatively static context for an agent, focusing on items and their states."""
        location = self.agent_locations.get(agent_name)
        if not location:
            return f"{agent_name} is lost and disoriented."

        # --- Basic Info & Main Description ---
        # The core description comes directly from the location definition
        location_description = self.location_descriptions.get(
            location, 'An unknown place')
        context = f"Current Location: {location} ({location_description}).\n"

        # --- Environmental Context ---
        context += f"Current Weather: {self.global_context.get('weather', 'Indeterminate')}.\n"
        exits = self.get_reachable_locations(location)
        context += f"Visible Exits: {', '.join(exits) if exits else 'None apparent'}.\n"

        # --- Other Agents ---
        other_agents = [
            name for name in self.get_agents_at(location) if name != agent_name
        ]
        if other_agents:
            context += f"Others present: {', '.join(other_agents)}.\n"
        else:
            context += f"{agent_name} is alone here.\n"

        # --- Items/Objects and their State (from location_properties["contains"]) ---
        location_props = self.location_properties.get(location, {})
        items_list = location_props.get("contains", [])
        item_descriptions = []

        if isinstance(items_list, list):  # Ensure it's a list
            for item_data in items_list:
                if isinstance(item_data, dict):  # Ensure each item is a dict
                    obj_name = item_data.get("object")
                    obj_state = item_data.get("state")
                    obj_desc = item_data.get(
                        "optional_description")  # Optional

                    if obj_name and obj_state is not None:  # Require object name and state
                        desc_str = ""
                        # Start with description + name or just name
                        if obj_desc:
                            # e.g., "a sturdy wooden door (Shelter Door)"
                            desc_str += f"{obj_desc} ({obj_name})"
                        else:
                            # e.g., "chair"
                            desc_str += f"{obj_name}"

                        # Add the state clearly
                        # e.g., " - currently locked", " - currently occupied by Alice"
                        desc_str += f" - currently {obj_state}"
                        item_descriptions.append(desc_str)
                    else:
                        if config.SIMULATION_MODE == 'debug':
                            print(
                                f"[World Context Warning] Item in '{location}' missing 'object' or 'state': {item_data}")
                else:
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"[World Context Warning] Item in '{location}' is not a dictionary: {item_data}")

        if item_descriptions:
            context += "Items and features you observe:\n"
            for item_desc in item_descriptions:
                context += f"- {item_desc}\n"
        else:
            # Refined message when no specific items are listed
            context += "There are no specific items demanding attention right now.\n"

        return context.strip()

    def get_full_state_string(self) -> str:
        """For debugging - shows more structured log."""
        state = f"--- World State (Step: {self.current_step}) ---\n"
        state += f"Global Context: {self.global_context}\n"
        state += f"Agent Locations: {self.agent_locations}\n"
        state += "Location Details:\n"
        for loc_name in self.location_descriptions:
            state += f"  - {loc_name}:\n"
            state += f"    Description: {self.location_descriptions.get(loc_name, 'N/A')}\n"
            state += f"    Exits: {self.location_connectivity.get(loc_name, [])}\n"
            state += f"    Properties: {self.location_properties.get(loc_name, {})}\n"
            state += f"    Agents Here: {self.get_agents_at(loc_name)}\n"

        # Clarified
        state += f"Registered Agents for Events: {list(self.registered_agents.keys())}\n"
        state += f"Event Log ({len(self.event_log)} total, showing last {config.MAX_RECENT_EVENTS}):\n"
        display_events = self.event_log[-config.MAX_RECENT_EVENTS:]
        for event in display_events:  # Corrected variable name
            state += f"  - St{event.step} [{event.triggered_by}@{event.location or 'Global'}/{event.scope}] {event.description}\n"
        return state + "-------------------"

    def apply_state_updates(self, updates: List[tuple], triggered_by: str):
        """Applies a list of state changes suggested by the Action Resolver."""
        if not updates:
            return

        if config.SIMULATION_MODE == 'debug':  # Added debug print
            print(
                f"[World State Apply]: Applying {len(updates)} updates triggered by {triggered_by}: {updates}"
            )
        for update_tuple in updates:  # Renamed for clarity
            try:
                update_type = update_tuple[0]
                # e.g., agent_name or location_name
                target_name = update_tuple[1]

                if update_type == "agent_location":
                    new_location = update_tuple[2]
                    self.add_agent_to_location(
                        agent_name=target_name,
                        location_name=new_location,
                        triggered_by=triggered_by,
                    )
                elif update_type == "location_property":
                    if len(update_tuple) == 4:
                        prop_name = update_tuple[2]
                        prop_value = update_tuple[3]
                        self.set_location_property(
                            location=target_name,
                            prop_name=prop_name,
                            value=prop_value,
                            triggered_by=triggered_by,
                        )
                
                    else:
                        print(
                            f"[World State Apply Error]: Invalid format for location_property update: {update_tuple}"
                        )
                # Add more update types here (e.g., add_item_to_location, remove_item_from_location)
                
                elif update_type == "item_state":
                    # update_tuple: ('item_state', location_name, item_name_to_update, new_item_state)
                    # target_name is location_name here
                    if len(update_tuple) == 4:
                        location_name = target_name  # Location of the primary item
                        # Name of the primary item
                        item_name_to_update = update_tuple[2]
                        # New state for the primary item (and linked item)
                        new_item_state = update_tuple[3]

                        items_in_location = self.get_location_property(
                            location_name, "contains")
                        # item_actually_updated flag removed as linked logic is now inside the state change block
                        original_item_found = False

                        if isinstance(items_in_location, list):
                            for item_data in items_in_location:  # item_data is for the primary item
                                if isinstance(item_data, dict) and item_data.get("object") == item_name_to_update:
                                    original_item_found = True
                                    old_state = item_data.get("state")
                                    if old_state != new_item_state:
                                        # Directly update the primary item's state
                                        item_data["state"] = new_item_state

                                        if config.SIMULATION_MODE == 'debug':
                                            print(
                                                f"[World State Update]: Item '{item_name_to_update}' in '{location_name}' state changed from '{old_state}' to '{new_item_state}' (Trigger: {triggered_by})."
                                            )
                                        # Log a specific event for the primary item state change
                                        self.log_event(
                                            description=f"The state of {item_name_to_update} (in {location_name}) is now '{new_item_state}'.",
                                            scope="local",
                                            location=location_name,
                                            triggered_by=triggered_by
                                        )

                                        # --- START: Handle Linked Objects ---
                                        linked_to_info = item_data.get(
                                            "linked_to")
                                        if isinstance(linked_to_info, dict) and "location" in linked_to_info and "object_key" in linked_to_info:
                                            linked_loc_name = linked_to_info["location"]
                                            # Key of the item in the other location
                                            linked_obj_key = linked_to_info["object_key"]

                                            linked_location_items = self.get_location_property(
                                                linked_loc_name, "contains")
                                            if isinstance(linked_location_items, list):
                                                for linked_item_data in linked_location_items:
                                                    if isinstance(linked_item_data, dict) and linked_item_data.get("object") == linked_obj_key:
                                                        old_linked_state = linked_item_data.get(
                                                            "state")
                                                        if old_linked_state != new_item_state:  # Propagate the new state
                                                            linked_item_data["state"] = new_item_state
                                                            if config.SIMULATION_MODE == 'debug':
                                                                print(
                                                                    f"[World State Update - Linked]: Item '{linked_obj_key}' in '{linked_loc_name}' state "
                                                                    f"changed from '{old_linked_state}' to '{new_item_state}' "
                                                                    f"(due to link from '{item_name_to_update}' in '{location_name}' by {triggered_by})."
                                                                )
                                                            # Log an event for the linked item's change so agents there can perceive it
                                                            self.log_event(
                                                                description=f"The {linked_obj_key} is now '{new_item_state}', as it's linked to an item affected by {triggered_by}'s action.",
                                                                scope="local",
                                                                location=linked_loc_name,
                                                                triggered_by="SystemLink"  # Special trigger for system-driven linked changes
                                                            )
                                                        break  # Found and processed the linked item
                                                else:  # Inner loop's else: if linked item not found in linked_location_items
                                                    if config.SIMULATION_MODE == 'debug':
                                                        print(
                                                            f"[World State Apply Warning]: Linked item '{linked_obj_key}' in '{linked_loc_name}' "
                                                            f"(linked from '{item_name_to_update}' in '{location_name}') not found in 'contains' list."
                                                        )
                                            else:  # linked_location_items is not a list
                                                if config.SIMULATION_MODE == 'debug':
                                                    print(
                                                        f"[World State Apply Error]: 'contains' property for linked location '{linked_loc_name}' "
                                                        "is not a list or is missing when trying to update linked item state."
                                                    )
                                        # --- END: Handle Linked Objects ---
                                    else:  # old_state == new_item_state
                                        if config.SIMULATION_MODE == 'debug':
                                            print(
                                                f"[World State Info]: Item '{item_name_to_update}' in '{location_name}' state is already '{new_item_state}'. No change made.")
                                    break  # Primary item found and processed.

                            if not original_item_found:
                                print(
                                    f"[World State Apply Warning]: Could not update item '{item_name_to_update}' in '{location_name}'. Item not found in 'contains' list during update attempt.")
                        else:  # items_in_location is not a list
                            print(
                                f"[World State Apply Error]: 'contains' property for '{location_name}' is not a list or is missing when trying to update item state.")
                    else:  # len(update_tuple) != 4
                        print(
                            f"[World State Apply Error]: Invalid format for item_state update: {update_tuple}"
                        )
                else:  # Unknown update_type
                    print(
                        f"[World State Apply Warning]: Unknown update type '{update_type}' in {update_tuple}"
                    )

            except IndexError as e:
                print(
                    f"[World State Apply Error]: Malformed update tuple {update_tuple}: {e}"
                )
            except Exception as e:
                print(
                    f"[World State Apply Error]: Failed to apply update {update_tuple}: {e}"
                )

    def add_item_to_location(self, location_name: str, item_name: str, item_state: str, item_description: str, triggered_by: str = "System") -> bool:
        if location_name not in self.location_properties:
            if config.SIMULATION_MODE == 'debug':
                print(
                    f"[WorldState Error] Add Item: Location '{location_name}' not found.")
            return False

        # Ensure 'contains' is a list
        if "contains" not in self.location_properties[location_name] or not isinstance(self.location_properties[location_name]["contains"], list):
            self.location_properties[location_name]["contains"] = []

        # Check if item already exists (by name) to avoid duplicates, or decide policy
        for item_data in self.location_properties[location_name]["contains"]:
            if isinstance(item_data, dict) and item_data.get("object") == item_name:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"[WorldState Info] Add Item: Item '{item_name}' already exists in '{location_name}'. Not adding again.")
                # Optionally, update existing item's state/desc here, or just return False
                return False  # For now, don't add if name exists

        new_item = {
            "object": item_name,
            "state": item_state,
            "optional_description": item_description
            # "linked_to": {} # Could be added if director specifies linkage
        }
        self.location_properties[location_name]["contains"].append(new_item)

        # log_msg = f"{triggered_by} causes '{item_name}' (described as: {item_description}, state: {item_state}) to appear in {location_name}."
        # self.log_event(
        #     description=log_msg,
        #     scope="local",
        #     location=location_name,
        #     triggered_by=triggered_by
        # )
        if config.SIMULATION_MODE == 'debug':
            print(
                f"[WorldState Update] Add Item: '{item_name}' added to '{location_name}' by {triggered_by}.")
        return True

    def modify_item_state(self, location_name: str, item_name: str, new_state: str, triggered_by: str = "System") -> bool:
        if location_name not in self.location_properties:
            if config.SIMULATION_MODE == 'debug':
                print(
                    f"[WorldState Error] Modify Item State: Location '{location_name}' not found.")
            return False

        items_in_location = self.get_location_property(
            location_name, "contains")
        if not isinstance(items_in_location, list):
            if config.SIMULATION_MODE == 'debug':
                print(
                    f"[WorldState Error] Modify Item State: 'contains' for '{location_name}' is not a list.")
            return False

        item_found_and_updated = False
        for item_data in items_in_location:
            if isinstance(item_data, dict) and item_data.get("object") == item_name:
                old_state = item_data.get("state")
                if old_state != new_state:
                    item_data["state"] = new_state
                    item_found_and_updated = True  # Mark as updated

                    log_msg = f"The state of '{item_name}' in {location_name} changes from '{old_state}' to '{new_state}' (due to {triggered_by})."
                    self.log_event(
                        description=log_msg,
                        scope="local",
                        location=location_name,
                        triggered_by=triggered_by
                    )
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"[WorldState Update] Modify Item State: '{item_name}' in '{location_name}' changed to '{new_state}' by {triggered_by}.")

                    # --- Handle Linked Objects (copied and adapted from apply_state_updates) ---
                    linked_to_info = item_data.get("linked_to")
                    if isinstance(linked_to_info, dict) and "location" in linked_to_info and "object_key" in linked_to_info:
                        linked_loc_name = linked_to_info["location"]
                        linked_obj_key = linked_to_info["object_key"]
                        # Recursively call or directly implement linked update logic here
                        # For simplicity, let's assume modify_item_state can be called for the linked item
                        # This might need careful handling to avoid infinite loops if links are bidirectional AND state changes trigger more state changes.
                        # However, here the trigger is external (Director), so it should be fine.
                        self.modify_item_state(
                            linked_loc_name, linked_obj_key, new_state, triggered_by=f"SystemLink (from {item_name})")
                    # --- End Handle Linked Objects ---
                    break  # Item found and updated
                else:  # State is already the new_state
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"[WorldState Info] Modify Item State: '{item_name}' in '{location_name}' is already '{new_state}'. No change by {triggered_by}.")
                    item_found_and_updated = True  # Still counts as "found" for returning True
                    break

        if not item_found_and_updated and config.SIMULATION_MODE == 'debug':
            print(
                f"[WorldState Warning] Modify Item State: Item '{item_name}' not found in '{location_name}' for update by {triggered_by}.")

        # Return true if found (even if state was same), false if not found
        return item_found_and_updated
