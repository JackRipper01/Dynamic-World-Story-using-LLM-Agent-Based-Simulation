# thinking.py
import google.generativeai as genai
import config
from abc import ABC, abstractmethod

class BaseThinker(ABC):
    """Abstract base class for agent thinking/decision-making modules."""
    @abstractmethod
    def generate_utterance(self, agent, world_state, memory_context):
        """Generates the agent's next action/thought/speech as a natural language string."""
        pass

class GeminiThinker(BaseThinker):
    """Uses Google Gemini LLM to generate agent utterances."""
    def __init__(self, model):
        self.llm = model # Pass the initialized model instance

    def generate_utterance(self, agent, world_state, memory_context):
        """Formats prompt and calls the Gemini API."""
        current_world_context = world_state.get_context_for_agent(agent.name)

        prompt = f"""You are {agent.name}, a character in a simulated world.
Your personality: {agent.personality}.

Your current situation:
{current_world_context}

{memory_context}

Based *only* on the above, what do you think, say, or do next?
Describe your action, thought, or utterance in a single, short, natural sentence.
Focus on what you *personally* do or perceive. Be concise.
Examples:
- I walk towards the Forest Edge.
- I ask Bob, "Did you hear that noise?"
- I examine the ground near the shelter.
- I think this mist is unnerving.
- I decide to wait and see what happens.

Your response (one sentence):"""

        print(f"\n[{agent.name} is thinking...]")
        # print(f"--- DEBUG PROMPT for {agent.name} ---\n{prompt}\n--------------------") # Optional debug

        try:
            response = self.llm.generate_content(prompt)
            # Basic cleanup: strip whitespace, take first line
            utterance = response.text.strip().split('\n')[0]

            # Validate response
            if not utterance or len(utterance) < 5: # Arbitrary minimum length
                 print(f"[{agent.name} Warning]: LLM gave short/empty response: '{utterance}'. Defaulting to wait.")
                 utterance = f"{agent.name} waits silently, unsure what to do." # More descriptive default
            else:
                 # Ensure the response sounds like the agent (optional refinement)
                 # if not utterance.lower().startswith(("i ", "my ", f"{agent.name.lower()} ")):
                 #    utterance = f"{agent.name} thinks: {utterance}" # Frame it if needed
                 print(f"[{agent.name} decides]: {utterance}")

            return utterance

        except Exception as e:
            print(f"[{agent.name} Error]: LLM generation failed: {e}")
            # Check for specific feedback if available
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                 print(f"[{agent.name} Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            # Return a meaningful error state utterance
            return f"{agent.name} pauses, feeling confused or encountering an issue."