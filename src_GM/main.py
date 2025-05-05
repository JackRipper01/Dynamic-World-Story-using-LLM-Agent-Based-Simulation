from collections import namedtuple
import time
from typing import List
import google.generativeai as genai
import argparse

import config  # Import the whole config module

from world import WorldState
from agent.agent import Agent
from director import Director


Event = namedtuple(
    "Event", ["description", "location", "scope", "step", "triggered_by"])


def get_memory_module(agent, memory_type):
    if memory_type == "SimpleMemory":
        from agent.memory import SimpleMemory
        return SimpleMemory()
    if memory_type == "ShortLongTMemory":
        from agent.memory import ShortLongTMemory
        return ShortLongTMemory(agent, reflection_threshold=10)
    else:
        raise ValueError(f"Unknown memory type: {memory_type}")


def get_planning_module(planning_type, model):
    if planning_type == "GeminiThinker":
        from agent.planning import SimplePlanning
        return SimplePlanning(model)

    else:
        raise ValueError(f"Unknown thinker type: {planning_type}")


def get_action_resolver(resolver_type, model, world_ref=None):
    if resolver_type == "LLMResolver":
        from action_resolver import LLMActionResolver
        return LLMActionResolver(model, world_ref)

    else:
        raise ValueError(f"Unknown action resolver type: {resolver_type}")


def get_event_dispatcher(dispatcher_type: str):
    if dispatcher_type == "DirectEventDispatcher":
        from event_dispatcher import DirectEventDispatcher
        return DirectEventDispatcher()
    else:
        raise ValueError(f"Unknown event dispatcher type: {dispatcher_type}")

# --- Main Simulation Function (Modified) ---


def run_simulation():
    """Runs the simulation with controlled output based on config.SIMULATION_MODE."""

    # Mode is now globally accessible via config.SIMULATION_MODE
    # Example usage: if config.SIMULATION_MODE == 'debug': print(...)

    if config.SIMULATION_MODE == 'debug':
        print("--- Starting Agent Simulation with Director (DEBUG MODE) ---")
        print(f"Config: Memory={config.AGENT_MEMORY_TYPE}, Thinker={config.AGENT_PLANNING_TYPE}, Resolver={config.ACTION_RESOLVER_TYPE}, Perception={config.EVENT_PERCEPTION_MODEL}")
    elif config.SIMULATION_MODE == 'story':
        print("--- Starting Agent Simulation ---")

    # 1. Initialize LLM Model
    if config.SIMULATION_MODE == 'debug':
        print(f"Configuring Gemini model: {config.MODEL_NAME}")
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=config.MODEL_NAME,
        generation_config=config.GENERATION_CONFIG,
    )
    if config.SIMULATION_MODE == 'debug':
        print("Model configured.")

    # 2. Initialize World State and Event Dispatcher
    event_dispatcher = get_event_dispatcher(config.EVENT_PERCEPTION_MODEL)
    world = WorldState(locations=config.KNOWN_LOCATIONS)
    world.global_context['weather'] = "Clear"
    if config.SIMULATION_MODE == 'debug':
        print("World state and event dispatcher initialized.")

    # 3. Initialize Agents
    agents: List[Agent] = []
    if config.SIMULATION_MODE == 'debug':
        print("Initializing agents...")
    for agent_conf in config.agent_configs:
        agent_name = agent_conf["name"]
        thinker = get_planning_module(config.AGENT_PLANNING_TYPE, model)
        agent = Agent(
            name=agent_name,
            gender=agent_conf["gender"],
            personality=agent_conf["personality"],
            initial_goals=agent_conf["initial_goals"],
            memory_module=None,
            planning_module=thinker
        )
        # Memory initialization might print DEBUG lines, needs fixing in memory module
        agent.memory = get_memory_module(agent, config.AGENT_MEMORY_TYPE)

        agents.append(agent)
        start_location = agent_conf["initial_location"]
        # world.add_agent_to_location might print, needs fixing in world module
        world.add_agent_to_location(
            agent_name, start_location, triggered_by="Setup")
        # world.register_agent might print, needs fixing in world module
        world.register_agent(agent)
        if config.SIMULATION_MODE == 'debug':
            print(f"- Agent '{agent_name}' created at '{start_location}'.")

    if config.SIMULATION_MODE == 'debug':
        print("Agents initialized.")

    # 4. Initialize Director
    director_model = model
    director = Director(world, director_model, config.NARRATIVE_GOAL)
    if config.SIMULATION_MODE == 'debug':
        # Show goal in debug
        print(f"Director initialized with goal: '{config.NARRATIVE_GOAL}'")

    # 5. Initialize Action Resolver
    action_resolver = get_action_resolver(
        config.ACTION_RESOLVER_TYPE, model, world_ref=world)
    if config.SIMULATION_MODE == 'debug':
        print("Action resolver initialized.")

    # --- Simulation Steps ---
    step = 0
    while step < config.SIMULATION_MAX_STEPS:
        step += 1
        world.advance_step()

        if config.SIMULATION_MODE == 'debug':
            print(
                f"\n{'='*15} Simulation Step {step}/{config.SIMULATION_MAX_STEPS} {'='*15}")
            print(world.get_full_state_string())
        elif config.SIMULATION_MODE == 'story':
            print(f"\n--- TIME STEP {step} ---")

        # --- Agent Thinking Phase ---
        if config.SIMULATION_MODE == 'debug':
            print("\n--- Agent Thinking Phase ---")
        agent_intentions = {}
        agent_current_locations = {}
        for agent in agents:
            # Agent prints like "[Thinking...]" need to be fixed in agent.py
            if config.SIMULATION_MODE == 'debug':
                print(f"\n-- Processing {agent.name} --")
            current_loc = world.agent_locations.get(agent.name, None)
            if not current_loc:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"[Sim Warning]: Agent {agent.name} has no location! Skipping.")
                continue
            agent_current_locations[agent.name] = current_loc

            # agent.plan() might print things like "[Intends...]", needs fixing in agent.py
            intended_output = agent.plan(world)
            agent_intentions[agent.name] = intended_output
            # No print here, intent is shown via resolver output or not at all in story mode

            time.sleep(1.0)

        # --- Action Resolution Phase ---
        if config.SIMULATION_MODE == 'debug':
            print("\n--- Action Resolution Phase ---")
            
        # The Action Resolver interprets intentions and determines outcomes
        resolution_results = {}  # agent_name -> resolution_dict
        all_state_updates = []  # Collect updates from all agents first
        all_outcome_events = []  # Collect outcome events

        for agent_name, intent in agent_intentions.items():
            agent_loc = agent_current_locations.get(agent_name)
            if agent_loc and action_resolver:
                # action_resolver.resolve() might print "[LLM Resolver...]", needs fixing in action_resolver.py
                if config.SIMULATION_MODE == 'debug':
                    print(f"-- Resolving for {agent_name} at {agent_loc} --")
                result = action_resolver.resolve(
                    agent_name, agent_loc, intent, world
                )
                resolution_results[agent_name] = result
                if result and result.get("success"):
                    outcome_desc = result.get('outcome_description')
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"[Resolver OK] {agent_name}: {result.get('action_type')} -> {outcome_desc}")
                    if config.SIMULATION_MODE == 'story':  # <<< KEY STORY OUTPUT
                        print(f"{outcome_desc}\n\n")

                    if result.get("world_state_updates"):
                        all_state_updates.extend(result["world_state_updates"])
                    all_outcome_events.append(
                        (outcome_desc, 'action_outcome', agent_loc, agent_name)
                    )
                elif result:
                    reason = result.get('reasoning', 'Unknown reason')
                    outcome_desc = result.get(
                        'outcome_description', 'Action failed.')
                    if config.SIMULATION_MODE == 'debug':
                        print(f"[Resolver FAIL] {agent_name}: {reason}")
                        # Show failed outcome desc in debug too
                        print(f"            Outcome: {outcome_desc}")
                    # <<< KEY STORY OUTPUT (Failure)
                    if config.SIMULATION_MODE == 'story':
                        # Make failure less technical for story
                        print(
                            f"{agent_name} tried to act, but {outcome_desc.lower()}")

                    all_outcome_events.append(
                        (outcome_desc, 'action_outcome', agent_loc, agent_name)
                    )
                else:
                    error_msg = f"System error resolving {agent_name}'s action."
                    if config.SIMULATION_MODE == 'debug':
                        print(
                            f"[Resolver ERROR] Critical failure resolving for {agent_name}")
                    if config.SIMULATION_MODE == 'story':
                        print(
                            f"[System Note] Issue resolving {agent_name}'s action.")
                    all_outcome_events.append(
                        (error_msg, 'system_error', agent_loc, 'System')
                    )
            else:
                if config.SIMULATION_MODE == 'debug':
                    print(
                        f"[Sim Warning]: Cannot resolve action for {agent_name}, location or resolver unknown.")
            time.sleep(0.5)

        # --- World Update Phase ---
        if config.SIMULATION_MODE == 'debug':
            print("\n--- World Update Phase ---")
        if all_state_updates:
            # world.apply_state_updates might print, needs fixing in world.py
            world.apply_state_updates(
                all_state_updates, triggered_by="AgentActions")
            if config.SIMULATION_MODE == 'debug':
                print("Applied world state updates.")
        else:
            if config.SIMULATION_MODE == 'debug':
                print("No world state updates required.")

        # --- Agents Perceiving and Event Logging Phase ---
        
        # Agents perceive changes in world and action of other agents or ambient events by dispatching the new event to them
        if config.SIMULATION_MODE == 'debug':
            print("\n--- Logging Action Outcomes & Dispatching Events ---")
        for desc, scope, loc, trig_by in all_outcome_events:
            # world.log_event might print "[Event Log...]", needs fixing in world.py
            world.log_event(desc, scope, loc, trig_by)
            # Event logging itself shouldn't print to console unless debugging world state

            # Dispatcher might print "[Dispatcher...]", needs fixing in event_dispatcher.py
            # Agent perception might print "DEBUG ... Perceived", needs fixing in agent/memory
            # Corrected order based on Event definition
            new_event = Event(desc, loc, scope, world.current_step, trig_by)
            event_dispatcher.dispatch_event(
                new_event, world.registered_agents, world.agent_locations)
            # No prints needed here for story mode. Debug prints should be inside the called methods.

        # --- End Step ---
        if config.SIMULATION_MODE == 'debug':
            print("\n--- End of Step ---")
            print(world.get_full_state_string())

        # --- User Input --- (Keep for both modes)
        user_input = input(
            "Enter for next step, 'goal <new goal>' to change director goal, 'q' to quit: ").lower().strip()

        if user_input == 'q':
            print("Quitting simulation by user request.")
            break
        # ... (rest of user input handling remains the same, prints are fine for both modes) ...
        elif user_input.startswith('goal '):
            new_goal = user_input[len('goal '):].strip()
            if new_goal:
                print(f"Updating Director goal to: '{new_goal}'")
                director.narrative_goal = new_goal
                # Log event internally, but maybe don't print confirmation here unless debug?
                world.log_event(
                    f"COMMAND: Director narrative goal updated to '{new_goal}'.", "global", "world", "User")
            else:
                print("Invalid command. Use 'goal <description>'.")
        elif user_input.startswith('w '):
            new_weather = user_input[len('w '):].strip().title()
            if new_weather:
                print(f"Manual weather override to: {new_weather}")
                world.set_weather(new_weather, triggered_by="User")
            else:
                print("Invalid command. Use 'w <condition>'.")
        elif user_input:
            print(f"Unknown command: '{user_input}'")

    print(f"\n--- Simulation Ended after {step} steps ---")


# --- Run ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Agent Simulation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--debug', action='store_true',
                    help='Enable detailed debug logging.')
    group.add_argument('--story', action='store_true',
                    help='Enable narrative story logging.')
    args = parser.parse_args()

    # Set the global simulation mode in the config module
    config.SIMULATION_MODE = 'debug' if args.debug else 'story'

    # Run the simulation (it will now read the mode from config)
    run_simulation()
