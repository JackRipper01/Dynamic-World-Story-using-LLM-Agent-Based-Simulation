# agent.py
# No longer needs direct LLM imports, relies on Planning/Memory modules
from agent.memory import BaseMemory
from agent.planning import BasePlanning
from world import WorldState

class Agent:
    def __init__(self, name:str, personality:str, memory_module:BaseMemory, planning_module:BasePlanning):
        self.name = name
        self.personality = personality
        self.memory = memory_module # An instance of BaseMemory
        self.planning = planning_module # An instance of BasePlanning
        self.action_buffer = None  # Store the output of plan() before resolution
        print(f"Agent {name} initialized with {type(memory_module).__name__} and {type(planning_module).__name__}.")

    def perceive(self, event):
        """Processes a perceived event from the world and stores it in memory."""
        # Simple formatting for now, could be more sophisticated
        perception_text = f"[Perception @ Step {event.step}] ({event.scope} at {event.location or 'Global'} by {event.triggered_by}): {event.description}"
        self.memory.add_observation(perception_text)
        print(f"DEBUG {self.name} Perceived: {perception_text}") # Optional debug

    def plan(self, world_state:WorldState):
        """
        Agent's thinking cycle. Uses memory and planning to decide next action intent.
        Does NOT execute the action, just returns the intended output.
        """
        # 1. Get memory context
        memory_context = self.memory.get_memory_context()

        # 2. Get minimal static world context (if needed by the thinker)
        # Pass only what's necessary, avoid full dynamic state if using event perception
        static_context = world_state.get_static_context_for_agent(self.name)

        # 3. Plan (call the planning module)
        # Pass agent reference (for personality), static context, and memory context
        action_output = self.planning.generate_output(
            self, static_context, memory_context)

        # 4. Store intended action (important!)
        self.action_buffer = action_output
        # Also add own *intended* action to memory for self-reflection
        self.memory.add_observation(
            f"[My Intent @ Step {world_state.current_step}] {action_output}")

        return action_output

    # Note: Memory update for the *result* of the action now happens implicitly
    # when the ActionResolver's outcome event is logged and dispatched back
    # to the agent via perceive().
