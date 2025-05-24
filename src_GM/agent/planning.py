# planning.py
import time
import google.generativeai as genai
import config
from abc import ABC, abstractmethod
try:
    # Also catch general API errors
    from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
except ImportError:
    # Provide fallback or raise an error if the necessary library is not installed
    print("Warning: google-api-core not installed. API error handling may not work correctly.")

    class ResourceExhausted(Exception):
        pass  # Define a dummy exception if import fails

    class GoogleAPICallError(Exception):
        pass  # Define a dummy exception if import fails
    
class BasePlanning(ABC):
    """Abstract base class for agent thinking/decision-making modules."""
    @abstractmethod
    def generate_output(self, agent, static_world_context, memory_context):  # Renamed
        """Generates the agent's next intended action/thought/speech output."""
        pass

class SimplePlanning(BasePlanning):
    """
    A simple planning module that uses an LLM to generate action outputs.
    """
    
    def __init__(self, model):
        self.llm = model # Pass the initialized model instance
        self.is_initial_prompt=False

    def generate_output(self, agent, static_world_context, memory_context): 
        """Formats prompt and calls the Gemini API."""

        prompt = f"""You are {agent.name}, a character in a simulated world.
Your personality: {agent.personality}.
Your gender: {getattr(agent, 'gender', 'Not specified')}.
Your goals: {agent.goals}
Your background: {agent.background}

Your current world situation:

{static_world_context}

Your recent memories and perceptions (most recent last):

{memory_context}

Based on your personality, goals, gender, situation, and memories, what do you think, say, or do next?
Choose and describe ONE single action, or utterance. You can be descriptive but must focus on only one action.
If you speak, use quotes. If you act, describe the action.

IMPORTANT: If someone has spoken to you directly in your recent perceptions, prioritize responding to them before pursuing your own goals. Being responsive to others is crucial for realistic social interaction.

Consider how you might interact with other agents if they're present. You can:
- Talk to them (e.g., "Ask Bob, "Hello, can you help me?"")
- Collaborate with them on tasks
- Observe their behavior
- Respond to their actions or questions
- Form alliances or rivalries based on your goals

Examples of valid single intents:
- Walk towards the Forest Edge to see if I can find any berries.
- Ask Bob, "Did you hear that strange noise coming from the shelter? It sounded like scratching."
- Carefully examine the ground near the shelter for any tracks or clues.
- Think: 'This weather is getting colder. I need to reinforce the shelter soon, especially if Bob plans on staying.'
- Wait silently and observe Bob's next move.
- Respond to Alice, "The forest does look interesting, but I'm more concerned about finding food and water first. What kind of potion are you making?"

Important: Provide only ONE action, thought, or utterance. Do not combine multiple actions.
Your action output (one single action):"""
        if self.is_initial_prompt==False:
            self.is_initial_prompt=True
            print(f"[{agent.name} Prompt]: {prompt}")  #TEMPORAL ------------------------------------->
        # if config.SIMULATION_MODE == 'debug':
        #     print(f"\n[{agent.name} is thinking...]")
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
            # else:
            #     if config.SIMULATION_MODE == 'debug':
            #         print(f"[{agent.name} intends]: {utterance}")
            
            # print(f"[{agent.name} Response]: {utterance}")  #TEMPORAL ------------------------------------->
            return utterance

        except Exception as e:
            print(f"[{agent.name} Error]: LLM generation failed: {e}")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                print(
                    f"[{agent.name} Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            return f"Intend to pause due to confusion."  # Return an intent


class SimplePlanningIdentityOnly(BasePlanning):
    """
    A simple planning module that uses an LLM to generate action outputs.
    """

    def __init__(self, model):
        self.llm = model  # Pass the initialized model instance
        self.is_initial_prompt = False

    def generate_output(self, agent, static_world_context, memory_context):
        """Formats prompt and calls the Gemini API."""

        prompt = f"You are {agent.name}, a character in a simulated world.\n"


        prompt += f"Your identity: {agent.identity}\n"

        # Conditionally add the context line
        if agent.initial_context:
            prompt += f"Context: {agent.initial_context}\n"

        # Add the rest of the multi-line content
        prompt += f"""
Your current world situation:

{static_world_context}

Your recent memories and perceptions (most recent last):

{memory_context}

Based on your identity, situation, and memories, what do you think, say, or do next?
Choose and describe ONE single action, or utterance. You can be descriptive but must focus on only one action.
If you speak, use quotes. If you act, describe the action.

Consider how you might interact with other agents if they're present. You can:
- Talk to them (e.g., "Ask Bob, "Hello, can you help me?"")
- Collaborate with them on tasks
- Observe their behavior
- Respond to their actions or questions
- Form alliances or rivalries based on your goals

Examples of valid single intents:
- Walk towards the Forest Edge to see if I can find any berries.
- Ask Bob, "Did you hear that strange noise coming from the shelter? It sounded like scratching."
- Carefully examine the ground near the shelter for any tracks or clues.
- Tell to self: 'This weather is getting colder. I need to reinforce the shelter soon, especially if Bob plans on staying.'
- Wait silently and observe Bob's next move.
- Respond to Alice, "The forest does look interesting, but I'm more concerned about finding food and water first. What kind of potion are you making?"

Important: Provide only ONE action, thought, or utterance. Do not combine multiple actions.
Your action output (one single action):"""
        if self.is_initial_prompt == False:
            self.is_initial_prompt = True
            # TEMPORAL ------------------------------------->
            print(f"[{agent.name} Prompt]: {prompt}")
        # if config.SIMULATION_MODE == 'debug':
        #     print(f"\n[{agent.name} is thinking...]")
        # print(f"--- DEBUG PROMPT for {agent.name} ---\n{prompt}\n--------------------")
        response = None
        try:
            response = self.llm.generate_content(prompt)
            # Use the full, stripped response text
            utterance = response.text.strip()

            # Check if the response is empty or just whitespace
            if not utterance:
                print(
                    f"[{agent.name} Warning]: LLM gave short/empty response: '{utterance}'. Defaulting to wait intent.")
                utterance = f"Intend to wait silently."
            # else:
            #     if config.SIMULATION_MODE == 'debug':
            #         print(f"[{agent.name} intends]: {utterance}")

            # print(f"[{agent.name} Response]: {utterance}")  #TEMPORAL ------------------------------------->
            return utterance

        except ResourceExhausted as e:
            print(
                f"[{agent.name} Error]: LLM generation failed: {e}. Waiting 10 seconds and retrying...")
            time.sleep(10)
            return self.generate_output(agent, static_world_context, memory_context)
        
        except Exception as e:
            print(f"[{agent.name} Error]: LLM generation failed: {e}")
            # check if the error is  "429 You exceeded your current quota,...", in that case, wait 10 seconds and retry the request
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                print(
                    f"[{agent.name} Safety Block]: Reason: {response.prompt_feedback.block_reason}")
            return f"Intend to pause due to confusion."  # Return an intent
