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
    "temperature": 1.0,  # User's desired higher temperature
    "top_p": 0.95,
    "top_k": 50,         # Adjusted for higher temp
    "max_output_tokens": 128,  # Slightly more room for creative plans
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
    "max_output_tokens": 4000,  # Allow for a longer story
}

# For Director (balanced for decision making and subtle influence)
DIRECTOR_GEN_CONFIG = {
    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 128,
}

# For Agent Memory Reflection (synthesis, concise, accurate)
AGENT_REFLECTION_GEN_CONFIG = {
    "temperature": 0.6,  # More focused for reflection
    "top_p": 0.95,
    "top_k": 30,
    "max_output_tokens": 300,  # Enough for a few insights
}

# Simulation Settings
MAX_RECENT_EVENTS = 15
MAX_MEMORY_TOKENS = 1000  # Increased memory capacity
SIMULATION_MAX_STEPS = 30


# --- World Definition ---
WEATHER = "Warm, quiet afternoon"
KNOWN_LOCATIONS_DATA = {
    "Abuelo Ceibo": {
        "description": "A colossal tree with deep, sprawling roots and a wide canopy that casts a significant shadow, central to the conflict between Mateo and Elena. Its bark is gnarled, bearing the marks of time.",
        "exits_to": ["Mateo's Farm Land", "Elena's Homestead"],
        "properties": {
            "contains": [
                {"object": "boundary markers", "state": "old, weathered",
                    "optional_description": "Small, worn stones indicating the property line, almost swallowed by the encroaching grass."
                 }
            ]
        }
    },
    "Mateo's House": {
        "description": "Sprawling fields of meticulously tended crops stretch towards the horizon, showcasing Mateo's modern agricultural practices. The hum of distant machinery occasionally breaks the calm, hinting at ongoing work.",
        "exits_to": ["Abuelo Ceibo", "Valley"],
        "properties": {
            "contains": [
                {"object": "tractor", "state": "parked and well-maintained",
                    "optional_description": "A powerful, clean tractor, a symbol of Mateo's efficient, modern farming methods, standing ready for use."
                 },
                {"object": "sacks of new seeds", "state": "stacked neatly",
                    "optional_description": "Durable sacks filled with a promising new variety of crop seeds, representing Mateo's aspirations for a more profitable harvest."
                 }
            ]
        }
    },
    "Elena's House": {
        "description": "A quaint, traditional farmhouse nestled amidst a flourishing herbal garden and an ancient well. The atmosphere is one of timeless tranquility, steeped in history, with the gentle buzz of bees around the flowers.",
        "exits_to": ["Abuelo Ceibo", "Valley"],
        "properties": {
            "contains": [
                {"object": "old wooden bench", "state": "weathered but sturdy",
                    "optional_description": "A simple, well-worn wooden bench positioned under the shade of a smaller fruit tree, a place for quiet contemplation or storytelling."
                 },
                {"object": "herbal garden", "state": "vibrant and fragrant",
                    "optional_description": "Elena's small, vibrant garden bursting with a diverse array of medicinal herbs and traditional vegetables, their scents mingling in the air."
                 }
            ]
        }
    },
    "Valley": {  # Adding a general valley location as suggested previously
        "description": "The surrounding fertile valley, cradling the farms and homesteads. It's a place where ancient traditions subtly influence the land, but also where modern pressures are keenly felt.",
        # Conceptual exits
        "exits_to": ["Mateo's House", "Elena's House", "Abuelo Ceibo"]
    }
}


# --- Component Selection ---
AGENT_MEMORY_TYPE = "ShortLongTMemoryIdentityOnly"
AGENT_PLANNING_TYPE = "SimplePlanningIdentityOnly"
ACTION_RESOLVER_TYPE = "LLMActionResolverWithReason"
EVENT_PERCEPTION_MODEL = "DirectEventDispatcher"
STORY_GENERATOR_TYPE = "LLMLogStoryGenerator"

# --- Narrative / Scenario ---
NARRATIVE_GOAL = """The story should depict the escalating conflict between Mateo's pragmatic need to cut the ancient Abuelo Ceibo for agricultural expansion and Elena's deep, traditional conviction to protect it. It must build tension as both characters present their cases and take sides, leading to a critical confrontation at the tree's base. The narrative should then resolve this fundamental dispute, either through a negotiated compromise that allows both sides to find common ground, or a crucial discovery that redefines the tree's inherent value, ultimately guiding the characters towards a shared path forward."""
TONE = "Reflective, empathetic, and slightly somber, focusing on the clash between tradition and progress, the weight of responsibility, and the deep connection to the land. The narrative should explore the emotional and practical complexities of the characters' positions, aiming for a resolution that honors the spirit of the valley and its inhabitants."
agent_configs = [
    {
        "name": "Mateo",
        "identity": "Young, pragmatic, and with a more modern vision of agriculture. Mateo has recently inherited his father's land and is eager to implement new techniques to improve productivity and secure his family's future. He is hardworking and respectful, but also views things from a perspective of efficiency and necessity. He feels the weight of responsibility and economic pressure. His objective is to expand his cultivation area to plant a new, more profitable type of crop, for which he considers the land occupied by the Abuelo Ceibo vital. Furthermore, he fears that the tree's old branches might be dangerous.",
        "initial_location": "Mateo's House",
        "gender": "",
        "personality": "",
        "initial_goals": "",
        "background": "",
        "initial_context": "Mateo surveyed his fields, the afternoon sun glinting off the newly turned earth. His gaze drifted to the immense Abuelo Ceibo at the property line, its sprawling canopy a dark silhouette against the sky. The familiar pang of economic pressure and the weight of his family's future gnawed at him. The tree stood directly in the path of his plans for a new, profitable crop, and its old branches seemed a constant threat. He knew he had to talk to Elena today, despite the heavy certainty of conflict."
    },
    {
        "name": "Elena",
        "identity": "An elder, widowed woman with a profound spiritual and sentimental connection to the land and its traditions. Elena has lived her entire life beside the Abuelo Ceibo, just as her parents and grandparents did. For her, the tree is not merely wood and leaves, but a living being with history, a guardian, and a symbol of her family's and the valley's resilience. She is wise, a bit stubborn, and perceives the world at a slower, more contemplative pace. Her objective is to protect the Abuelo Ceibo at all costs, considering cutting it down an act of betrayal.",
        "initial_location": "Elena's House",
        "gender": "",
        "personality": "",
        "initial_goals": "",
        "background": "",
        "initial_context": "Elena sat on her porch, sipping herbal tea, watching the changing light on the Abuelo Ceibo. Its ancient branches, familiar as her own skin, swayed gently in the breeze. She felt a deep sense of peace, but also a growing unease. Mateo had been looking at the tree differently lately, and she knew the unspoken threat that hung in the air. This tree was more than just wood; it was the history of her family, the guardian of the valley, and she would protect it with every fiber of her being."
    }
]


SIMULATION_MODE = 'debug'  # Keep debug for testing
