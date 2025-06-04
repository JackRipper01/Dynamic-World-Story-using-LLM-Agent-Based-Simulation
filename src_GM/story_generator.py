# src_GM/story_generator.py
from google.api_core.exceptions import ResourceExhausted
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
    

from logs import append_to_log_file  # To log generated stories or errors

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

    def generate_story(self, log_file_path: str, agent_configs: list, narrative_goal: str,tone:str) -> str:
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
        if tone:
            tone_prompt = tone

        # 3. Craft Prompt (remains largely the same, uses the new events_summary)
        # Check if we actually read events before including the summary header
        if formatted_events:
            events_section = f"""{events_summary}"""
        else:
            # If no events were read (file not found or empty), adapt the prompt
            # This will contain the error message or "No events..."
            events_section = events_summary

        prompt = f"""You are a master storyteller. Your task is to transform raw simulation logs into a vivid, coherent, and engaging story.

Narrative Premise/Goal:
{narrative_goal if narrative_goal else "An emergent narrative adventure."}

Tone: {tone_prompt if tone_prompt else "Neutral"}

{characters_summary}

{events_section}

Instructions for the Story:
- **Core Principle:** Use the simulation logs as the *ground knowledge* and *key plot points*. The story must adhere strictly to the sequence and core facts of the logged events, ensuring high fidelity.
- **Narrative Expansion:** Your primary goal is to *elaborate upon* and *contextualize* these events. Do not simply list them or present only dialogue.
- **Show, Don't Tell:**
    - **Setting & Atmosphere:** Describe the environment, time of day, weather, and the overall atmosphere. Set the scene for each significant event.
    - **Character Description:** Describe character appearances, expressions, body language, and subtle gestures.
    - **Sensory Details:** Incorporate sights, sounds, smells, and tactile sensations to immerse the reader.
    - **Actions & Movements:** Expand on simple actions. For example, instead of "Character A moved to the kitchen," describe *how* they moved, their purpose, and what they encountered.
- **Character Depth:**
    - **Internal Monologue/Thoughts:** Infer and describe characters' thoughts, feelings, and internal struggles. How do they react emotionally to the events? What are their immediate desires or concerns?
    - **Motivations:** Clearly (or subtly) reveal the motivations behind characters' actions and decisions, consistent with their established identities.
    - **Relationships:** Show the dynamics and evolution of relationships between characters through their interactions and reactions.
- **Flow and Pacing:**
    - Weave all elements into a flowing, continuous narrative prose.
    - Use smooth transitions between events and scenes.
    - Vary sentence structure and paragraph length for readability.
- **Introduction:** Begin with an engaging introduction (1-2 paragraphs) that sets the stage, introduces the primary characters, and hints at the overarching premise.
- **Conclusion:** Craft a compelling and conclusive ending of any length, even if the simulation logs end abruptly. Provide a fitting resolution, an impactful cliffhanger, or a thoughtful reflection on the events.


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
                "max_output_tokens": 4000,
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
            append_to_log_file("simulation_story_zero-shot.txt", "\n--- Final Generated Story ---")
            append_to_log_file("simulation_story_zero-shot.txt", story_text)
            append_to_log_file("simulation_story_zero-shot.txt",
                               "---------------------------\n")

            try:
                # Ensure 'config' is accessible, or pass narrative_goal and agent_configs directly
                with open("simulation_story.txt", "w", encoding="utf-8") as f:
                    f.write(
                        f"Simulation Goal: {narrative_goal if narrative_goal else 'N/A'}\n")  # Use narrative_goal from argument
                    f.write("Characters:\n")
                    for ac in agent_configs:  # Use agent_configs from argument
                        f.write(f"  - {ac['name']}: {ac['identity']}\n")
                    f.write("\n--- STORY ---\n")
                    f.write(story_text)  # Use the generated story_text
                print("\n(Story also saved to simulation_story.txt)")
            except Exception as e:
                print(f"\n[Error] Could not save story to file: {e}")
            
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

class LLMIterativeStoryGenerator:
    def __init__(self, llm, tone=None):
        self.llm = llm
        self.tone = tone

    def _call_llm_for_story(self, prompt: str, max_tokens: int) -> str:
        """Helper function to make the LLM call with error handling."""
        try:
            story_generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 60,
                "max_output_tokens": max_tokens,
            }
            response = self.llm.generate_content(
                prompt, generation_config=story_generation_config)
            story_text = response.text.strip()
            return story_text

        except ResourceExhausted as e:
            print(f"[{self.name if hasattr(self, 'name') else 'StoryGenerator'} Error]: LLM generation failed: {e}. Waiting 10 seconds and retrying...")
            time.sleep(10)
            # Be careful with infinite retries. Consider adding a retry counter.
            # Recursive retry or raise
            return self._call_llm_for_story(prompt, max_tokens)

        except Exception as e:
            error_message = f"[StoryGenerator Error]: LLM story generation failed: {e}"
            print(error_message)
            if 'response' in locals() and hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                feedback_message = f" (Safety Feedback: {response.prompt_feedback})"
                print(feedback_message)
            # Return a distinct error string
            return f"[ERROR]: An error occurred while trying to tell the story: {e}"

    def generate_initial_story_draft(self, log_file_path: str, agent_configs: list, narrative_goal: str) -> str:
        print("\n--- Generating Initial Story Draft from Simulation Logs ---")

        character_intros = []
        for agent_conf in agent_configs:
            intro = f"- {agent_conf['name']}: {agent_conf['identity']}."
            character_intros.append(intro)
        characters_summary = "The characters involved were:\n" + \
            "\n".join(character_intros)

        formatted_events = []
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                raw_events = [line.strip() for line in f if line.strip()]
            formatted_events = raw_events
            if not formatted_events:
                events_summary = "No events were logged during the simulation."
                print("No events found in the log file.")
            else:
                print(
                    f"Read {len(formatted_events)} events from {log_file_path}")
                if config.SIMULATION_MODE == 'debug':
                    print("--- Logged Events Read ---")
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
            formatted_events = []
        except Exception as e:
            events_summary = f"Error reading event log file '{log_file_path}': {e}"
            print(events_summary)
            formatted_events = []

        tone_prompt = self.tone if self.tone else ""

        if formatted_events:
            events_section = f"""{events_summary}"""
        else:
            events_section = events_summary

        # This prompt is modified slightly to explicitly state it's a first attempt at a full story
        prompt = f"""You are a master storyteller. Your task is to transform raw simulation logs into a vivid, coherent, and engaging story. This is your initial attempt to create the complete narrative.

Narrative Premise/Goal:
{narrative_goal if narrative_goal else "An emergent narrative adventure."}

Tone: {tone_prompt if tone_prompt else "Neutral"}

{characters_summary}

{events_section}

Instructions for the Story:
- **Core Principle: Weaving the Narrative:** Your paramount task is to transform the raw simulation logs into a *rich, immersive, and continuous narrative*. While maintaining high fidelity to the core events in the logs, *do not simply recount them*. Instead, use them as the structural backbone upon which you build a compelling story.
- **Narrative Expansion:** Your primary goal is to *elaborate upon* and *contextualize* these events but be careful not to simply list them or present only dialogue.
- **Show, Don't Tell:**
    - **Setting & Atmosphere:** Immerse the reader by vividly describing the environment, time of day, weather, and the overall atmosphere *as it changes and relates to the events*.
    - **Character Immersion:** Go beyond simple actions. Describe characters' appearances, expressions, body language, and subtle gestures. Infuse their internal thoughts, feelings, and emotional reactions to the unfolding events. Reveal their evolving motivations and the dynamics of their relationships through their interactions and dialogue.
    - **Sensory & Action Detail:** Incorporate rich sensory details (sights, sounds, smells, tactile sensations). For actions, detail *how* they were performed, the *purpose* behind them, and the *challenges or successes* encountered.
- **Cohesion and Flow:**
    - **Seamless Transitions:** Ensure smooth, logical, and evocative transitions between scenes and events. Avoid abrupt shifts and chronological leaps without proper narrative bridging. Each new scene should naturally follow the previous one.
    - **Pacing & Rhythm:** Vary sentence structure and paragraph length to create a dynamic reading experience that reflects the story's tension and calm.
    - **Unified Story, Not a List:** The ultimate goal is a flowing, prose-driven narrative, not a factual report or a series of bullet points disguised as text. Every event should feel earned and contribute to the overall story progression. Avoid starting sentences with "Then," or similar repetitive chronological markers.
- **Leveraging the Narrative Goal:** Continuously keep the overarching "Narrative Premise/Goal" in mind. How do the events contribute to or evolve this goal? Use it to guide the story's direction and emotional tone.
- **Introduction:** Begin with an engaging introduction (1-2 paragraphs) that sets the stage, introduces the primary characters, and hints at the overarching premise. Make sure that the introduction is coherent with the logs. For example, if the logs start with a character in a certain location, ensure the introduction connects to that.
Your Story:
"""

        if config.SIMULATION_MODE == 'debug':
            print("--- Story Generation Prompt (First Draft) ---")
            print(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
            print("-----------------------------")

        # Use max_output_tokens from your config
        generated_story = self._call_llm_for_story(prompt, max_tokens=2048)

        if not generated_story or "[ERROR]" in generated_story:
            failure_message = generated_story if "[ERROR]" in generated_story else "The LLM storyteller produced an empty draft."
            print(failure_message)
            return failure_message

        print("--- Initial Story Draft Complete ---")
        append_to_log_file("Initial_Story_Draft.txt",
                           "\n--- Initial Generated Story Draft ---")
        append_to_log_file("Initial_Story_Draft.txt", generated_story)
        append_to_log_file("Initial_Story_Draft.txt",
                           "-----------------------------------\n")

        return generated_story

    def refine_and_conclude_story(self, current_story_so_far: str, agent_configs: list, narrative_goal: str) -> str:
        """
        Iteratively refines and attempts to conclude the story based on previous content.
        The LLM determines if it's complete or needs to continue.
        """
        print("\n--- Refining Story and Checking for Conclusion ---")

        # Re-gather context as it's passed in each iteration
        character_intros = []
        for agent_conf in agent_configs:
            intro = f"- {agent_conf['name']}: {agent_conf['identity']}."
            character_intros.append(intro)
        characters_summary = "The characters involved were:\n" + \
            "\n".join(character_intros)

        tone_prompt = self.tone if self.tone else "Neutral"

        # The core iterative prompt
        prompt = f"""You are a master storyteller. You are currently reviewing a story in progress.

Narrative Premise/Goal:
{narrative_goal if narrative_goal else "An emergent narrative adventure."}

Tone: {tone_prompt}

{characters_summary}

**Story So Far (Read this carefully):**
{current_story_so_far}

---

**Your Task & Decision Process:**

1.  **Review the "Story So Far":**
    *   Does it feel like it has reached a compelling, natural, and conclusive narrative ending that aligns with the "Narrative Premise/Goal"?.

2.  **Determine Action:**
    *   **IF the story is NOT yet complete OR needs further development/elaboration based on remaining logs or to reach a proper conclusion:**
        *   Begin your response with the tag: `[CONTINUE_WRITING]`
        *   Then, write the *next coherent segment* of the story, picking up exactly where the "Story So Far" left off.
        *   Continue to incorporate any remaining logs, or start building towards a satisfying conclusion if logs are exhausted.
        *   Ensure new content is consistent with established characters and world.
    *   **IF the story IS complete and has reached a satisfactory, conclusive ending:**
        *   Begin your response with the tag: `[STORY_COMPLETE]`
        *   Then, provide the *final, polished version* of the entire story. This should be the "Story So Far" potentially with a final concluding paragraph or two. Ensure it flows perfectly as a complete work.
---

**General Storytelling Guidelines:**
- **Narrative Expansion:** Elaborate upon and contextualize events. Do not simply list them or present only dialogue.
- **Show, Don't Tell:** Expand descriptions of settings, character expressions, body language, actions, and incorporate sensory details.
- **Character Depth:** Deepen character insight by inferring their thoughts, feelings, and motivations, consistent with their personalities.
- **Pacing & Flow:** Ensure smooth transitions, varied sentence structure, and overall readability.
- **Avoid Repetition:** Ensure variety in language and sentence structure.

Your Response (starting with either [CONTINUE_WRITING] or [STORY_COMPLETE] ):
"""
        if config.SIMULATION_MODE == 'debug':
            print("--- Story Refinement/Conclusion Prompt ---")
            print(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
            print("-----------------------------")

        # Set a high max_output_tokens because the model might either append a short segment
        # or output the entire story if it determines it's complete.
        response_text = self._call_llm_for_story(prompt, max_tokens=8192)

        if not response_text or "[ERROR]" in response_text:
            failure_message = response_text if "[ERROR]" in response_text else "The LLM produced an empty response or an error during refinement."
            print(failure_message)
            return failure_message  # Return error to stop iteration

        # Parse the response based on the tags
        if response_text.startswith("[CONTINUE_WRITING]"):
            segment = response_text[len("[CONTINUE_WRITING]"):].strip()
            print("LLM chose to CONTINUE WRITING.")
            # Preserve tag for external loop to process
            return "[CONTINUE_WRITING]" + segment
        elif response_text.startswith("[STORY_COMPLETE]"):
            final_story = response_text[len("[STORY_COMPLETE]"):].strip()
            print("LLM determined story is COMPLETE.")
            # Preserve tag for external loop to process
            return "[STORY_COMPLETE]" + final_story
        else:
            print(
                "WARNING: LLM did not start response with expected tag. Treating as continuation.")
            return "[CONTINUE_WRITING]" + response_text # Default to continue if no tag
        
    def continue_narrative_from_logs(self, current_story_so_far: str, full_log_content: str, agent_configs: list, narrative_goal: str) -> str:
        """
        Continues generating the narrative from simulation logs, aiming to cover all significant events.
        The LLM will indicate if it believes the logs are sufficiently covered.
        
        Args:
            current_story_so_far: The story written so far.
            full_log_content: The complete, raw simulation logs.
            agent_configs: Configuration for agents/characters.
            narrative_goal: The overall goal for the story.
            
        Returns:
            A string indicating either "[LOGS_COMPLETE]" or "[CONTINUE_FROM_LOGS]" or "[CONTINUE_FROM_LOGS_STARTING_FROM_A_NEW_SENTENCE]" followed by the new segment.
            Returns "[ERROR]" if the LLM call fails or returns an unexpected format.
        """
        try:
            character_intros = []
            for agent_conf in agent_configs:
                intro = f"- {agent_conf['name']}: {agent_conf['identity']}."
                character_intros.append(intro)
            characters_summary = "The characters involved were:\n" + \
                "\n".join(character_intros)

            system_prompt = f"""
            You are a master storyteller. Your task is to transform raw simulation logs into a vivid, coherent, and engaging story.
            Your task is to review the existing story draft against the provided simulation logs and to continue writing it if necessary.
            
            **Instructions:**
            1.  **Review Coverage:** Carefully read the `Current Story Draft` and compare it against the `Simulation Logs`.
                Identify if there are significant events, crucial character interactions, or key plot points in the logs that have not yet been fully integrated or narrated in the story.
            2.  **Continue if Necessary:** If you identify uncovered significant logs, continue the story to incorporate them.
                Add new narrative segments that flow naturally from the `Current Story Draft`.
                Maintain the tone, style, and established plot of the story.
                Focus on moving the plot forward based on the next chronological events in the logs that haven't been covered.
            3.  **Conclude if Sufficient:** If you believe the `Current Story Draft` has adequately covered all *crucial* events from the `Simulation Logs`
                to form a coherent and compelling narrative (even if not every minor log entry is literally transcribed), then indicate that the log conversion phase is complete.
                
            **Narrative Goal:** {narrative_goal}
            
            **Characters:**
            {characters_summary}
            
            **Tone:** {self.tone}
            
            How to build a good story:
            - **Narrative Expansion:** Your primary goal is to *elaborate upon* and *contextualize* these events while maintaining high fidelity to the core events in the logs, *do not simply recount them*. Instead, use them as the structural backbone upon which you build a compelling story. Be careful not to simply list them or present only dialogue.
            - **Show, Don't Tell:**
                - **Setting & Atmosphere:** Immerse the reader by vividly describing the environment, time of day, weather, and the overall atmosphere *as it changes and relates to the events*.
                - **Character Immersion:** Go beyond simple actions. Describe characters' appearances, expressions, body language, and subtle gestures. Infuse their internal thoughts, feelings, and emotional reactions to the unfolding events. Reveal their evolving motivations and the dynamics of their relationships through their interactions and dialogue.
                - **Sensory & Action Detail:** Incorporate rich sensory details (sights, sounds, smells, tactile sensations). For actions, detail *how* they were performed, the *purpose* behind them, and the *challenges or successes* encountered.
            - **Cohesion and Flow:**
                - **Seamless Transitions:** Ensure smooth, logical, and evocative transitions between scenes and events. Avoid abrupt shifts and chronological leaps without proper narrative bridging. Each new scene should naturally follow the previous one.
                - **Pacing & Rhythm:** Vary sentence structure and paragraph length to create a dynamic reading experience that reflects the story's tension and calm.
                - **Unified Story, Not a List:** The ultimate goal is a flowing, prose-driven narrative, not a factual report or a series of bullet points disguised as text. Every event should feel earned and contribute to the overall story progression. Avoid starting sentences with "Then," or similar repetitive chronological markers.
            - **Leveraging the Narrative Goal:** Continuously keep the overarching "Narrative Premise/Goal" in mind. How do the events contribute to or evolve this goal? Use it to guide the story's direction and emotional tone.

            **Simulation Logs (full chronological record):**
            {full_log_content}
            
            **Current Story Draft (what you have written so far):**
            {current_story_so_far}
            
            **Your Response Format:**
            -   If you need to continue the story to cover more logs and you want to start from a incomplete sentence, start your response with [CONTINUE_FROM_LOGS_STARTING_FROM_INCOMPLETE_SENTENCE] followed by the new narrative segment you want to append.
            -   If you need to continue the story to cover more logs and you want to start from a new sentence, start your response with [CONTINUE_FROM_LOGS_STARTING_FROM_A_NEW_SENTENCE] followed by the new narrative segment you want to append.
            -   If you believe all crucial logs have been converted into the narrative and this phase is complete, start your response with [LOGS_COMPLETE] . DO NOT re-output the entire story, just the tag [LOGS_COMPLETE] .
            """

            response = self._call_llm_for_story(
                prompt=system_prompt,max_tokens=2048)

            # Keep the check simple; the calling script will handle the content
            if response.startswith("[CONTINUE_FROM_LOGS_STARTING_FROM_INCOMPLETE_SENTENCE]") or response.startswith("[LOGS_COMPLETE]") or response.startswith("[CONTINUE_FROM_LOGS_STARTING_FROM_A_NEW_SENTENCE]"):
                return response
            else:
                print(
                    f"DEBUG: Unexpected LLM response format: {response[:500]}...")
                return "[ERROR] Unexpected LLM response format for continue_narrative_from_logs."
        except Exception as e:
            print(f"Error in continue_narrative_from_logs: {e}")
            return "[ERROR] " + str(e)


class LLMChunkedStoryGenerator(BaseStoryGenerator):
    """
    Generates a story by processing simulation logs in chunks, iteratively building the narrative.
    """

    def __init__(self, model, tone: str = None):
        self.llm = model
        self.tone = tone
        self.name = "LLMChunkedStoryGenerator"  # For error messages

    def _call_llm_for_story(self, prompt: str, max_tokens: int) -> str:
        """Helper function to make the LLM call with error handling."""
        try:
            story_generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 60,
                "max_output_tokens": max_tokens,
            }
            response = self.llm.generate_content(
                prompt, generation_config=story_generation_config)
            story_text = response.text.strip()
            return story_text

        except ResourceExhausted as e:
            print(f"[{self.name} Error]: LLM generation failed due to resource exhaustion: {e}. Waiting 10 seconds and retrying...")
            time.sleep(10)
            return self._call_llm_for_story(prompt, max_tokens)
        except GoogleAPICallError as e:
            print(
                f"[{self.name} Error]: Google API call failed: {e}. Waiting 10 seconds and retrying...")
            time.sleep(10)
            return self._call_llm_for_story(prompt, max_tokens)
        except Exception as e:
            error_message = f"[{self.name} Error]: LLM story generation failed: {e}"
            print(error_message)
            if 'response' in locals() and hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                feedback_message = f" (Safety Feedback: {response.prompt_feedback})"
                print(feedback_message)
            return f"[ERROR]: An unexpected error occurred: {e}"

    # ADDED: The refine_and_conclude_story method from LLMIterativeStoryGenerator
    def refine_and_conclude_story(self, current_story_so_far: str, agent_configs: list, narrative_goal: str) -> str:
        """
        Iteratively refines and attempts to conclude the story based on previous content.
        The LLM determines if it's complete or needs to continue.
        """
        print(
            "\n--- Refining Story and Checking for Conclusion (from Chunked Generator) ---")

        # Re-gather context as it's passed in each iteration
        character_intros = []
        for agent_conf in agent_configs:
            intro = f"- {agent_conf['name']}: {agent_conf['identity']}."
            character_intros.append(intro)
        characters_summary = "The characters involved were:\n" + \
            "\n".join(character_intros)

        tone_prompt = self.tone if self.tone else "Neutral"

        # The core iterative prompt
        prompt = f"""You are a master storyteller. You are currently reviewing a story in progress.

Narrative Premise/Goal:
{narrative_goal if narrative_goal else "An emergent narrative adventure."}

Tone: {tone_prompt}

{characters_summary}

**Story So Far (Read this carefully):**
{current_story_so_far}

---

**Your Task & Decision Process:**

1.  **Review the "Story So Far":**
    *   Does it feel like it has reached a compelling, natural, and conclusive narrative ending that aligns with the "Narrative Premise/Goal"?.

2.  **Determine Action:**
    *   **IF the story is NOT yet complete OR needs further development/elaboration based on remaining logs or to reach a proper conclusion:**
        *   Begin your response with the tag: `[CONTINUE_WRITING]`
        *   Then, write the *next coherent segment* of the story, picking up exactly where the "Story So Far" left off.
        *   Continue to incorporate any remaining logs, or start building towards a satisfying conclusion if logs are exhausted.
        *   Ensure new content is consistent with established characters and world.
    *   **IF the story IS complete and has reached a satisfactory, conclusive ending:**
        *   Begin your response with the tag: `[STORY_COMPLETE]`
        *   Then, provide the *final, polished version* of the entire story. This should be the "Story So Far" potentially with a final concluding paragraph or two. Ensure it flows perfectly as a complete work.
---

**General Storytelling Guidelines:**
- **Narrative Expansion:** Elaborate upon and contextualize events. Do not simply list them or present only dialogue.
- **Show, Don't Tell:** Expand descriptions of settings, character expressions, body language, actions, and incorporate sensory details.
- **Character Depth:** Deepen character insight by inferring their thoughts, feelings, and motivations, consistent with their personalities.
- **Pacing & Flow:** Ensure smooth transitions, varied sentence structure, and overall readability.
- **Avoid Repetition:** Ensure variety in language and sentence structure.

Your Response (starting with either [CONTINUE_WRITING] or [STORY_COMPLETE] ):
"""
        if config.SIMULATION_MODE == 'debug':
            print("--- Story Refinement/Conclusion Prompt ---")
            print(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
            print("-----------------------------")

        # Set a high max_output_tokens because the model might either append a short segment
        # or output the entire story if it determines it's complete.
        response_text = self._call_llm_for_story(prompt, max_tokens=8192)

        if not response_text or "[ERROR]" in response_text:
            failure_message = response_text if "[ERROR]" in response_text else "The LLM produced an empty response or an error during refinement."
            print(failure_message)
            return failure_message  # Return error to stop iteration

        # Parse the response based on the tags
        if response_text.startswith("[CONTINUE_WRITING]"):
            segment = response_text[len("[CONTINUE_WRITING]"):].strip()
            print("LLM chose to CONTINUE WRITING.")
            # Preserve tag for external loop to process
            return "[CONTINUE_WRITING]" + segment
        elif response_text.startswith("[STORY_COMPLETE]"):
            final_story = response_text[len("[STORY_COMPLETE]"):].strip()
            print("LLM determined story is COMPLETE.")
            # Preserve tag for external loop to process
            return "[STORY_COMPLETE]" + final_story
        else:
            print(
                "WARNING: LLM did not start response with expected tag. Treating as continuation.")
            # Default to continue if no tag
            return "[CONTINUE_WRITING]" + response_text

    # Overriding the abstract method with a different signature, consistent with original file's implementation

    def generate_story(self, log_file_path: str, agent_configs: list, narrative_goal: str, chunk_size: int = 10) -> str:
        """
        Generates a story by processing simulation logs in chunks, iteratively building the narrative.
        After building the draft from chunks, it uses an iterative refinement process to conclude.

        Args:
            log_file_path: Path to the simulation event log file.
            agent_configs: List of agent configurations.
            narrative_goal: The overarching narrative goal.
            chunk_size: Number of log events per processing chunk.
            max_story_context_tokens: Maximum tokens from the 'story so far' to include in prompt.
                                    This helps manage context window limits.

        Returns:
            A string containing the generated story.
        """
        print("\n--- Generating Story from Chunks of Simulation Logs ---")

        # 1. Gather Character Information
        character_intros = []
        for agent_conf in agent_configs:
            intro = f"- {agent_conf['name']}: {agent_conf['identity']}."
            character_intros.append(intro)
        characters_summary = "The characters involved were:\n" + \
            "\n".join(character_intros)

        tone_prompt = self.tone if self.tone else "Neutral"

        # 2. Read All Events from File
        all_raw_events = []
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                all_raw_events = [line.strip() for line in f if line.strip()]
            if not all_raw_events:
                print("No events found in the log file. Cannot generate story.")
                return "No events were logged during the simulation, so no story could be generated."
            print(f"Read {len(all_raw_events)} events from {log_file_path}")
        except FileNotFoundError:
            print(
                f"Error: The event log file '{log_file_path}' was not found.")
            return f"Error: Event log file '{log_file_path}' not found."
        except Exception as e:
            print(f"Error reading event log file '{log_file_path}': {e}")
            return f"Error reading event log: {e}"

        full_story_draft = ""
        num_chunks = (len(all_raw_events) + chunk_size - 1) // chunk_size

        # 3. Process Chunks to build initial draft
        for i in range(num_chunks):
            start_index = i * chunk_size
            end_index = min((i + 1) * chunk_size, len(all_raw_events))
            current_chunk_events = all_raw_events[start_index:end_index]

            events_text = "\n".join(current_chunk_events)

            # # Truncate story so far to fit context window
            # # A simple way to truncate is by characters, assuming ~4 chars per token.
            # # This is a rough estimate; for better accuracy, use a proper tokenizer.
            # truncated_story_context = full_story_draft
            # if len(truncated_story_context) > max_story_context_tokens * 4:  # Convert tokens to chars
            #     truncated_story_context = truncated_story_context[-(
            #         max_story_context_tokens * 4):]
            #     # Try to cut at a sentence boundary for better context
            #     last_period_index = truncated_story_context.rfind('.')
            #     if last_period_index != -1:
            #         truncated_story_context = truncated_story_context[last_period_index+1:].strip(
            #         )
            #     truncated_story_context = "... " + truncated_story_context  # Indicate truncation

            chunk_prompt = f"""You are a master storyteller. You are currently building a narrative based on simulation logs, segment by segment.

Narrative Premise/Goal:
{narrative_goal if narrative_goal else "An emergent narrative adventure."}

Tone: {tone_prompt}

{characters_summary}

Story So Far (for context and continuity; DO NOT rewrite, just append to it smoothly. This is the narrative that has already been generated):
{full_story_draft if full_story_draft else "No story written yet. Start with an engaging introduction for the overall narrative."}

Events for this segment (These are the *next* chronological events from the simulation log. Focus on narrating THESE events and seamlessly integrating them into the story):
{events_text}

Instructions:
- Write ONLY the NEXT narrative segment. It must flow directly and coherently from the "Story So Far".
- For the first segment, include an engaging introduction that sets the stage and introduces characters, consistent with the first events.
- For subsequent segments, seamlessly continue the narrative from the last sentence of the "Story So Far".
- **Elaborate, describe, and immerse:**
    - Show, don't tell: Describe settings, character expressions, body language, sensory details (sights, sounds, smells).
    - Infer character thoughts, feelings, and motivations *as they relate to these events*.
    - Expand on actions: Instead of "moved to kitchen," describe *how* they moved, their purpose, and what they encountered.
- Maintain the established tone and narrative style.
- Do NOT add a conclusion at this stage. Just continue the story.
- Do NOT re-state events directly as they appear in the logs; transform them into vivid prose.
- Ensure smooth transitions between scenes and events within this segment and from the previous story.
- End your segment at a natural break, ready for the next part to be appended.

Your Story Segment:
"""
            print(
                f"\n--- Generating Story Segment {i+1}/{num_chunks} (Events {start_index+1}-{end_index}) ---")
            if config.SIMULATION_MODE == 'debug':
                # Print a reasonable portion of the prompt for debugging
                debug_prompt_display_length = 1500
                print(chunk_prompt[:debug_prompt_display_length] + "..." if len(
                    chunk_prompt) > debug_prompt_display_length else chunk_prompt)
                print("-" * 20)

            # Allocate tokens for each segment
            segment = self._call_llm_for_story(chunk_prompt, max_tokens=2048)
            if "[ERROR]" in segment:
                print(
                    f"Error generating segment {i+1}. Stopping chunked generation early.")
                append_to_log_file("simulation_story_chunked.txt",
                                   "\n--- PARTIAL STORY (Error during chunked generation) ---\n")
                append_to_log_file(
                    "simulation_story_chunked.txt", full_story_draft)
                append_to_log_file("simulation_story_chunked.txt",
                                   f"\n[ERROR occurred at chunk {i+1}: {segment}]\n")
                # Return what we have or the error
                return full_story_draft if full_story_draft else segment

            # Ensure the segment starts with a new sentence if the previous one ended abruptly
            # or if the LLM provided an introduction. This is for robustness.
            clean_segment = segment.strip()
            # Logic to ensure clean appending between segments
            if full_story_draft and not full_story_draft.endswith(('.', '!', '?')) and clean_segment and clean_segment[0].isupper():
                # If previous story didn't end with punctuation but new one starts with capital,
                # force a period for better flow.
                full_story_draft += ". "
            elif full_story_draft and not full_story_draft.endswith(('.', '!', '?')) and clean_segment and not clean_segment[0].isupper():
                # If previous story didn't end with punctuation and new one doesn't start capital,
                # it's likely a sentence continuation (good). Add a space.
                full_story_draft += " "
            full_story_draft += clean_segment
            print(
                f"Segment {i+1} generated. Current story length: {len(full_story_draft.split())} words.")
            # Use configured delay to manage API rate limits
            time.sleep(2)

        # Log the draft after chunking is complete
        append_to_log_file("Initial_Story_Draft.txt",
                           "\n--- Story Draft After Chunked Processing ---\n")
        append_to_log_file("Initial_Story_Draft.txt", full_story_draft)
        append_to_log_file("Initial_Story_Draft.txt",
                           "------------------------------------------\n")

        return full_story_draft
