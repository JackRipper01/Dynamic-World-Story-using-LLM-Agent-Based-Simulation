# agent.py
# No longer needs direct LLM imports, relies on Thinker/Memory modules

class Agent:
    def __init__(self, name, personality, memory_module, thinking_module):
        self.name = name
        self.personality = personality
        self.memory = memory_module # An instance of BaseMemory
        self.thinker = thinking_module # An instance of BaseThinker
        self.last_utterance = "None" # Store the last decided utterance
        print(f"Agent {name} initialized with {type(memory_module).__name__} and {type(thinking_module).__name__}.")

    def step(self, world_state):
        """Performs one step of the agent's cycle: perceive, think, decide."""
        # 1. Get memory context
        memory_context = self.memory.get_memory_context()

        # 2. Think (call the thinking module)
        # The thinker module gets world context via world_state.get_context_for_agent
        utterance = self.thinker.generate_utterance(self, world_state, memory_context)
        self.last_utterance = utterance

        # 3. Update own memory AFTER thinking/acting
        # Include both the world perception and the action taken
        # World perception is implicitly handled by the thinker via get_context_for_agent
        self.memory.add_observation(f"My action/thought: {utterance}")

        return utterance