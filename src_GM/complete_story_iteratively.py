from main import create_llm_instance
from story_generator import LLMIterativeStoryGenerator
from config import agent_configs
import config


# Create an instance of StoryGenerator
llm = create_llm_instance(
    config.MODEL_NAME,
    config.STORY_GENERATOR_GEN_CONFIG,
    purpose="Story Generator"
)

story_generator = LLMIterativeStoryGenerator(llm,config.TONE)

final_story = ""
current_story_draft = ""
max_iterations = 5  # Safety break to prevent infinite loops
iteration_count = 0

# STEP 1: Generate the initial draft
current_story_draft = story_generator.generate_initial_story_draft(
    log_file_path="simulation_log.txt",
    agent_configs=config.agent_configs,
    narrative_goal=config.NARRATIVE_GOAL
)

if "[ERROR]" in current_story_draft:
        print("Initial story generation failed. Exiting.")
else:
    # STEP 2: Enter the iteration loop
    while iteration_count < max_iterations:
        iteration_count += 1
        print(f"\n--- Iteration {iteration_count} of Story Refinement ---")

        response_from_llm = story_generator.refine_and_conclude_story(
            current_story_so_far=current_story_draft,
            log_file_path="simulation_log.txt",
            agent_configs=config.agent_configs,
            narrative_goal=config.NARRATIVE_GOAL
        )

        if "[ERROR]" in response_from_llm:
            print("Error during story refinement. Stopping iteration.")
            final_story = current_story_draft # Use the last good draft
            break

        if response_from_llm.startswith("[STORY_COMPLETE]"):
            final_story = response_from_llm[len("[STORY_COMPLETE]"):].strip()
            print(f"Story completed after {iteration_count} iterations.")
            break
        elif response_from_llm.startswith("[CONTINUE_WRITING]"):
            new_segment = response_from_llm[len("[CONTINUE_WRITING]"):].strip()
            current_story_draft += "\n" + new_segment # Append new segment
            print("Story continued. Current length:", len(current_story_draft.split()))
        else:
            # Fallback if no tag was found, assume it's a continuation
            print("Unexpected LLM response format, assuming continuation.")
            current_story_draft += "\n" + response_from_llm.strip()

    if iteration_count >= max_iterations and not final_story:
        print(f"Max iterations ({max_iterations}) reached. Story may be incomplete.")
        final_story = current_story_draft # Use the last state as final

    print("\n--- FINAL GENERATED STORY ---")
    print(final_story)
    print("-----------------------------\n")

    # Save the final story
    try:
        with open("simulation_story.txt", "w", encoding="utf-8") as f:
            f.write(f"Simulation Goal: {config.NARRATIVE_GOAL}\n")
            f.write("Characters:\n")
            for ac in config.agent_configs:
                f.write(f"  - {ac['name']}: {ac['identity']}\n")
            f.write("\n--- FINAL STORY ---\n")
            f.write(final_story)
        print("\n(Final story also saved to simulation_story.txt)")
    except Exception as e:
        print(f"\n[Error] Could not save final story to file: {e}")
