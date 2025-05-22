# src_GM/story_generator.py
from abc import ABC, abstractmethod
from world import WorldState  # To access event logs, etc.
import config  # To access agent_configs, narrative_goal for context


class BaseStoryGenerator(ABC):
    """
    Abstract Base Class for components that generate a narrative story
    from simulation data.
    """
    @abstractmethod
    def generate_story(self, world_state: WorldState, agent_configs: list, narrative_goal: str) -> str:
        """
        Generates a story based on the provided simulation data.

        Args:
            world_state: The final WorldState object, containing the event log.
            agent_configs: The initial configurations for all agents (for character intros).
            narrative_goal: The overarching narrative goal of the simulation (for theme).

        Returns:
            A string containing the generated story.
        """
        pass


class LLMLogStoryGenerator(BaseStoryGenerator):
    """
    Generates a story by feeding the entire event log and context to an LLM.
    """

    def __init__(self, model):
        self.llm = model
        self.tone = config.TONE  

    def generate_story(self, world_state: WorldState, agent_configs: list, narrative_goal: str) -> str:
        print("\n--- Generating Story from Simulation Logs ---")

        # 1. Gather Character Information
        character_intros = []
        for agent_conf in agent_configs:
            intro = f"- {agent_conf['name']}: {agent_conf['identity']}."
            character_intros.append(intro)

        characters_summary = "The characters involved were:\n" + \
            "\n".join(character_intros)

        # 2. Gather Event Log
        # Format events for better readability by the LLM
        formatted_events = []
        for event in world_state.event_log:
            # Event = namedtuple("Event", ["description", "location", "scope", "step", "triggered_by"])
            location_info = f"at {event.location}" if event.location and event.location != "Global" else "globally"
            scope_info = f"(scope: {event.scope})"

            # Make agent actions more prominent
            event_text = event.description
            if event.scope == "action_outcome" and event.triggered_by != "System" and event.triggered_by != "Director":
                # If the description already starts with the agent's name, use it.
                # Otherwise, prepend. This handles cases where outcome_description is already good.
                if not event_text.lower().startswith(event.triggered_by.lower()):
                    event_text = f"{event.triggered_by} {event_text[0].lower() + event_text[1:] if event_text else ''}"

            formatted_events.append(
                f"{event_text}, Location: {location_info}, {scope_info} scope.\n")
            print(f"Event: {event_text}, Location: {location_info}, {scope_info} scope.")#--------------------------> temporal

        events_summary = "The key events that unfolded, in chronological order:\n" + \
            "\n".join(formatted_events)

        tone_prompt = ""
        if self.tone:
            tone_prompt= self.tone

        # 3. Craft Prompt
        prompt = f"""You are a master storyteller. Based on the following information from a simulated world, write a coherent and engaging story.

Narrative Premise/Goal:
{narrative_goal if narrative_goal else "An emergent narrative adventure."}

Tone: {tone_prompt if tone_prompt else "Neutral"}

{characters_summary}

{events_summary}

Please weave these elements into a flowing narrative. Describe the setting, character actions, interactions, and the overall progression of events. Try to infer thoughts or motivations if consistent with personalities and events, but clearly distinguish between observed events and inferred internal states if necessary. Make it readable and interesting.

If the simulation ended without a clear conclusion, feel free to create a fitting ending or cliffhanger.

Your Story:
"""
        if config.SIMULATION_MODE == 'debug':
            print("--- Story Generation Prompt ---")
            print(prompt[:1000] + "..." if len(prompt) >
                  1000 else prompt)  # Print a snippet if too long
            print("-----------------------------")

        # 4. Call LLM
        try:
            # Potentially use a different generation config for storytelling
            story_generation_config = {
                "temperature": 0.7,  # More creative but still coherent
                "top_p": 0.95,
                "top_k": 60,  # Wider K for more diverse vocabulary
                "max_output_tokens": 2000,  # Allow for a longer story
            }
            # If you want to use a specific model or config just for story generation:
            # story_model = genai.GenerativeModel(model_name=config.MODEL_NAME, generation_config=story_generation_config)
            # response = story_model.generate_content(prompt)
            # Or use the existing model with its default config, or temporarily override

            response = self.llm.generate_content(
                prompt, generation_config=story_generation_config)  # Can override if needed
            story_text = response.text.strip()

            if not story_text:
                return "The LLM storyteller was lost for words and produced an empty tale."

            print("--- Story Generation Complete ---")
            return story_text

        except Exception as e:
            print(f"[StoryGenerator Error]: LLM story generation failed: {e}")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                print(f" (Safety Feedback: {response.prompt_feedback})")
            return f"An error occurred while trying to tell the story: {e}"
