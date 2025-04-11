# main.py
import time
import google.generativeai as genai

# Import our modules
import config
from world import WorldState
from agent.agent import Agent
from agent.memory import SimpleMemory # Import the specific memory type
from agent.thinking import GeminiThinker # Import the specific thinker type
from interpreter import interpret_and_update

def run_simulation():
    print("--- Starting Modular Free Agent Simulation ---")

    # 1. Initialize LLM Model (using config)
    print(f"Configuring Gemini model: {config.MODEL_NAME}")
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=config.MODEL_NAME,
        generation_config=config.GENERATION_CONFIG,
        safety_settings=config.SAFETY_SETTINGS
    )
    print("Model configured.")

    # 2. Initialize World State
    world = WorldState(locations=config.KNOWN_LOCATIONS)
    world.global_context['weather'] = "Misty" # Initial weather

    # 3. Initialize Agents (using components)
    agents = []
    thinker = GeminiThinker(model) # Create one thinker instance (can be shared)

    agent_configs = [
        {"name": "Alice", "personality": config.DEFAULT_PERSONALITIES.get("Alice", "default")},
        {"name": "Bob", "personality": config.DEFAULT_PERSONALITIES.get("Bob", "default")}
    ]

    for agent_conf in agent_configs:
        agent_name = agent_conf["name"]
        memory = SimpleMemory() # Each agent gets its own memory instance
        agent = Agent(
            name=agent_name,
            personality=agent_conf["personality"],
            memory_module=memory,
            thinking_module=thinker
        )
        agents.append(agent)
        # Add agent to world (define starting location)
        start_location = "Park" # Or randomize / load from config
        world.add_agent(agent_name, start_location)
        world.log_event(f"{agent_name} appears in the {start_location}.") # Log initial appearance


    # --- Simulation Steps ---
    step = 0
    while step < config.SIMULATION_MAX_STEPS:
        step += 1
        print(f"\n{'='*15} Simulation Step {step}/{config.SIMULATION_MAX_STEPS} {'='*15}")
        print(world.get_full_state_string()) # Show world state at start

        # --- Agent Phase ---
        agent_actions = {} # Store agent name -> utterance
        for agent in agents:
            print(f"\n--- Processing {agent.name} ---")
            utterance = agent.step(world) # Agent perceives, thinks, updates memory
            agent_actions[agent.name] = utterance
            time.sleep(1.5) # Pause for readability

        # --- Interpretation and Update Phase ---
        print("\n--- Interpreting Actions & Updating World ---")
        for agent_name, utterance in agent_actions.items():
             interpretation_result = interpret_and_update(agent_name, utterance, world)
             print(f"[Interpreter Result for {agent_name}]: {interpretation_result}")
             # Update agent's memory with the interpretation result? Optional.
             # agent_object = next((a for a in agents if a.name == agent_name), None)
             # if agent_object:
             #    agent_object.memory.add_observation(f"World interpretation: {interpretation_result}")
             time.sleep(0.5) # Small delay between interpretations

        # --- Manual Control / End Step ---
        print("\n--- End of Step ---")
        print(world.get_full_state_string()) # Show world state after updates

        # Manual stepping and control
        user_input = input("Enter for next step, 'w <condition>' (e.g. w Sunny) to change weather, 'q' to quit: ").lower().strip()

        if user_input == 'q':
            print("Quitting simulation by user request.")
            break
        elif user_input.startswith('w '):
            new_weather = user_input[2:].strip().title()
            if new_weather:
                old_weather = world.global_context['weather']
                world.global_context['weather'] = new_weather
                world.log_event(f"COMMAND: The weather suddenly changes from {old_weather} to {new_weather}.")
            else:
                print("Invalid command. Use 'w <condition>', e.g., 'w Rainy'.")
        elif user_input: # Any other non-empty input could be a command later
             print(f"Unknown command: '{user_input}'")
        # Pressing Enter continues the loop

    print(f"\n--- Simulation Ended after {step} steps ---")

# --- Run ---
if __name__ == "__main__":
    run_simulation()