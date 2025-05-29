from django import conf
from main import create_llm_instance
from story_generator import LLMIterativeStoryGenerator,LLMLogStoryGenerator
from config import agent_configs
import config


# Create an instance of StoryGenerator
llm = create_llm_instance(
    config.MODEL_NAME,
    config.STORY_GENERATOR_GEN_CONFIG,
    purpose="Story Generator"
)

story_generator =LLMLogStoryGenerator(llm)

story_generator.generate_story("simulation_logs.txt",config.agent_configs,config.NARRATIVE_GOAL,config.TONE)