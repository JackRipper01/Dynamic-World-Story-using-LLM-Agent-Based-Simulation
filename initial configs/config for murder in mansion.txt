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
WEATHER="STORMY"  
KNOWN_LOCATIONS_DATA = {
    "Study": {
        "description": "Lord Alistair Finch's private sanctuary, filled with antique maps, worn leather books, and the scent of old paper and pipe tobacco. It is the scene of the crime.",
        # Assume direct exit to the main gathering area
        "exits_to": ["Drawing Room"],
        "properties": {
            "contains": [
                {"object": "lord alistair finch body", "state": "dead",
                    "optional_description": "The body of Lord Alistair Finch lies face down near his desk, a dark stain spreading on his back."
                },
                {"object": "mahogany desk", "state": "slightly disturbed",
                    "optional_description": "A heavy, ornate desk. Papers are scattered near the edge, suggesting a hasty departure or a brief struggle before the fall."
                },
                {"object": "antique globe", "state": "finial missing",
                    "optional_description": "A large, floor-standing globe. The decorative, pointed metal finial at the top of the axis is missing."
                },
                {"object": "bookshelves", "state": "full of books",
                    "optional_description": "Floor-to-ceiling shelves overflowing with books on art, history, and obscure subjects."
                },
                {"object": "armchair", "state": "overturned",
                    "optional_description": "A heavy leather armchair lies on its side near the body."
                },
                {"object": "fireplace", "state": "dying embers",
                    "optional_description": "A large fireplace where a fire is slowly burning down to embers."
                },
                {"object": "window", "state": "closed and latched",
                    "optional_description": "A tall, mullioned window, securely closed and latched from the inside. Rain streaks down the panes."
                },
                {"object": "lord alistairs will", "state": "on desk",
                    "optional_description": "A folded legal document titled 'Last Will and Testament', resting prominently on the desk."
                },
                {"object": "art negotiation papers", "state": "on desk scattered",
                    "optional_description": "Documents and notes related to the potential sale of artworks, some scattered on the desk."
                }
            ]
        }
    },

    "Drawing Room": {
        "description": "A grand but slightly faded room used for entertaining guests. Sumptuous furniture and family portraits line the walls. The characters gather here.",
        # Acts as a central hub connecting to other main areas
        "exits_to": ["Study", "Gallery", "Guest Bedroom", "Kitchen"],
        "properties": {
            "contains": [
                {"object": "sofas and chairs", "state": "occupied by suspects",
                    "optional_description": "Plush velvet sofas and armchairs where the remaining occupants of the manor are gathered."
                },
                {"object": "coffee table", "state": "scattered tea cups",
                    "optional_description": "A large central table littered with teacups, saucers, and a teapot from the recent gathering."
                },
                {"object": "fireplace", "state": "roaring fire",
                    "optional_description": "A large fireplace, providing warmth and light, a stark contrast to the storm outside and the mood within."
                },
                {"object": "family portraits", "state": "hanging on walls",
                    "optional_description": "Numerous portraits of stern-faced Finch ancestors observing the scene from the walls."
                },
                {"object": "grandfather clock", "state": "ticking loudly",
                    "optional_description": "A tall, ornate clock in the corner, its pendulum swinging and ticking filling the tense silence."
                }
            ]
        }
    },
    "Gallery": {
        "description": "A long hall dedicated to the manor's art collection. While impressive, many pieces are dusty or poorly lit, reflecting the manor's decline.",
        # Assumed exit back to the main gathering area
        "exits_to": ["Drawing Room"],
        "properties": {
            "contains": [
                {"object": "painting collection", "state": "displayed",
                    "optional_description": "Various oil paintings, landscapes, and portraits hanging along the walls."
                },
                {"object": "the obscure painting", "state": "hanging prominently",
                    "optional_description": "A specific, darker painting depicting a scene that includes a figure holding a distinctive dagger or pointed object."
                },
                {"object": "pedestal", "state": "empty",
                    "optional_description": "An empty pedestal in the centre of the room, perhaps awaiting a new acquisition or display piece."
                },
                {"object": "dust motes", "state": "visible in light",
                    "optional_description": "Dust motes dance in the shafts of light filtering through the occasional window or lamps."
                }
            ]
        }
    },
    "Kitchen": {
        "description": "The functional heart of the manor's service wing. Large, slightly dated, filled with the smells of cooked meals and cleaning supplies.",
        # Assumed exit back to the main house area (via service entrance near drawing room?)
        "exits_to": ["Drawing Room"],
        "properties": {
            "contains": [
                {"object": "large oven stove", "state": "warm",
                    "optional_description": "A large, old-fashioned cast-iron oven and hob, still radiating warmth."
                },
                {"object": "work table", "state": "clean",
                    "optional_description": "A large wooden table used for food preparation."
                },
                {"object": "knife rack", "state": "full",
                    "optional_description": "A wooden block holding a set of various kitchen knives. All seem to be present."
                },
                {"object": "servant bell system", "state": "silent",
                    "optional_description": "A panel on the wall with small bells and labels for different rooms, currently quiet."
                },
                {"object": "cleaning supplies", "state": "stored neatly",
                    "optional_description": "Brooms, mops, and cleaning fluids stored in a corner."
                }
            ]
        }
    },
    "Guest Bedroom": {
        "description": "One of the manor's many guest rooms, comfortably furnished but perhaps a little impersonal. Likely occupied by one of the visitors.",
        # Assumed exit back to the main house area (e.g., upstairs landing connected to drawing room area)
        "exits_to": ["Drawing Room"],
        "properties": {
            "contains": [
                {"object": "four poster bed", "state": "neatly made",
                    "optional_description": "A large bed with curtains, currently tidy."
                },
                {"object": "wardrobe", "state": "closed",
                    "optional_description": "A large wooden wardrobe for storing clothes."
                },
                {"object": "dressing table", "state": "tidy",
                    "optional_description": "A small table with a mirror and a set of brushes or toiletries."
                },
                {"object": "suitcase", "state": "partially unpacked",
                    "optional_description": "A suitcase lies open or closed near the wardrobe, suggesting the occupant is staying."
                },
                {"object": "window", "state": "closed",
                    "optional_description": "A window looking out onto the stormy night."
                }
            ]
        }
    }
}


# --- Component Selection ---
AGENT_MEMORY_TYPE = "ShortLongTMemoryIdentityOnly"
AGENT_PLANNING_TYPE = "SimplePlanningIdentityOnly"
ACTION_RESOLVER_TYPE = "LLMResolver"
EVENT_PERCEPTION_MODEL = "DirectEventDispatcher"
STORY_GENERATOR_TYPE = "LLMLogStoryGenerator"

# --- Narrative / Scenario ---
NARRATIVE_GOAL = """The story should culminate in Inspector Dubois gathering all the suspects, explaining his deductions step-by-step, and dramatically revealing the true murderer and their method. The "how" of the murder should be as intriguing as the "who." """
TONE = "Formal, suspenseful, intellectually stimulating, with a focus on logical deduction and character interactions rather than gore or action."

agent_configs = [
    {
        "name": "Thomas Dubois",
        "identity": "Inspector Thomas Dubois, a slightly unassuming man in his late 40s, known for his meticulous logic, quiet observation, and ability to deduce motives from seemingly insignificant details and human psychology. ",
        "initial_location": "Drawing Room",
        "gender":"",
        "personality":"",
        "initial_goals":"",
        "background":"",
        "initial_context": " Inspector Thomas Dubois had been enjoying a quiet, albeit slightly strained, evening as a guest at Blackwood Manor, discussing art and the terrible weather with the other occupants in the drawing-room. The sudden, hushed announcement from Mr. Davies that Lord Alistair had been found dead abruptly shattered the social facade, shifting Dubois immediately from polite visitor to keen observer and imminent investigator, his mind already beginning to piece together the puzzle from the reactions around him."
    },
    {
        "name": "Eleanor Finch",
        "identity":"Eleanor Finch, Lord Alistair's estranged niece, in her early 30s. She carries a considerable amount of debt and has just discovered she is the sole beneficiary of Lord Alistair's revised will – a will she knew nothing about until his recent announcement. She appears nervous and overly emotional.",
        "initial_location": "Drawing Room",
        "gender": "",
        "personality": "",
        "initial_goals": "",
        "background": "",
        "initial_context": " Eleanor Finch was already on edge, her nerves frayed by the storm outside and the weight of her precarious financial situation, recently compounded by the bewildering news of her uncle's revised will. The shock of Lord Alistair's death sent her into a state of visible distress, wringing her hands and struggling to compose herself amidst gasps and murmurs in the drawing-room, her grief and fear intertwined."
    },
    {
        "name": "Aris Thorne",
        "identity": "Dr. Aris Thorne, Lord Alistair's seemingly loyal, long-time personal physician, in his late 50s. He is outwardly calm and collected, but possesses an unnerving knowledge of the Finch family's deepest secrets. He frequently glances at Eleanor with concern.",
        "initial_location": "Drawing Room",
        "gender": "",
        "personality": "",
        "initial_goals": "",
        "background": "",
        "initial_context": "Dr. Aris Thorne maintained a veneer of professional calm upon hearing the news, his medical background perhaps steels him against overt displays of panic. However, beneath the surface, his sharp eyes missed nothing, particularly Eleanor's reaction, while his mind processed the implications of Lord Alistair's sudden demise, perhaps connecting it to long-held family secrets he was privy to. He would be observing the scene from the drawing-room, ready to offer his 'assistance' or observations."
    },
    {
        "name": "Xenia Petrova",
        "identity": "Madame Xenia Petrova, a flamboyant and ambitious international art dealer in her 40s, who was negotiating a major, highly secretive sale with Lord Alistair just hours before his death. She claims a strong alibi but seems overly interested in a specific, obscure painting in the manor's collection.",
        "initial_location": "Drawing Room",
        "gender": "",
        "personality": "",
        "initial_goals": "",
        "background": "",
        "initial_context": " Madame Xenia Petrova, fresh from her intense negotiation with Lord Alistair, was likely anticipating the outcome of her potential deal when the news broke. Her initial state would be one of dramatic shock and annoyance at the sudden disruption, quickly overlaid with a calculating curiosity as she assessed how this unforeseen event might impact her business interests and access to the manor's collection, while perhaps making a mental note of who else seemed affected. She'd be in the drawing-room, observing."
    },
    {
        "name": "Mr. Davies",
        "identity": "Mr. Davies, the manor's stoic and long-serving butler in his 60s. He sees and hears everything but reveals very little, offering only curt, precise answers to the Inspector's questions. He seems subtly protective of Lord Alistair's legacy and killed Lord Alistair.",
        "initial_location": "Drawing Room",
        "gender": "",
        "personality": "",
        "initial_goals": "",
        "background": "",
        "initial_context": "Mr. Davies, the unflappable butler, is the one who discovered the body in the study. His initial state is one of grim, controlled urgency as he delivers the shocking news to the assembled company in the drawing-room, his usual stoicism tested by the gravity of the situation, yet still managing to convey the facts with precise, if curt, language, before leading the Inspector to the scene."
    },
]
SIMULATION_MODE = 'debug'  # Keep debug for testing
