# config.py
import os
from dotenv import load_dotenv

# Load API Key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found. Make sure it's set in the .env file.")

# LLM Generation Settings
GENERATION_CONFIG = {
  "temperature": 0.9,
  "top_p": 0.95,
  "top_k": 50,
  "max_output_tokens": 150,
}

# LLM Safety Settings
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Model Name
MODEL_NAME = "gemini-1.5-flash" # Or "gemini-1.5-pro"

# Simulation Settings
MAX_RECENT_EVENTS = 15 # How many events world remembers
MAX_MEMORY_TOKENS = 600 # Rough limit for agent memory string
SIMULATION_MAX_STEPS = 30

# World Settings
KNOWN_LOCATIONS = {
    "Park": "A wide open park area with some trees.",
    "Shelter": "A simple wooden shelter.",
    "Forest Edge": "The edge of a dark forest."
}

# Agent Settings (Example Personalities)
DEFAULT_PERSONALITIES = {
    "Alice": "curious, slightly anxious, observant",
    "Bob": "calm, pragmatic, speaks plainly"
}