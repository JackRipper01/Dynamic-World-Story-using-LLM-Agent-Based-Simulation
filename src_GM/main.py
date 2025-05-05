# --- Imports ---
from collections import namedtuple  # For creating simple Event objects
import time  # For pausing execution (e.g., between agent actions)
from typing import List  # For type hinting lists (e.g., list of Agents)
import google.generativeai as genai  # Google's Generative AI library
import argparse  # For parsing command-line arguments

import config  # Import the whole config module to access global settings

# Import custom modules for simulation components
from world import WorldState
from agent.agent import Agent
from director import Director

# --- Data Structures ---

# Define a simple structure to represent events within the simulation
Event = namedtuple(
    "Event", ["description", "location", "scope", "step", "triggered_by"])

# --- Factory Functions for Components ---
# These functions allow creating different implementations of simulation components
# based on configuration strings, promoting modularity.


def get_memory_module(agent, memory_type):
    """Factory function to create an agent's memory module."""
    if memory_type == "SimpleMemory":
        from agent.memory import SimpleMemory
        return SimpleMemory()
    if memory_type == "ShortLongTMemory":
        from agent.memory import ShortLongTMemory
        # Example of passing configuration to a specific memory type
        return ShortLongTMemory(agent, reflection_threshold=10)
    else:
        # Handle unknown memory types specified in config
        raise ValueError(f"Unknown memory type: {memory_type}")


def get_planning_module(planning_type, model):
    """Factory function to create an agent's planning module (thinker)."""
    if planning_type == "GeminiThinker":
        from agent.planning import SimplePlanning
        return SimplePlanning(model)
    # Add other planning types here if needed
    # elif planning_type == "AnotherThinker":
    #     from agent.planning import AnotherThinker
    #     return AnotherThinker(...)
    else:
        # Handle unknown planning types specified in config
        raise ValueError(f"Unknown thinker type: {planning_type}")


def get_action_resolver(resolver_type, model, world_ref=None):
    """Factory function to create the action resolver."""
    if resolver_type == "LLMResolver":
        from action_resolver import LLMActionResolver
        # Pass the language model and a reference to the world state
        return LLMActionResolver(model, world_ref)
    # Add other resolver types here if needed
    # elif resolver_type == "RuleBasedResolver":
    #     from action_resolver import RuleBasedResolver
    #     return RuleBasedResolver(...)
    else:
        # Handle unknown resolver types specified in config
        raise ValueError(f"Unknown action resolver type: {resolver_type}")


def get_event_dispatcher(dispatcher_type: str):
    """Factory function to create the event dispatcher."""
    if dispatcher_type == "DirectEventDispatcher":
        from event_dispatcher import DirectEventDispatcher
        return DirectEventDispatcher()
    # Add other dispatcher types here if needed
    # elif dispatcher_type == "FilteredEventDispatcher":
    #     from event_dispatcher import FilteredEventDispatcher
    #     return FilteredEventDispatcher(...)
    else:
        # Handle unknown dispatcher types specified in config
        raise ValueError(f"Unknown event dispatcher type: {dispatcher_type}")

# --- Main Simulation Function ---


def run_simulation():
    """
    Sets up and runs the agent simulation loop.
    Initializes the world, agents, director, and other components based on the 'config' module.
    Manages the main simulation steps, including agent thinking, action resolution,
    world updates, event dispatching, and user interaction.
    Output verbosity depends on the config.SIMULATION_MODE ('debug' or 'story').
    """

    # --- Initialization Phase ---
    # Configure logging based on the simulation mode set in config
    if config.SIMULATION_MODE == 'debug':
        print("--- Starting Agent Simulation with Director (DEBUG MODE) ---")
        print(f"Config: Memory={config.AGENT_MEMORY_TYPE}, Thinker={config.AGENT_PLANNING_TYPE}, Resolver={config.ACTION_RESOLVER_TYPE}, Perception={config.EVENT_PERCEPTION_MODEL}")
    elif config.SIMULATION_MODE == 'story':
        print("--- Starting Agent Simulation ---")

    # 1. Initialize LLM Model
    if config.SIMULATION_MODE == 'debug':
        print(f"Configuring Gemini model: {config.MODEL_NAME}")
    # Configure the generative AI model using the API key from config
    genai.configure(api_key=config.GEMINI_API_KEY)
    # Create the specific generative model instance
    model = genai.GenerativeModel(
        model_name=config.MODEL_NAME,
        generation_config=config.GENERATION_CONFIG,
    )
    if config.SIMULATION_MODE == 'debug':
        print("Model configured.")

    # 2. Initialize World State and Event Dispatcher
    # Create the event dispatcher using the factory function based on config
    event_dispatcher = get_event_dispatcher(config.EVENT_PERCEPTION_MODEL)
    # Create the world state with known locations from config
    world = WorldState(locations=config.KNOWN_LOCATIONS)
    # Set initial global context (e.g., weather)
    world.global_context['weather'] = "Clear"
    if config.SIMULATION_MODE == 'debug':
        print("World state and event dispatcher initialized.")

    # 3. Initialize Agents
    agents: List[Agent] = []  # Type hint for a list of Agent objects
    if config.SIMULATION_MODE == 'debug':
        print("Initializing agents...")
    # Loop through agent configurations defined in the config module
    for agent_conf in config.agent_configs:
        agent_name = agent_conf["name"]
        # Create the planning module (thinker) for the agent
        thinker = get_planning_module(config.AGENT_PLANNING_TYPE, model)
        # Create the Agent instance
        agent = Agent(
            name=agent_name,
            gender=agent_conf["gender"],
            personality=agent_conf["personality"],
            initial_goals=agent_conf["initial_goals"],
            memory_module=None,  # Memory will be assigned below
            planning_module=thinker
        )
        # Create and assign the memory module using the factory function
        agent.memory = get_memory_module(agent, config.AGENT_MEMORY_TYPE)

        # Add the agent to the simulation's list of agents
        agents.append(agent)
        # Set the agent's starting location in the world state
        start_location = agent_conf["initial_location"]
        world.add_agent_to_location(
            agent_name, start_location, triggered_by="Setup")  # Log the setup action
        # Register the agent instance with the world (for lookups, event dispatching)
        world.register_agent(agent)
        if config.SIMULATION_MODE == 'debug':
            print(f"- Agent '{agent_name}' created at '{start_location}'.")

    if config.SIMULATION_MODE == 'debug':
        print("Agents initialized.")

    # 4. Initialize Director
    director_model = model  # The director might use the same LLM or a different one
    # Create the Director instance, passing the world, model, and narrative goal
    director = Director(world, director_model, config.NARRATIVE_GOAL)
    if config.SIMULATION_MODE == 'debug':
        print(f"Director initialized with goal: '{config.NARRATIVE_GOAL}'")

    # 5. Initialize Action Resolver
    # Create the action resolver using the factory function
    action_resolver = get_action_resolver(
        config.ACTION_RESOLVER_TYPE, model, world_ref=world)  # Pass world reference
    if config.SIMULATION_MODE == 'debug':
        print("Action resolver initialized.")

    # ---------------------------------------- Simulation Steps ----------------------------------------
    step = 0  # Initialize step counter
    # Main simulation loop, continues until max steps are reached
    while step < config.SIMULATION_MAX_STEPS:
        step += 1  # Increment step counter
        world.advance_step()  # Advance the world's internal clock/step counter

        # Print step header based on simulation mode
        if config.SIMULATION_MODE == 'debug':
            print(
                f"\n{'='*15} Simulation Step {step}/{config.SIMULATION_MAX_STEPS} {'='*15}")
            # In debug mode, print the full world state at the start of the step
            print(world.get_full_state_string())
        elif config.SIMULATION_MODE == 'story':
            print(f"\n--- TIME STEP {step} ---")

        # ---------------------------------------- Agent Thinking Phase ----------------------------------------
        # Each agent observes the world and decides on their next action/intention.
        if config.SIMULATION_MODE == 'debug':
            print("\n--- Agent Thinking Phase ---")
        agent_intentions = {}  # Store planned action/intention for each agent
        agent_current_locations = {}  # Store current location for action resolution context
        for agent in agents:
            if config.SIMULATION_MODE == 'debug':
                print(f"\n-- Processing {agent.name} --")
            # Get the agent's current location from the world state
            current_loc = world.agent_locations.get(agent.name, None)
            # Handle cases where an agent might not have a location (should ideally not happen)
            if not current_loc:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"[Sim Warning]: Agent {agent.name} has no location! Skipping.")
                continue  # Skip this agent for this step
            agent_current_locations[agent.name] = current_loc  # Store location

            # Ask the agent to plan its action based on the current world state
            intended_output = agent.plan(world)
            # Store the intention
            agent_intentions[agent.name] = intended_output

            # Optional pause to avoid hitting API rate limits or to slow down simulation
            time.sleep(1.0)

        # ---------------------------------------- Action Resolution Phase ----------------------------------------
        # The Action Resolver interprets agent intentions and determines the outcomes
        # and necessary world state changes.
        if config.SIMULATION_MODE == 'debug':
            print("\n--- Action Resolution Phase ---")

        resolution_results = {}  # Store the outcome dict from the resolver for each agent
        all_state_updates = []  # Collect ALL state update instructions before applying them
        # Collect events resulting from actions (success or failure)
        all_outcome_events = []

        # Iterate through the intentions planned by each agent
        for agent_name, intent in agent_intentions.items():
            agent_loc = agent_current_locations.get(agent_name)
            # Ensure the agent has a location and the action resolver is available
            if agent_loc and action_resolver:
                if config.SIMULATION_MODE == 'debug':
                    print(f"-- Resolving for {agent_name} at {agent_loc} --")
                # Call the action resolver to determine the outcome of the intended action
                result = action_resolver.resolve(
                    agent_name, agent_loc, intent, world
                )
                resolution_results[agent_name] = result  # Store the raw result

                # --- Process Successful Action ---
                if result and result.get("success"):
                    outcome_desc = result.get(
                        'outcome_description', f"{agent_name} acted.")  # Default description
                    if config.SIMULATION_MODE == 'debug':
                        # Detailed debug log for successful action
                        print(
                            f"[Resolver OK] {agent_name}: {result.get('action_type')} -> {outcome_desc}")
                    if config.SIMULATION_MODE == 'story':
                        # Narrative output for successful action
                        # Add extra newline for story readability
                        print(f"{outcome_desc}\n\n")

                    # Collect world state updates if the action caused any
                    if result.get("world_state_updates"):
                        all_state_updates.extend(result["world_state_updates"])
                    # Collect the outcome event to be logged and potentially perceived
                    all_outcome_events.append(
                        # description, scope, location, triggered_by
                        (outcome_desc, 'action_outcome', agent_loc, agent_name)
                    )
                # --- Process Failed Action ---
                elif result:  # If result exists but 'success' is not True
                    reason = result.get('reasoning', 'Unknown reason')
                    outcome_desc = result.get(
                        'outcome_description', 'Action failed.')
                    if config.SIMULATION_MODE == 'debug':
                        # Detailed debug log for failed action
                        print(f"[Resolver FAIL] {agent_name}: {reason}")
                        print(f"   Outcome: {outcome_desc}")
                    if config.SIMULATION_MODE == 'story':
                        # Narrative output for failed action
                        print(
                            f"{agent_name} tried to act, but {outcome_desc.lower()}")  # Narrative phrasing

                    # Collect the failure outcome event
                    all_outcome_events.append(
                        (outcome_desc, 'action_outcome', agent_loc, agent_name)
                    )
                # --- Handle Resolver Errors ---
                else:  # If the resolver returned None or an unexpected structure
                    error_msg = f"System error resolving {agent_name}'s action."
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"[Resolver ERROR] Critical failure resolving for {agent_name}")
                    if config.SIMULATION_MODE == 'story':
                        print(
                            f"[System Note] Issue resolving {agent_name}'s action.")
                    # Log a system error event
                    all_outcome_events.append(
                        (error_msg, 'system_error', agent_loc,
                        'System')  # Use 'System' as trigger
                    )
            # --- Handle Missing Agent Location or Resolver ---
            else:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"[Sim Warning]: Cannot resolve action for {agent_name}, location or resolver unknown.")
            # Optional pause between resolving actions
            time.sleep(0.5)

        # ---------------------------------------- World Update Phase ----------------------------------------
        # Apply all collected state changes to the world simultaneously.
        if config.SIMULATION_MODE == 'debug':
            print("\n--- World Update Phase ---")
        if all_state_updates:
            # Apply the list of update instructions to the world state
            world.apply_state_updates(
                all_state_updates, triggered_by="AgentActions")  # Indicate the trigger
            if config.SIMULATION_MODE == 'debug':
                print("Applied world state updates.")
        else:
            # No updates were generated in this step
            if config.SIMULATION_MODE == 'debug':
                print("No world state updates required.")

        # ---------------------------------------- Agents Perceiving and Event Logging Phase ----------------------------------------
        # Log the outcomes of actions as events and dispatch them so agents can perceive them.
        if config.SIMULATION_MODE == 'debug':
            print("\n--- Logging Action Outcomes & Dispatching Events ---")
        # Iterate through the collected outcome events (successes, failures, errors)
        for desc, scope, loc, trig_by in all_outcome_events:
            # 1. Log the event to the world's historical record
            world.log_event(desc, scope, loc, trig_by)

            # 2. Create an Event object
            new_event = Event(
                description=desc,
                location=loc,
                scope=scope,
                step=world.current_step,
                triggered_by=trig_by
            )
            # 3. Dispatch the event using the configured dispatcher
            # The dispatcher determines which agents should perceive this event
            event_dispatcher.dispatch_event(
                new_event, world.registered_agents, world.agent_locations)

        # ---------------------------------------- End Step ----------------------------------------
        if config.SIMULATION_MODE == 'debug':
            print("\n--- End of Step ---")
            # Print the final world state after all updates and events for the step
            print(world.get_full_state_string())

        # ---------------------------------------- User Input ----------------------------------------
        # Allows pausing the simulation, quitting, or changing parameters mid-run.
        user_input = input(
            "Enter for next step, 'goal <new goal>' to change director goal, 'w <weather>' for weather, 'q' to quit: "
        ).lower().strip()

        if user_input == 'q':
            # Quit the simulation loop
            print("Quitting simulation by user request.")
            break
        elif user_input.startswith('goal '):
            # Change the director's narrative goal dynamically
            new_goal = user_input[len('goal '):].strip()
            if new_goal:
                print(f"Updating Director goal to: '{new_goal}'")
                director.narrative_goal = new_goal
                # Log this user command as a world event
                world.log_event(
                    f"COMMAND: Director narrative goal updated to '{new_goal}'.",
                    scope="global", location="world", triggered_by="User"
                )
            else:
                print("Invalid command. Use 'goal <description>'.")
        elif user_input.startswith('w '):
            # Manually override the weather
            # Capitalize words
            new_weather = user_input[len('w '):].strip().title()
            if new_weather:
                print(f"Manual weather override to: {new_weather}")
                # Update world state and log event
                world.set_weather(new_weather, triggered_by="User")
            else:
                print("Invalid command. Use 'w <condition>'.")
        # Handle empty input (just press Enter) or unknown commands
        elif user_input:
            if user_input:  # Only print error if it wasn't just Enter
                print(
                    f"Unknown command: '{user_input}'. Press Enter to continue.")
            # Otherwise, pressing Enter just proceeds to the next step

    # ---------------------------------------- Simulation End ----------------------------------------
    print(f"\n--- Simulation Ended after {step} steps ---")


# --- Main Execution Block ---
if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Run Agent Simulation")
    # Create a mutually exclusive group: user must choose --debug OR --story
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--debug', action='store_true',
                       help='Enable detailed debug logging.')
    group.add_argument('--story', action='store_true',
                       help='Enable narrative story logging.')

    # Parse the command-line arguments provided by the user
    args = parser.parse_args()

    # Set the global simulation mode in the config module based on the arguments.
    # This allows other modules imported after this point to easily check the mode.
    config.SIMULATION_MODE = 'debug' if args.debug else 'story'

    # Call the main simulation function, which will now use the mode set in config
    run_simulation()
