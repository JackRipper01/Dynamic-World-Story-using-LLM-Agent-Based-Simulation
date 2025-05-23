# src_GM/story_generator.py
from abc import ABC, abstractmethod
import time
from world import WorldState  # To access event logs, etc.
import config  # To access agent_configs, narrative_goal for context
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

    def generate_story(self, log_file_path: str, agent_configs: list, narrative_goal: str) -> str:
        print("\n--- Generating Story from Simulation Logs ---")

        # 1. Gather Character Information (remains the same)
        character_intros = []
        for agent_conf in agent_configs:
            intro = f"- {agent_conf['name']}: {agent_conf['identity']}."
            character_intros.append(intro)

        characters_summary = "The characters involved were:\n" + \
            "\n".join(character_intros)

        # 2. Read Event Log from File
        formatted_events = []
        try:
            # Read the content line by line from the log file
            with open(log_file_path, 'r', encoding='utf-8') as f:
                # Read all lines, strip whitespace/newlines, and filter out empty lines
                raw_events = [line.strip() for line in f if line.strip()]

            # Note: Since the log file saved raw strings without the original
            # location, scope, triggered_by metadata, we can only present
            # the raw logged strings to the LLM.
            # The original formatting like 'Location: at {location_info}' is lost.
            formatted_events = raw_events  # Each line from the file is an event

            if not formatted_events:
                events_summary = "No events were logged during the simulation."
                print("No events found in the log file.")
            else:
                print(
                    f"Read {len(formatted_events)} events from {log_file_path}")
                # Print read events for debug/verification if needed
                if config.SIMULATION_MODE == 'debug':
                    print("--- Logged Events Read ---")
                    # Print first 20 lines or less
                    for i, event_line in enumerate(formatted_events[:20]):
                        print(f"Event {i+1}: {event_line}")
                    if len(formatted_events) > 20:
                        print("...")
                    print("------------------------")

                events_summary = "The key events that unfolded, based on the simulation log:\n" + \
                                 "\n".join(formatted_events)

        except FileNotFoundError:
            events_summary = f"Error: The event log file '{log_file_path}' was not found."
            print(events_summary)
            formatted_events = []  # Ensure it's empty if file not found
        except Exception as e:
            events_summary = f"Error reading event log file '{log_file_path}': {e}"
            print(events_summary)
            formatted_events = []  # Ensure it's empty if reading failed

        tone_prompt = ""
        if self.tone:
            tone_prompt = self.tone

        # 3. Craft Prompt (remains largely the same, uses the new events_summary)
        # Check if we actually read events before including the summary header
        if formatted_events:
            events_section = f"""{events_summary}"""
        else:
            # If no events were read (file not found or empty), adapt the prompt
            # This will contain the error message or "No events..."
            events_section = events_summary

        prompt = f"""You are a master storyteller. Based on the following information from a simulated world, write a coherent and engaging story.

Narrative Premise/Goal:
{narrative_goal if narrative_goal else "An emergent narrative adventure."}

Tone: {tone_prompt if tone_prompt else "Neutral"}

{characters_summary}

{events_section}

Instructions for the Story:
- Weave these elements into a flowing narrative.
- Describe the context, character actions, interactions, and the overall progression of events.
- Strive for high fidelity to the simulation events, recounting them as they occurred.
- Try to infer thoughts or motivations if consistent with personalities and events (clearly distinguish if needed).
- Add one or two paragraphs for introduction/context at the start.
- Create a fitting ending or cliffhanger if the simulation is inconclusive.
- Make the story readable and engaging.

Your Story:
"""
        if config.SIMULATION_MODE == 'debug':
            print("--- Story Generation Prompt ---")
            # Limit prompt printing length for readability
            print(prompt[:2000] + "..." if len(prompt) >
                  2000 else prompt)
            print("-----------------------------")

        # 4. Call LLM (remains the same)
        try:
            story_generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 60,
                "max_output_tokens": 2000,
            }

            response = self.llm.generate_content(
                prompt, generation_config=story_generation_config)
            story_text = response.text.strip()

            if not story_text:
                # Log the failure to the simulation output file as well
                failure_message = "The LLM storyteller was lost for words and produced an empty tale."
                print(failure_message)  # Print to console
                # Use your logging utility here if needed:
                # from logs import append_to_log_file
                # append_to_log_file("simulation_log.txt", failure_message)
                return failure_message

            print("--- Story Generation Complete ---")
            # Print generated story to console if desired
            # print(story_text)

            # You might also want to log the final generated story to a DIFFERENT file
            # than the event log, or append it to the SAME file with a clear marker.
            # E.g.,
            # from logs import append_to_log_file
            # append_to_log_file("simulation_log.txt", "\n--- Final Generated Story ---")
            # append_to_log_file("simulation_log.txt", story_text)
            # append_to_log_file("simulation_log.txt", "---------------------------\n")

            return story_text
        except ResourceExhausted as e:
            print(
                f"[{self.name} Error]: LLM generation failed: {e}. Waiting 10 seconds and retrying...")
            time.sleep(10)
            return self.generate_story(log_file_path, agent_configs, narrative_goal)
        
        except Exception as e:
            error_message = f"[StoryGenerator Error]: LLM story generation failed: {e}"
            print(error_message)
            # Log the error to your simulation output file
            # from logs import append_to_log_file
            # append_to_log_file("simulation_log.txt", error_message)

            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                feedback_message = f" (Safety Feedback: {response.prompt_feedback})"
                print(feedback_message)
                # Log safety feedback
                # from logs import append_to_log_file
                # append_to_log_file("simulation_log.txt", feedback_message)

            return f"An error occurred while trying to tell the story: {e}"

# Example usage (assuming you have a StoryGenerator instance 'story_gen'):
# story_gen = StoryGenerator(llm_model=your_llm_instance, tone="Agatha Christie Style")
# simulation_event_log_file = "path/to/your/event_log.txt"
# agents_info = [...] # Your list of agent configs
# narrative_goal_desc = "Solve the murder mystery at Blackwood Manor."
# generated_story = story_gen.generate_story(simulation_event_log_file, agents_info, narrative_goal_desc)
# print("\n--- Final Result ---")
# print(generated_story)
