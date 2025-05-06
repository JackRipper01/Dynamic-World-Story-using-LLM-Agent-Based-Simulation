# config.py
import os
from dotenv import load_dotenv

# Load API Key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError(
        "Gemini API Key not found. Make sure it's set in the .env file.")

# LLM Generation Settings
GENERATION_CONFIG = {
    "temperature": 1.3,
    "top_p": 0.95,
    "top_k": 50,
    "max_output_tokens": 200,  # Increased to allow for more detailed responses
}

# LLM Safety Settings
# SAFETY_SETTINGS = [
#     {"category": "HARM_CATEGORY_HARASSMENT",
#         "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
#     {"category": "HARM_CATEGORY_HATE_SPEECH",
#         "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
#     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
#         "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
#     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
#         "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
# ]


# Model Name
MODEL_NAME = "gemini-2.0-flash-lite"

# Simulation Settings
MAX_RECENT_EVENTS = 15
MAX_MEMORY_TOKENS = 600
SIMULATION_MAX_STEPS = 30

# World Settings
KNOWN_LOCATIONS = {
    "Park": "A wide open park area with some trees.",
    "Shelter": "A simple wooden shelter.",
    "Forest Edge": "The edge of a dark forest."
}

# Agent Settings
DEFAULT_PERSONALITIES = {
    "Alice": "curious, slightly anxious, observant",
    "Bob": "calm, pragmatic, speaks plainly"
}
# --- Component Selection ---
# Choose the implementations for different parts of the simulation
# (Allows easy switching for experiments)

# Options: "SimpleMemory", "VectorMemory" (future)
AGENT_MEMORY_TYPE = "ShortLongTMemory"
# Options: "GeminiThinker", "RuleBasedThinker" (future)
AGENT_PLANNING_TYPE = "GeminiThinker"

# Action Resolution Strategy (Crucial for your experiments!)
# Options: "LLMResolver", "StructuredValidator", "Passthrough", "HybridRefine" (future)
ACTION_RESOLVER_TYPE = "LLMResolver"  # Start with the current LLM-based logic

# Event Perception Model (How agents receive events)
# Options: "DirectDispatch", "SummaryContext" (old way)
EVENT_PERCEPTION_MODEL = "DirectEventDispatcher"

NARRATIVE_GOAL = "Create a humorous story about two strangers with conflicting goals who must eventually cooperate."
# DIRECTOR_COOLDOWN_MIN = 2 # Example: Could make cooldown configurable
# DIRECTOR_COOLDOWN_MAX = 5

# agent_configs = [
#     {"name": "Alice",
#      "personality": "creative, adventurous, slightly mischievous, believes in supernatural phenomena",
#      "gender": "woman",
#      "initial_location": "Forest Edge",
#      "initial_goals": ["Find magical ingredients in the forest for a special potion",
#                        "Convince someone to help explore the deeper parts of the forest",
#                        "Establish a comfortable base camp"]},

#     {"name": "Bob",
#      "personality": "practical, skeptical, organized, values comfort and security above all",
#      "gender": "man",
#      "initial_location": "Forest Edge",
#     "initial_goals": ["Find a reliable source of food and water."]}
# ]
agent_configs = [
    # --- The Investigator/Observer ---
    {
        "name": "Alice",
        "personality": "An observant and creative individual fascinated by puzzles and hidden motives, driven by a mix of fear and morbid curiosity to uncover the truth.",
        "gender": "woman",
        "initial_location": "Shelter",
        "initial_goals": [  # Goals AFTER discovering the body
            "Figure out what *really* happened to David.",
            "Observe everyone's reactions and inconsistencies closely.",
            "Look for any unusual clues.",
            "Ensure my own safety without appearing overly suspicious."
        ],
        "background": [
            "You are Alice. A storm forced you into this shelter with Bob, Charlie, Eve, and David. ",
            "David has been found murdered. You are trapped with the others, one of whom is the killer. Your goal is to figure out who, observing carefully.",
        ],
    },

    # --- The Secret Murderer ---
    {
        "name": "Bob",
        "personality": "Appears practical and safety-focused but is secretly ruthless and desperate, skillfully acting innocent to conceal his guilt as the murderer.",
        "gender": "man",
        "initial_location": "Shelter",
        "initial_goals": [  # Goals AFTER the murder (HIS secret goals)
            "Convincingly act shocked and scared about David's death.",
            "Avoid suspicion at all costs; deflect questions smoothly.",
            "Subtly steer suspicion towards someone else if possible.",
            "Find any opportunity to destroy evidence or escape.",
            "Feigned Goal: Cooperate to appear innocent."
        ],
        "background": [
            "You are Bob. You killed David in this shelter shortly before he was discovered. No one saw you. ",
            "You are trapped with Alice, Charlie, and Eve. You MUST appear innocent; act shocked and scared, but inwardly focus on deflecting suspicion and surviving."
        ],
    },

    # --- The Logical Analyst ---
    {
        "name": "Charlie",
        "personality": "A calm and analytical thinker who approaches the crisis with logical precision, focusing on systematically gathering evidence to identify the killer.",
        "gender": "man",
        "initial_location": "Shelter",
        "initial_goals": [  # Goals AFTER discovering the body
            "Establish the basic facts: time, cause, potential motives.",
            "Question everyone systematically.",
            "Secure the immediate area.",
            "Identify the most logical suspect based on opportunity/motive."
        ],
        "background": [
            "You are Charlie. A storm trapped you in this shelter with Alice, Bob, Eve, and David, who has just been found murdered. Rely on logic and observation to systematically investigate and find the killer before panic takes over."
        ],
    },

    # --- The Empathetic/Nervous One ---
    {
        "name": "Eve",
        "personality": "A highly empathetic and anxious person who reacts emotionally to the tense situation, seeking safety while trying to read others' feelings for clues.",
        "gender": "woman",
        "initial_location": "Near Riverbank (seeking shelter)",
        "initial_goals": [  # Goals AFTER discovering the body
            "Find out who the killer is immediately so I can feel safe.",
            "Try to understand how everyone is feeling; look for emotional tells.",
            "Seek protection or ally with someone trustworthy.",
            "Express fear and urge action."
        ],
        "background": [
            "You are Eve. A storm trapped you in this shelter with Alice, Bob, Charlie, and David - but David has been murdered! You are terrified and trapped with the killer; focus on reading emotions, finding who seems suspicious, and staying safe."
        ],
    }
]
SIMULATION_MODE = 'debug'
