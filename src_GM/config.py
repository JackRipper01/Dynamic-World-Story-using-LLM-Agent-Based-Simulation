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
    "temperature": 0.9,  # Director might benefit from slightly lower temp if too random
    "top_p": 0.95,
    "top_k": 50,
    "max_output_tokens": 150,
}

# LLM Safety Settings
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


# Model Name
MODEL_NAME = "gemini-1.5-flash"

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
AGENT_MEMORY_TYPE = "SimpleMemory"
# Options: "GeminiThinker", "RuleBasedThinker" (future)
AGENT_PLANNING_TYPE = "GeminiThinker"

# Action Resolution Strategy (Crucial for your experiments!)
# Options: "LLMResolver", "StructuredValidator", "Passthrough", "HybridRefine" (future)
ACTION_RESOLVER_TYPE = "LLMResolver"  # Start with the current LLM-based logic

# Event Perception Model (How agents receive events)
# Options: "DirectDispatch", "SummaryContext" (old way)
EVENT_PERCEPTION_MODEL = "DirectDispatch"

NARRATIVE_GOAL = "Develop a beautiful and funny story."
# DIRECTOR_COOLDOWN_MIN = 2 # Example: Could make cooldown configurable
# DIRECTOR_COOLDOWN_MAX = 5

agent_configs = [
    {"name": "Alice", "personality": DEFAULT_PERSONALITIES.get(
        "Alice", "default")},
    {"name": "Bob", "personality": DEFAULT_PERSONALITIES.get(
        "Bob", "default")}
]
