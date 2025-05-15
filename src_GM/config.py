# config.py
import os
from dotenv import load_dotenv

# Load API Key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError(
        "Gemini API Key not found. Make sure it's set in the .env file.")
    
# Model Name
MODEL_NAME = "gemini-2.0-flash-lite"  # "gemini-pro"

# LLM Generation Settings
GENERATION_CONFIG = {
    "temperature": 1.3,
    "top_p": 0.95,
    "top_k": 50,
    "max_output_tokens": 200,  # Increased to allow for more detailed responses
}


# --- LLM Generation Settings for Different Components ---

# For Agent Planning (more creative)
AGENT_PLANNING_GEN_CONFIG = {
    "temperature": 1.5,  # User's desired higher temperature
    "top_p": 0.95,
    "top_k": 60,         # Adjusted for higher temp
    "max_output_tokens": 250,  # Slightly more room for creative plans
}

# For Action Resolver (more logical, less creative)
ACTION_RESOLVER_GEN_CONFIG = {
    "temperature": 0.7,  # User's desired lower temperature
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 200,
}

# For Story Generator (creative, can be longer)
STORY_GENERATOR_GEN_CONFIG = {
    "temperature": 0.75,  # Balanced for storytelling
    "top_p": 0.95,
    "top_k": 60,
    "max_output_tokens": 2000,  # Allow for a longer story
}

# For Director (balanced for decision making and subtle influence)
DIRECTOR_GEN_CONFIG = {
    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 150,
}

# For Agent Memory Reflection (synthesis, concise, accurate)
AGENT_REFLECTION_GEN_CONFIG = {
    "temperature": 0.6,  # More focused for reflection
    "top_p": 0.85,
    "top_k": 30,
    "max_output_tokens": 300,  # Enough for a few insights
}

# Simulation Settings
MAX_RECENT_EVENTS = 15
MAX_MEMORY_TOKENS = 1000  # Increased memory capacity
SIMULATION_MAX_STEPS = 30

# --- World Definition ---
KNOWN_LOCATIONS_DATA = {
    "EscapeRoom": {
        "description": "A plain, windowless room. The walls are bare, and the only prominent feature is a single door.",
        # The conceptual exit, requires the door to be open
        "exits_to": ["Corridor"],
        "properties": {
            "contains": [
                {"object": "Room Door", "state": "closed and unlocked",
                    "optional_description": "A standard wooden door. It appears to be the only way out.",
                    # Link to the corresponding door object in the Corridor
                    "linked_to": {"location": "Corridor", "object_key": "Corridor Access Door"}
                 },
                {"object": "small table", "state": "empty",
                    "optional_description": "A dusty small table in one corner."},
                {"object": "flickering lightbulb", "state": "dimly illuminating the room",
                    "optional_description": "An old lightbulb hanging from the ceiling, casting long shadows."}
            ]
        }
    },

    "Corridor": {
        "description": "A long, narrow corridor stretching into the distance. It feels a bit drafty here.",
        "exits_to": ["EscapeRoom"],  # Allows returning to the room
        "properties": {
            "contains": [
                {"object": "Corridor Access Door", "state": "closed and unlocked",  # Initial state matches Room Door
                 "optional_description": "The door leading back into the room you (presumably) just exited.",
                 # Link back to the corresponding door object in the EscapeRoom
                 "linked_to": {"location": "EscapeRoom", "object_key": "Room Door"}
                 }
            ]
        }
    }
}


# --- Component Selection ---
AGENT_MEMORY_TYPE = "ShortLongTMemory"
AGENT_PLANNING_TYPE = "GeminiThinker"
ACTION_RESOLVER_TYPE = "LLMResolver"
EVENT_PERCEPTION_MODEL = "DirectEventDispatcher"
STORY_GENERATOR_TYPE = "LLMLogStoryGenerator"

# --- Narrative / Scenario ---
NARRATIVE_GOAL = "Franco seeks guidance from the cheerful Dr. Piad for his stressful thesis work in the lab."

agent_configs = [
    {
        "name": "Alex",
        "personality": "Pragmatic and observant.",
        "gender": "woman", 
        "initial_location": "EscapeRoom",
        "initial_goals": [
            "Find a way out of this room.",
        ],
        "background": [
            "You suddenly find yourself in an unfamiliar, plain room with one other person.",
            "You have no memory of arriving here.",
        ],
    },
    {
        "name": "Ben",
        "personality": "Action-oriented and somewhat impatient.",
        "gender": "man",
        "initial_location": "EscapeRoom",
        "initial_goals": [
            "Get out of this room as quickly as possible.",
        ],
        "background": [
            "You've woken up in a strange, featureless room. Another person is here with you.",
        ],
    },
]
SIMULATION_MODE = 'debug'  # Keep debug for testing
