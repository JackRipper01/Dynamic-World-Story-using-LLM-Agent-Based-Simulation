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

    def generate_output(self, agent, static_world_context, memory_context): 
        """Formats prompt and calls the Gemini API."""

        # Prepare goals string (handle empty list)
        goals_string = "Your current goals:\n" + "\n".join(f"- {g}" for g in agent.goals) if agent.goals else "You have no specific goals right now."

        prompt = f"""You are {agent.name}, a character in a simulated world.
Your personality: {agent.personality}.
Your gender: {getattr(agent, 'gender', 'Not specified')}.

{goals_string}

Your current world situation:
{static_world_context}

Your recent memories and perceptions (most recent last):
{memory_context}

Based on your personality, goals, gender, situation, and memories, what do you intend to think, say, or do next?
Choose and describe ONE single intended action, thought, or utterance. You can be descriptive but must focus on only one intent.
If you intend to speak, use quotes. If you intend to think, describe the thought. If you intend to act, describe the action.

Examples of valid single intents:
- Intend to walk towards the Forest Edge to see if I can find any berries.
- Intend to ask Bob, "Did you hear that strange noise coming from the shelter? It sounded like scratching."
- Intend to carefully examine the ground near the shelter for any tracks or clues.
- Intend to think: 'This weather is getting colder. I need to reinforce the shelter soon, especially if Bob plans on staying.'
- Intend to wait silently and observe Bob's next move.

Important: Provide only ONE intended action, thought, or utterance. Do not combine multiple intents.
Your intended output (one single intent):"""

        print(f"\n[{agent.name} is thinking...]")
        # print(f"--- DEBUG PROMPT for {agent.name} ---\n{prompt}\n--------------------")
        response=None
        try:
            response = self.llm.generate_content(prompt)
            # Use the full, stripped response text
            utterance = response.text.strip()

            # Check if the response is empty or just whitespace
            if not utterance:
                print(
                    f"[{agent.name} Warning]: LLM gave short/empty response: '{utterance}'. Defaulting to wait intent.")
                utterance = f"Intend to wait silently."
            else:
                # Print the potentially multi-line intent
                print(f"[{agent.name} intends]: {utterance}")

            return utterance

        except Exception as e:
            print(f"[{agent.name} Error]: LLM generation failed: {e}")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                print(
                    f"[{agent.name} Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            return f"Intend to pause due to confusion."  # Return an intent
