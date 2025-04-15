# thinking.py
import google.generativeai as genai
import config
from abc import ABC, abstractmethod

class BasePlanning(ABC):
    """Abstract base class for agent thinking/decision-making modules."""
    @abstractmethod
    def generate_output(self, agent, static_world_context, memory_context):  # Renamed
        """Generates the agent's next intended action/thought/speech output."""
        pass

class SimplePlanning(BasePlanning):
    """Uses Google Gemini LLM to generate agent utterances."""
    def __init__(self, model):
        self.llm = model # Pass the initialized model instance

    def generate_output(self, agent, static_world_context, memory_context):  # Renamed
        """Formats prompt and calls the Gemini API."""

        prompt = f"""You are {agent.name}, a character in a simulated world.
Your personality: {agent.personality}.

Your current static situation:
{static_world_context}

Your recent memories and perceptions (most recent last):
{memory_context}

Based *only* on the above, what do you intend to think, say, or do next?
Describe your intended action, thought, or utterance in a single, short, natural sentence.
Focus on your intent. Be concise.
Examples:
- Try to walk towards the Forest Edge.
- Ask Bob, "Did you hear that noise?"
- Examine the ground near the shelter.
- Think about how cold the weather is getting.
- Decide to wait and see what happens.

Your intended output (one sentence):"""  # Changed 'response' to 'intended output'

        print(f"\n[{agent.name} is thinking...]")
        # print(f"--- DEBUG PROMPT for {agent.name} ---\n{prompt}\n--------------------")

        try:
            response = self.llm.generate_content(prompt)
            utterance = response.text.strip().split('\n')[0]

            if not utterance or len(utterance) < 5:
                print(
                    f"[{agent.name} Warning]: LLM gave short/empty response: '{utterance}'. Defaulting to wait intent.")
                utterance = f"Intend to wait silently."
            else:
                print(f"[{agent.name} intends]: {utterance}")

            return utterance

        except Exception as e:
            print(f"[{agent.name} Error]: LLM generation failed: {e}")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                print(
                    f"[{agent.name} Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            return f"Intend to pause due to confusion."  # Return an intent
