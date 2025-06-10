# story_from_chunks.py
import config
import time
# Assuming create_llm_instance is in main.py or a utility file accessible.
# If not, you'll need to define how your LLM model is initialized here.

try:
    from main import create_llm_instance
except ImportError:
    print("Warning: 'create_llm_instance' not found in main.py. Please ensure it's accessible or define LLM initialization here.")

from story_generator import LLMChunkedStoryGenerator
import config  # Assuming config.py has necessary settings

# Create an instance of StoryGenerator
llm = create_llm_instance(
    config.MODEL_NAME,
    config.STORY_GENERATOR_GEN_CONFIG,
    purpose="Chunked Story Generator"
)

story_generator = LLMChunkedStoryGenerator(llm, config.TONE)

# Define parameters for chunked generation
# Make sure this file exists and contains events
log_file_to_process = "mateo vs elena logs.txt"
chunk_size = 64  # Number of log entries per chunk to process at a time
# Max tokens from the 'story so far' to pass to the LLM for context

print(
    f"Starting chunked story generation for '{log_file_to_process}' with chunk size {chunk_size}...")
print(
    f"--- PHASE 1: Generating Initial Story Draft by Chunking Logs from '{log_file_to_process}' ---")

final_story = story_generator.generate_story(
    log_file_path=log_file_to_process,
    agent_configs=config.agent_configs,
    narrative_goal=config.NARRATIVE_GOAL,
    chunk_size=chunk_size
)

print("\n--- Initial Story Draft Generation Complete ---")
print("The initial draft has been saved to 'Initial_Story_Draft.txt'.")
print("To proceed, run the refinement script: python refine_story.py")
