# memory.py
import config
import google.generativeai as genai  # Add this import
from abc import ABC, abstractmethod 
from typing import TYPE_CHECKING, Optional, List, Dict, Any
if TYPE_CHECKING:
   from agent import Agent 

# --- Base Memory Class ---
class BaseMemory(ABC):
    """Abstract base class for agent memory modules."""
    def __init__(self, agent: 'Agent'):
        """Initializes the memory module, linking it to its agent."""
        self.agent = agent # Store the agent reference

    @abstractmethod
    def add_observation(self, observation_text: str, step: Optional[int] = None, type: str = "Generic"):
        """Adds a piece of information to memory.

        Args:
            observation_text: The core text of the memory.
            step: The simulation step number when the observation occurred (optional).
            type: The type of memory (e.g., "Perception", "Intent", "Dialogue", "Reflection").
        """
        pass

    @abstractmethod
    def get_memory_context(self, **kwargs) -> str:
        """Returns a string summary of relevant memories for the LLM prompt.
           Accepts optional keyword arguments for more specific retrieval if implemented.
        """
        pass

    @abstractmethod
    def clear(self):
        """Clears the memory."""
        pass

class SimpleMemory(BaseMemory):
    """A basic rolling string buffer memory."""
    def __init__(self, agent: 'Agent', max_length: int = config.MAX_MEMORY_TOKENS):
        """Initializes SimpleMemory."""
        super().__init__(agent) 
        self.memory_buffer = ""
        self.max_length = max_length # Approximate character length

    def add_observation(self, observation_text: str, step: Optional[int] = None, type: str = "Generic"):
        """Adds observation text to the buffer, prepending type/step if available."""
        # Format the entry with available metadata
        prefix = f"[T:{type}" + (f" S:{step}" if step is not None else "") + "] "
        new_entry = prefix + observation_text.strip()
        
        # Add new observation, ensuring separation
        # Don't overwrite new_entry here
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
        if config.SIMULATION_MODE == 'debug':
            print(f"DEBUG Memory Add: Added '{new_entry[:50]}...'. Buffer size: {len(self.memory_buffer)}") # Debug

    def get_memory_context(self, **kwargs) -> str:
        """Returns the entire (potentially trimmed) memory buffer."""
        if not self.memory_buffer:
            return "No specific memories recalled."
        return f"Recollections (most recent last):\n{self.memory_buffer}"

    def clear(self):
        self.memory_buffer = ""

# --- Short-Long Term Memory with Reflection ---
class ShortLongTMemory(BaseMemory):
    """Memory storing recent events (short-term) and LLM-generated
       reflections/summaries (long-term). Does NOT use embeddings."""
    def __init__(self, agent: 'Agent', reflection_threshold: int = 5):
        """
        Initializes ShortLongTermMemory.

        Args:
            agent: The agent this memory belongs to.
            reflection_threshold: Number of new short-term memories needed to trigger a reflection.
        """
        super().__init__(agent)
        self.short_term_memory: List[Dict[str, Any]] = [] # Stores {'step': int, 'type': str, 'text': str}
        self.long_term_memory: List[str] = [] # Stores reflection strings
        self.reflection_threshold = reflection_threshold
        self.unreflected_count = 0 # Counter for triggering reflection

        # Configure and instantiate the reflection model
        self.reflection_model = None  # Initialize to None
        try:
            # Configure and instantiate a dedicated model 
            generation_config = {
                    "temperature": 0.7, # Slightly less random for reflections
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 256 # Limit reflection length if needed
                }
            
            # Fix the variable name from reflection_mode to reflection_model
            self.reflection_model = genai.GenerativeModel(
                model_name=config.MODEL_NAME, # Or a specific model if desired
                generation_config=generation_config,
            )
            print(f"DEBUG {self.agent.name}: Reflection model '{config.MODEL_NAME}' initialized for ShortLongTermMemory.")
        except Exception as e:
            print(f"ERROR {self.agent.name}: Failed to initialize reflection model '{config.MODEL_NAME}': {e}. Reflections will be disabled.")
        

    def add_observation(self, observation_text: str, step: Optional[int] = None, type: str = "Generic"):
        """Adds observation to short-term memory and triggers reflection if threshold is met."""
        memory_entry = {
            "step": step,
            "type": type,
            "text": observation_text.strip()
        }
        self.short_term_memory.append(memory_entry)
        self.unreflected_count += 1
        # print(f"DEBUG {self.agent.name} Memory Add ShortTerm: Added '{memory_entry['text'][:50]}...'. Unreflected: {self.unreflected_count}")

        # --- Trigger Reflection ---
        if self.reflection_model and self.unreflected_count >= self.reflection_threshold:
            self._reflect()
            self.unreflected_count = 0 # Reset counter after reflection

    def _reflect(self):
        """Generates and stores a long-term reflection based on recent short-term memories."""
        if not self.reflection_model:
            print(f"DEBUG {self.agent.name}: Skipping reflection, model not available.")
            return
        if len(self.short_term_memory) < self.reflection_threshold:
            # Should not happen if called correctly, but safety check
            return

        # Get the most recent memories that haven't been reflected upon yet
        # For simplicity, we take the last 'reflection_threshold' entries.
        # A more robust way might track indices, but this works for now.
        memories_to_reflect = self.short_term_memory[-self.reflection_threshold:]

        # --- Prepare Prompt for Reflection LLM ---
        # Basic agent context
        prompt_context = f"Agent Name: {self.agent.name}\n"
        prompt_context += f"Goals: {self.agent.goals}\n"
        prompt_context += f"Personality: {self.agent.personality}\n\n"
        prompt_context += "Recent events and thoughts:\n"

        # Format the memories for the prompt
        for mem in memories_to_reflect:
            prefix = f"[T:{mem['type']}" + (f" S:{mem['step']}" if mem['step'] is not None else "") + "]"
            prompt_context += f"{prefix} {mem['text']}\n"

        # Reflection Instruction
        prompt_instruction = (
            "\nBased on the agent's personality and the recent events listed above, "
            "what are 1-3 high-level insights, conclusions, important observations, "
            "or summaries about the current situation, relationships, or goals? "
            "Focus on significance and synthesis, not just listing the events. Be concise."
        )

        full_prompt = prompt_context + prompt_instruction
        if config.SIMULATION_MODE == 'debug':
            print(f"DEBUG {self.agent.name}: Generating reflection...")
            print(f"--- Reflection Prompt ---\n{full_prompt}\n-----------------------") # Uncomment for deep debug

        # --- Call LLM for Reflection ---
        try:
            response = self.reflection_model.generate_content(full_prompt)
            reflection_text = response.text.strip()

            if reflection_text:
                self.long_term_memory.append(reflection_text)
                if config.SIMULATION_MODE == 'debug':
                    print(f"DEBUG {self.agent.name} Reflection Added: '{reflection_text[:80]}...'")
            else:
                print(f"WARN {self.agent.name}: Reflection generated empty text.")

        except Exception as e:
            print(f"ERROR {self.agent.name}: Failed to generate reflection: {e}")
            # Optionally add a placeholder LTM entry indicating failure?

    def get_memory_context(self, **kwargs) -> str:
        """Returns a formatted string containing both long-term reflections
           and recent short-term observations."""

        context = "--- Core Reflections & Summaries ---\n"
        if self.long_term_memory:
            # Maybe limit the number of reflections shown? For now, show all.
            context += "\n".join(f"- {ltm}" for ltm in self.long_term_memory) + "\n"
        else:
            context += "No long-term reflections generated yet.\n"

        context += "\n--- Recent Observations (most recent last) ---\n"
        if self.short_term_memory:
            # Limit the number of short-term memories shown in context?
            max_short_term_in_context = kwargs.get('max_short_term_entries', 20) # Example limit
            start_index = max(0, len(self.short_term_memory) - max_short_term_in_context)
            if start_index > 0:
                context += "[...older observations omitted...]\n"

            for mem in self.short_term_memory[start_index:]:
                prefix = f"[T:{mem['type']}" + (f" S:{mem['step']}" if mem['step'] is not None else "") + "]"
                context += f"{prefix} {mem['text']}\n"
        else:
            context += "No recent observations recorded.\n"

        # Limit total context length if needed (crude truncation)
        max_total_length = kwargs.get('max_context_length', 4000) # Example limit
        if len(context) > max_total_length:
            context = f"... (Memory Context Trimmed) ...\n{context[-max_total_length:]}"

        # print(f"DEBUG {self.agent.name} Memory Context Requested. Length: {len(context)}")
        return context.strip()
    def clear(self):
        """Clears both short-term and long-term memory."""
        self.short_term_memory = []
        self.long_term_memory = []
        self.unreflected_count = 0
        print(f"DEBUG {self.agent.name}: Memory cleared.")
        

    

    

    