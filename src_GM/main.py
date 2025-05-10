# --- Imports ---
from collections import namedtuple  # For creating simple Event objects
import random
import time  # For pausing execution (e.g., between agent actions)
# For type hinting lists (e.g., list of Agents)
from typing import List, Optional
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
            background=agent_conf["background"],
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

    # # 4. Initialize Director
    # director_model = model  # The director might use the same LLM or a different one
    # # Create the Director instance, passing the world, model, and narrative goal
    # director = Director(world, director_model, config.NARRATIVE_GOAL)
    # if config.SIMULATION_MODE == 'debug':
    #     print(f"Director initialized with goal: '{config.NARRATIVE_GOAL}'")

    # 5. Initialize Action Resolver
    # Create the action resolver using the factory function
    action_resolver = get_action_resolver(
        config.ACTION_RESOLVER_TYPE, model, world_ref=world)  # Pass world reference
    if config.SIMULATION_MODE == 'debug':
        print("Action resolver initialized.")

    # ---------------------------------------- Simulation Steps ----------------------------------------
    step = 0  # Initialize step counter
    # Main simulation loop, continues until max steps are reached

    # Tracks agent from PREVIOUS step
    last_agent_acted_in_previous_step: Optional[Agent] = None

    while step < config.SIMULATION_MAX_STEPS:
        step += 1  # Increment step counter
        world.advance_step()  # Advance the world's internal clock/step counter

        # Print step header based on simulation mode
        if config.SIMULATION_MODE == 'debug':
            print(f"\n\n")  # Add an extra blank line for better separation
            header_text = f" SIMULATION STEP {step}/{config.SIMULATION_MAX_STEPS} "
            print(header_text.center(70, '='))  # Centered header with '=' fill
            print("\n--- WORLD STATE (Start of Step) ---")
            print(world.get_full_state_string())
            print("--- END OF WORLD STATE ---\n")
        elif config.SIMULATION_MODE == 'story':
            # Add more vertical spacing for story mode time steps
            print(f"\n\n--- TIME STEP {step} ---\n")

        # --- Determine Agent Turn Order for this Step ---
        current_step_agents_list: List[Agent] = []  # Temp list for clarity
        if not agents:
            pass  # No agents to process, current_step_agents_list remains empty
        elif len(agents) == 1:
            # Only one agent, order is fixed
            current_step_agents_list = list(agents)
        else:
            # Randomize order from the main 'agents' list
            # Use list(agents) if 'agents' might not be a list
            shuffled_agents = random.sample(list(agents), len(agents))

            # Ensure the last agent from the previous round isn't first in this one
            if last_agent_acted_in_previous_step and \
               shuffled_agents[0].name == last_agent_acted_in_previous_step.name:  # Compare by a unique ID like name
                # Simple fix: swap the first agent with the second agent.
                # This assumes len(shuffled_agents) > 1, which is true due to len(agents) > 1 check
                shuffled_agents[0], shuffled_agents[1] = shuffled_agents[1], shuffled_agents[0]
            current_step_agents_list = shuffled_agents

        # This is the list your loop will use
        current_step_agents = current_step_agents_list

        if config.SIMULATION_MODE == 'debug' and current_step_agents:
            agent_order_names = [a.name for a in current_step_agents]
            print(f"Agent turn order for step {step}: {agent_order_names}")
            if last_agent_acted_in_previous_step:
                print(
                    f"(Last agent in step {step-1} was: {last_agent_acted_in_previous_step.name})")

        # This variable will track the actual last agent who took a turn in THIS step
        agent_who_took_last_turn_this_step: Optional[Agent] = None

        # --- Sequential Agent Action, Resolution, and Perception Loop ---
        for agent in current_step_agents:
            if config.SIMULATION_MODE == 'debug':
                # More prominent agent turn header
                turn_header = f" AGENT: {agent.name}'s Turn "
                # Centered with hyphens
                print(f"\n{turn_header.center(60, '-')}")
                print(
                    f"Location: {world.agent_locations.get(agent.name, 'Unknown')}")

            current_loc = world.agent_locations.get(agent.name, None)
            if not current_loc:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"  [Sim Warning]: Agent {agent.name} has no location! Skipping turn.")
                print("-" * 60)  # End agent turn block
                continue

            # 1. AGENT THINKING (Plan action)
            if config.SIMULATION_MODE == 'debug':
                print(f"  [Phase 1] {agent.name} Thinking...")
            # Agent plans based on current world state
            intended_output = agent.plan(world)

            # Optional pause
            time.sleep(0.2)

            # 2. ACTION RESOLUTION
            if config.SIMULATION_MODE == 'debug':
                print(f"  [Phase 2] Action Resolution for {agent.name}...")

            if not action_resolver:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"    [Sim Error]: Action resolver not available for {agent.name}. Skipping resolution.")
                print("-" * 60)  # End agent turn block
                continue

            result = action_resolver.resolve(
                agent.name, current_loc, intended_output, world
            )

            # 3. PROCESS RESULT, UPDATE WORLD, DISPATCH EVENT (IMMEDIATELY)
            outcome_desc_for_event = ""

            if result and result.get("success"):
                outcome_desc = result.get(
                    'outcome_description', f"{agent.name} acted.")
                outcome_desc_for_event = outcome_desc  # Use this for the event
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"    [RESOLVER_SUCCESS] Action: {result.get('action_type', 'Unknown')}")
                    print(f"      Outcome: {outcome_desc}")
                if config.SIMULATION_MODE == 'story':
                    # Slightly more spacing for story mode
                    print(f"\n{outcome_desc}\n")

                if result.get("world_state_updates"):
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"Applying world state updates for {agent.name}'s action...")
                    world.apply_state_updates(
                        result["world_state_updates"], triggered_by=agent.name)
                    if config.SIMULATION_MODE == 'debug':
                        print(f"        Updates applied.")
                    if any(upd.get('type') == 'agent_location' and upd.get('agent_name') == agent.name for upd in result["world_state_updates"]):
                        current_loc = world.agent_locations.get(
                            agent.name, current_loc)

            elif result:  # Failed Action
                reason = result.get('reasoning', 'Unknown reason')
                outcome_desc = result.get(
                    'outcome_description', 'Action failed.')
                outcome_desc_for_event = f"{agent.name} attempt to {intended_output.get('action_type','act')} failed: {outcome_desc}"

                if config.SIMULATION_MODE == 'debug':
                    print(f"    [RESOLVER_FAILURE] Reason: {reason}")
                    print(f"      Outcome: {outcome_desc_for_event}")
                if config.SIMULATION_MODE == 'story':
                    # Add a newline before for better separation
                    print(
                        f"\n{agent.name} tried to act, but {outcome_desc.lower()}")

            else:  # Resolver Error
                error_msg = f"System error resolving {agent.name}'s action for intent: {intended_output}."
                outcome_desc_for_event = error_msg
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"    [RESOLVER_ERROR] Critical failure for {agent.name}.")
                    print(f"      Details: {error_msg}")
                if config.SIMULATION_MODE == 'story':
                    # Add a newline before for better separation
                    print(
                        f"\n[System Note] Issue resolving {agent.name}'s action.")

            # 3b. CREATE, LOG, AND DISPATCH EVENT (for success, failure, or error)
            if outcome_desc_for_event:
                event_scope = result.get(
                    'event_scope', 'action_outcome') if result else 'system_error'
                world.log_event(outcome_desc_for_event, event_scope,
                                current_loc, agent.name if result else 'System')
                new_event = Event(
                    description=outcome_desc_for_event,
                    location=current_loc,
                    scope=event_scope,
                    step=world.current_step,
                    triggered_by=agent.name if result else 'System'
                )
                # if config.SIMULATION_MODE == 'debug':
                #     # Truncate long descriptions
                #     print(
                #         f"    [Event Dispatch] For: {new_event.triggered_by}, Desc: \"{new_event.description[:50]}...\"")
                event_dispatcher.dispatch_event(
                    new_event, world.registered_agents, world.agent_locations
                )

            if config.SIMULATION_MODE == 'debug':
                print("-" * 60)  # End agent turn block

            agent_who_took_last_turn_this_step = agent
            time.sleep(0.1)
            
         # Update the tracker for the *next* step's calculation
        if agent_who_took_last_turn_this_step:
            last_agent_acted_in_previous_step = agent_who_took_last_turn_this_step
        elif not agents:  # If there are no agents at all in the simulation
            last_agent_acted_in_previous_step = None
        # If agents exist but no one took a turn (e.g., all skipped),
        # last_agent_acted_in_previous_step retains its value, which is correct.

        # ---------------------------------------- End Step ----------------------------------------
        if config.SIMULATION_MODE == 'debug':
            print(f"\n")  # Add a blank line
            footer_text = f" END OF STEP {step} "
            print(footer_text.center(70, '-'))  # Centered footer with '-' fill
            print("\n--- WORLD STATE (End of Step) ---")
            print(world.get_full_state_string())
            print("--- END OF WORLD STATE ---\n")

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
