# main.py
import time
import google.generativeai as genai


# Import our modules
import config
from world import WorldState
from agent.agent import Agent
from agent.memory import SimpleMemory
from agent.thinking import GeminiThinker 
from interpreter import LLMInterpreter  # Import the LLM interpreter
from director import Director # Import the new Director class


def run_simulation():
    print("--- Starting Modular Free Agent Simulation with Director ---")

    # 1. Initialize LLM Model
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
    world.global_context['weather'] = "Clear" # Initial weather

    # 3. Initialize Agents
    agents = []
    thinker = GeminiThinker(model)
    agent_configs = [
        {"name": "Alice", "personality": config.DEFAULT_PERSONALITIES.get("Alice", "default")},
        {"name": "Bob", "personality": config.DEFAULT_PERSONALITIES.get("Bob", "default")}
    ]
    for agent_conf in agent_configs:
        agent_name = agent_conf["name"]
        memory = SimpleMemory()
        agent = Agent(
            name=agent_name,
            personality=agent_conf["personality"],
            memory_module=memory,
            thinking_module=thinker
        )
        agents.append(agent)
        start_location = "Park"
        world.add_agent(agent_name, start_location)
        world.log_event(f"{agent_name} appears in the {start_location}.", triggered_by="Setup") # Log initial appearance

    # 4. Initialize Director
    director = Director(world, model, config.NARRATIVE_GOAL) # Pass world, model, and goal

    ## 5. Initialize Interpreter
    interpreter = LLMInterpreter(model, world)
    
    # --- Simulation Steps ---
    step = 0
    while step < config.SIMULATION_MAX_STEPS:
        step += 1
        world.advance_step() # Increment world step counter
        print(f"\n{'='*15} Simulation Step {step}/{config.SIMULATION_MAX_STEPS} {'='*15}")
        print(world.get_full_state_string())

        # --- Agent Phase ---
        agent_actions = {} # agent_name -> utterance
        agent_current_locations = {} # Store locations for interpreter
        for agent in agents:
            print(f"\n--- Processing {agent.name} ---")
            # Get agent's location BEFORE they act (in case they move)
            current_loc = world.agent_locations.get(agent.name, None)
            if not current_loc:
                print(f"[Sim Warning]: Agent {agent.name} has no location! Skipping.")
                continue
            agent_current_locations[agent.name] = current_loc

            utterance = agent.step(world) # Agent perceives (filtered), thinks, updates memory
            agent_actions[agent.name] = utterance
            time.sleep(1.5)

        # --- Interpretation Phase ---
        print("\n--- Resolving Agent Actions via LLM Interpreter ---")
        for agent_name, utterance in agent_actions.items():
            agent_loc = agent_current_locations.get(agent_name)
            if agent_loc:
                # Call the new LLM-based resolver
                resolution_result = interpreter.interpret_and_resolve_action(
                    agent_name, agent_loc, utterance
                )
                if resolution_result:
                    # Log the interpreter's reasoning/decision for debugging?
                    print(f"[Resolver Result for {agent_name}]: Type={resolution_result.get('action_type')}, Success={resolution_result.get('success')}, Reason={resolution_result.get('reasoning', 'N/A')}")
                else:
                    print(f"[Resolver Result for {agent_name}]: Failed to resolve action.")
            else:
                print(f"[Sim Warning]: Cannot resolve action for {agent_name}, location unknown.")
            time.sleep(0.5) # Optional pause

        # --- Director Phase --- 
        director.step() # Let the director observe, think, and act
        time.sleep(1.0) # Optional pause after director

        # --- Manual Control / End Step ---
        
        print("\n--- End of Step ---")
        print(world.get_full_state_string()) # Show final state for the step

        # Manual stepping and limited override
        user_input = input("Enter for next step, 'goal <new goal>' to change director goal, 'q' to quit: ").lower().strip()

        if user_input == 'q':
            print("Quitting simulation by user request.")
            break
        elif user_input.startswith('goal '):
            new_goal = user_input[len('goal '):].strip()
            if new_goal:
                print(f"Updating Director goal to: '{new_goal}'")
                director.narrative_goal = new_goal
                world.log_event(f"COMMAND: Director narrative goal updated to '{new_goal}'.", triggered_by="User")
            else:
                print("Invalid command. Use 'goal <description>'.")
        elif user_input.startswith('w '): # Keep manual weather override? Optional.
             new_weather = user_input[len('w '):].strip().title()
             if new_weather:
                 print(f"Manual weather override to: {new_weather}")
                 world.set_weather(new_weather, triggered_by="User")
             else:
                 print("Invalid command. Use 'w <condition>'.")
        elif user_input:
            print(f"Unknown command: '{user_input}'")
        # Pressing Enter continues

    print(f"\n--- Simulation Ended after {step} steps ---")

# --- Run ---
if __name__ == "__main__":
    run_simulation()
