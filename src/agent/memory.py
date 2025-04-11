# memory.py
import config
from abc import ABC, abstractmethod # For defining abstract base class

class BaseMemory(ABC):
    """Abstract base class for agent memory modules."""
    @abstractmethod
    def add_observation(self, observation_text):
        """Adds a piece of information (perception, action result, thought) to memory."""
        pass

    @abstractmethod
    def get_memory_context(self):
        """Returns a string summary of relevant memories for the LLM prompt."""
        pass

    @abstractmethod
    def clear(self):
        """Clears the memory."""
        pass

class SimpleMemory(BaseMemory):
    """A basic rolling string buffer memory."""
    def __init__(self, max_length=config.MAX_MEMORY_TOKENS):
        self.memory_buffer = ""
        self.max_length = max_length # Approximate character length

    def add_observation(self, observation_text):
        # Add new observation, ensuring separation
        new_entry = observation_text.strip()
        if self.memory_buffer:
            self.memory_buffer = f"{self.memory_buffer}\n{new_entry}"
        else:
            self.memory_buffer = new_entry

        # Trim if exceeds max length (simple truncation from the beginning)
        if len(self.memory_buffer) > self.max_length:
            excess = len(self.memory_buffer) - self.max_length
            # Try to cut off at a newline to keep entries somewhat intact
            first_newline = self.memory_buffer.find('\n', excess)
            if first_newline != -1:
                 self.memory_buffer = self.memory_buffer[first_newline+1:]
            else: # If no newline found after excess, just truncate
                 self.memory_buffer = self.memory_buffer[excess:]
        # print(f"DEBUG Memory Add: Added '{new_entry[:50]}...'. Buffer size: {len(self.memory_buffer)}") # Debug

    def get_memory_context(self):
        if not self.memory_buffer:
            return "No specific memories recalled."
        # Provide the most recent memories
        return f"Recollections (most recent last):\n{self.memory_buffer}"

    def clear(self):
        self.memory_buffer = ""

# Example of how you might add another memory type later:
# class VectorMemory(BaseMemory):
#     def __init__(self, embedding_model, vector_db):
#         # ... implementation using embeddings ...
#         pass
#     def add_observation(self, observation_text):
#         # ... embed and store ...
#         pass
#     def get_memory_context(self, query_text):
#         # ... retrieve relevant memories based on query ...
#         pass
#     def clear(self):
#         # ... clear db ...
#         pass