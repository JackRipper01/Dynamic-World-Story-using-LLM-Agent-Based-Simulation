# agent.py
from agent.memory import BaseMemory
from agent.planning import BasePlanning
# from world import WorldState
import config
class Agent:
    def __init__(self, name:str,gender:str, personality:str,identity:str,initial_context:str, memory_module:BaseMemory, planning_module:BasePlanning, initial_goals: list[str] = None,background:list[str] = None):
        self.name = name
        self.gender = gender
        self.personality = personality
        self.memory = memory_module # An instance of BaseMemory
        self.planning = planning_module # An instance of BasePlanning
        self.goals = initial_goals if initial_goals is not None else [] # List of goal descriptions
        self.background = background if background is not None else []  # Placeholder for agent's background
        self.identity = identity 
        self.initial_context = initial_context
        self.action_buffer = None  # Store the output of plan() before resolution
        print(f"Agent {name} initialized with {type(memory_module).__name__} and {type(planning_module).__name__}.")

    def perceive(self, event):
        """Processes a perceived event from the world and stores it in memory."""
        # Simple formatting for now, could be more sophisticated
        perception_text = f"You just perceived in step {event.step} of the simulation the following event at {event.location}{f' by {event.triggered_by}' if event.triggered_by else ''}: {event.description}"
        self.memory.add_observation(perception_text)
        # if config.SIMULATION_MODE == 'debug': -------------------------------------------------> temporally disabled
        #     print(f"DEBUG {self.name} Perceived: {perception_text}") # Optional debug

    def add_goal(self, goal_description: str):
        """Adds a new goal to the agent's list."""
        if goal_description not in self.goals:
            self.goals.append(goal_description)
            if config.SIMULATION_MODE == 'debug':
                print(f"DEBUG {self.name} added goal: {goal_description}")
            # Optionally, add this event to memory
            self.memory.add_observation(f"[Internal] Added new goal: {goal_description}")

    def plan(self, world_state):
        """
        Agent's thinking cycle. Uses memory, goals, and planning to decide next action intent.
        Does NOT execute the action, just returns the intended output.
        """
        # 1. Get memory context
        memory_context = self.memory.get_memory_context()

        # 2. Get minimal static world context (if needed by the thinker)
        static_context = world_state.get_static_context_for_agent(self.name)

        # 3. Plan (call the planning module)
        # Pass agent reference (for personality/goals), static context, and memory context
        action_output = self.planning.generate_output(
            self, static_context, memory_context)

        # 4. Store intended action (important!)
        self.action_buffer = action_output
        # Also add own *intended* action to memory for self-reflection
        observation = f"You {self.name} intended in step {world_state.current_step} of the simulation the following action at {world_state.agent_locations[self.name]}: {action_output}"
        self.memory.add_observation(
            observation_text=observation)

        return action_output

    # Note: Memory update for the *result* of the action now happens implicitly
    # when the ActionResolver's outcome event is logged and dispatched back
    # to the agent via perceive().
