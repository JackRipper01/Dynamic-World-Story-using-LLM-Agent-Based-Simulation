# main.py
from collections import namedtuple
import time
from typing import List
import google.generativeai as genai

# Import our modules
import config

from world import WorldState
from agent.agent import Agent
from director import Director 

Event = namedtuple(
    "Event", ["description", "location", "scope", "step", "triggered_by"])

def get_memory_module(memory_type):
    if memory_type == "SimpleMemory":
        from agent.memory import SimpleMemory
        return SimpleMemory()
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

def run_simulation():
    print("--- Starting Agent Simulation with Director ---")
    print(f"Config: Memory={config.AGENT_MEMORY_TYPE}, Thinker={config.AGENT_PLANNING_TYPE}, Resolver={config.ACTION_RESOLVER_TYPE}, Perception={config.EVENT_PERCEPTION_MODEL}")
    
    # 1. Initialize LLM Model
    print(f"Configuring Gemini model: {config.MODEL_NAME}")
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=config.MODEL_NAME,
        generation_config=config.GENERATION_CONFIG,
        # safety_settings=config.SAFETY_SETTINGS
    )
    print("Model configured.")

    # 2. Initialize World State and Event Dispatcher
    event_dispatcher= get_event_dispatcher(config.EVENT_PERCEPTION_MODEL)
    world = WorldState(locations=config.KNOWN_LOCATIONS)
    world.global_context['weather'] = "Clear" # Initial weather

    # 3. Initialize Agents
    agents: List[Agent] = []
    
    for agent_conf in config.agent_configs:
        agent_name = agent_conf["name"]
        memory = get_memory_module(config.AGENT_MEMORY_TYPE)
        thinker = get_planning_module(config.AGENT_PLANNING_TYPE, model)
        agent = Agent(
            name=agent_name,
            gender=agent_conf["gender"],
            personality=agent_conf["personality"],
            initial_goals=agent_conf["initial_goals"],
            memory_module=memory,
            planning_module=thinker
        )
        agents.append(agent)
        start_location = agent_conf["initial_location"]
        world.add_agent_to_location(
            agent_name, start_location, triggered_by="Setup")
        world.register_agent(agent)

    # 4. Initialize Director (remains mostly the same, observes world state)
    director_model = model  
    director = Director(world, director_model, config.NARRATIVE_GOAL)

    ## 5. Initialize Action Resolver
    action_resolver = get_action_resolver(
        config.ACTION_RESOLVER_TYPE, model, world_ref=world)
    
    # --- Simulation Steps ---------------------------------------------------------------------------------------------
    step = 0
    while step < config.SIMULATION_MAX_STEPS:
        step += 1
        world.advance_step() # Increment world step counter
        print(f"\n{'='*15} Simulation Step {step}/{config.SIMULATION_MAX_STEPS} {'='*15}")
        print(world.get_full_state_string())

        # --- Director Phase -------------------------------------------------------------------------------------------
        # director.step()  # Let the director observe, think, and act
        # time.sleep(1.0)  # Optional pause after director
        
        
        # --- Agent Thinking Phase --------------------------------------------------------------------------------------
        # Agents decide their *intended* actions based on perceived events & memory
        agent_intentions = {}  # agent_name -> intended_action_output
        agent_current_locations = {}  # Store locations for resolver
        for agent in agents:
            print(f"\n--- Processing {agent.name} ---")
            # Get agent's location BEFORE they act (in case they move)
            current_loc = world.agent_locations.get(agent.name, None)
            if not current_loc:
                print(f"[Sim Warning]: Agent {agent.name} has no location! Skipping.")
                continue
            agent_current_locations[agent.name] = current_loc

            # Agent plan based on memory (inc. perceptions) and static context
            # Agent updates own memory with intent
            intended_output = agent.plan(world)
            agent_intentions[agent.name] = intended_output
            time.sleep(1.0)  # LLM rate limiting/pause


        # --- Action Resolution Phase --------------------------------------------------------------------------------
        # The Action Resolver interprets intentions and determines outcomes
        print("\n--- Action Resolution Phase ---")
        resolution_results = {}  # agent_name -> resolution_dict
        all_state_updates = []  # Collect updates from all agents first
        all_outcome_events = []  # Collect outcome events
        
        for agent_name, intent in agent_intentions.items():
            agent_loc = agent_current_locations.get(agent_name)
            if agent_loc and action_resolver:
                print(f"-- Resolving for {agent_name} at {agent_loc} --")
                result = action_resolver.resolve(
                    agent_name, agent_loc, intent, world
                )
                resolution_results[agent_name] = result
                if result and result.get("success"):
                    print(
                        f"[Resolver OK] {agent_name}: {result.get('action_type')} -> {result.get('outcome_description')}")
                    if result.get("world_state_updates"):
                        all_state_updates.extend(result["world_state_updates"])
                    # Create the event tuple for logging *after* state updates
                    all_outcome_events.append(
                        (result['outcome_description'],
                        'action_outcome', agent_loc, agent_name)
                    )
                elif result:  # Handled failure case
                    print(
                        f"[Resolver FAIL] {agent_name}: {result.get('reasoning', 'Unknown reason')}")
                    # Log the failure outcome event
                    all_outcome_events.append(
                        (result['outcome_description'],
                        'action_outcome', agent_loc, agent_name)
                    )
                else:  # Severe failure in resolver itself
                    print(
                        f"[Resolver ERROR] Critical failure resolving for {agent_name}")
                    # Log a generic system failure event?
                    all_outcome_events.append(
                        (f"System error resolving {agent_name}'s action.",
                        'system_error', agent_loc, 'System')
                    )
            else:
                print(
                    f"[Sim Warning]: Cannot resolve action for {agent_name}, location or resolver unknown.")
            time.sleep(0.5)

        
        # --- World Update Phase --------------------------------------------------------------------------------------
        # Apply all accumulated state changes atomically (conceptually)
        print("\n--- World Update Phase ---")
        if all_state_updates:
            world.apply_state_updates(
                all_state_updates, triggered_by="AgentActions")
        else:
            print("No world state updates required.")

        
        # --- Agents Perceiving and Event Logging Phase -------------------------------------------------------------------
        #Agents perceive changes in world and action of other agents or ambient events by dispatching the new event to them
        
        # Log all outcome events AFTER state updates are done and dispatch events to agent
        print("\n--- Logging Action Outcomes ---")
        for desc, scope, loc, trig_by in all_outcome_events:
            world.log_event(desc, scope, loc, trig_by)
            
            # This will dispatch perceptions
            new_event= Event(desc,scope,loc,world.current_step,trig_by)
            event_dispatcher.dispatch_event(new_event,world.registered_agents,world.agent_locations)
            
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
