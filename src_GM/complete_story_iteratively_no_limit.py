# In complete_story_iteratively_no_limit.py

import time
from main import create_llm_instance
from logs import append_to_log_file
from story_generator import LLMIterativeStoryGenerator
from config import agent_configs
import config

# Create an instance of StoryGenerator
llm = create_llm_instance(
    config.MODEL_NAME,
    config.STORY_GENERATOR_GEN_CONFIG,
    purpose="Story Generator"
)

story_generator = LLMIterativeStoryGenerator(llm, config.TONE)

final_story = ""
current_story_draft = ""
max_log_conversion_iterations = 10
max_refinement_iterations = 10
log_conversion_iteration_count = 0
refinement_iteration_count = 0

try:
    with open("murderer_case_logs.txt", "r", encoding="utf-8") as f:
        full_log_content = f.read()
except FileNotFoundError:
    print(f"Error: Log file not found at {config.LOG_FILE_PATH}. Exiting.")
    exit()
except Exception as e:
    print(f"Error reading log file: {e}. Exiting.")
    exit()

print("\n--- Generating Initial Story Segment from Logs ---")
current_story_draft = story_generator.generate_initial_story_draft(
    log_file_path="murderer_case_logs.txt",
    agent_configs=config.agent_configs,
    narrative_goal=config.NARRATIVE_GOAL
)

if "[ERROR]" in current_story_draft:
    print("Initial story segment generation failed. Exiting.")
else:
    
    append_to_log_file("Initial_Story_Draft.txt",current_story_draft)
    
    print("\n--- Iteratively Extending Story to Cover All Logs ---")
    while log_conversion_iteration_count < max_log_conversion_iterations:
        log_conversion_iteration_count += 1
        print(
            f"\n--- Log Conversion Iteration {log_conversion_iteration_count} ---")

        response_from_llm = story_generator.continue_narrative_from_logs(
            # LLM sees the *entire* accumulated story
            current_story_so_far=current_story_draft,
            full_log_content=full_log_content,
            agent_configs=config.agent_configs,
            narrative_goal=config.NARRATIVE_GOAL
        )

        if "[ERROR]" in response_from_llm:
            print("Error during log conversion. Stopping log conversion iteration.")
            break

        if response_from_llm.startswith("[LOGS_COMPLETE]"):
            print(
                f"Logs successfully converted to narrative after {log_conversion_iteration_count} iterations.")
            break
        elif response_from_llm.startswith("[CONTINUE_FROM_LOGS_STARTING_FROM_INCOMPLETE_SENTENCE]"):
            new_segment = response_from_llm[len(
                "[CONTINUE_FROM_LOGS_STARTING_FROM_INCOMPLETE_SENTENCE]"):].strip()
            current_story_draft += " " + new_segment
            print(
                f"Initial Story Draft continued to cover more logs. Current length: {len(current_story_draft.split())} words.")
            append_to_log_file("Initial_Story_Draft.txt", " " + new_segment)
        elif response_from_llm.startswith("[CONTINUE_FROM_LOGS_STARTING_FROM_A_NEW_SENTENCE]"):
            new_segment = response_from_llm[len(
                "[CONTINUE_FROM_LOGS_STARTING_FROM_A_NEW_SENTENCE]"):].strip()
            current_story_draft += "\n" + new_segment
            print(
                f"Initial Story Draft continued to cover more logs. Current length: {len(current_story_draft.split())} words.")
            append_to_log_file("Initial_Story_Draft.txt", "\n" + new_segment)
        else:
            print(
                "Unexpected response format during log conversion. Stopping log conversion.")
            break

        time.sleep(10)

    if log_conversion_iteration_count >= max_log_conversion_iterations:
        print(
            f"Max log conversion iterations ({max_log_conversion_iterations}) reached. Logs may not be fully covered.")

    # Proceed to the existing story refinement loop
    print("\n--- Entering Story Refinement Phase ---")
    # while refinement_iteration_count < max_refinement_iterations:
    #     refinement_iteration_count += 1
    #     print(
    #         f"\n--- Story Refinement Iteration {refinement_iteration_count} ---")

    #     response_from_llm = story_generator.refine_and_conclude_story(
    #         current_story_so_far=current_story_draft,
    #         agent_configs=config.agent_configs,
    #         narrative_goal=config.NARRATIVE_GOAL
    #     )

    #     if "[ERROR]" in response_from_llm:
    #         print("Error during story refinement. Stopping iteration.")
    #         final_story = current_story_draft
    #         break

    #     if response_from_llm.startswith("[STORY_COMPLETE]"):
    #         final_story = current_story_draft
    #         print(
    #             f"Story completed after {refinement_iteration_count} refinement iterations.")
    #         break
    #     elif response_from_llm.startswith("[CONTINUE_WRITING]"):
    #         new_segment = response_from_llm[len("[CONTINUE_WRITING]"):].strip()
    #         current_story_draft += "\n" + new_segment
    #         print("Story continued. Current length:",
    #               len(current_story_draft.split()))
    #     else:
    #         print("Unexpected response format during refinement. Stopping iteration.")
    #         final_story = current_story_draft
    #         break

    #     time.sleep(10)

    # if refinement_iteration_count >= max_refinement_iterations and not final_story:
    #     print(
    #         f"Max refinement iterations ({max_refinement_iterations}) reached. Story may be incomplete.")
    #     final_story = current_story_draft

    # print("\n--- FINAL GENERATED STORY ---")
    # print(final_story)
    # print("-----------------------------\n")

    # try:
    #     with open("simulation_story.txt", "w", encoding="utf-8") as f:
    #         f.write(f"Simulation Goal: {config.NARRATIVE_GOAL}\n")
    #         f.write("Characters:\n")
    #         for ac in config.agent_configs:
    #             f.write(f"  - {ac['name']}: {ac['identity']}\n")
    #         f.write("\n--- FINAL STORY ---\n")
    #         f.write(final_story)
    #     print("\n(Final story also saved to simulation_story.txt)")
    # except Exception as e:
    #     print(f"\n[Error] Could not save final story to file: {e}")
