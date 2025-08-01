"""
Configuration validation system for Dynamic World Story Simulation
Provides comprehensive validation of configuration settings and environment setup.
"""

import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json

try:
    from pydantic import BaseModel, Field, validator
    from pydantic.types import PositiveInt, PositiveFloat
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


class ValidationResult:
    """Container for validation results"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def add_error(self, message: str):
        self.errors.append(f"❌ ERROR: {message}")
    
    def add_warning(self, message: str):
        self.warnings.append(f"⚠️  WARNING: {message}")
    
    def add_info(self, message: str):
        self.info.append(f"ℹ️  INFO: {message}")
    
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    def get_summary(self) -> str:
        total_issues = len(self.errors) + len(self.warnings)
        if self.is_valid():
            return f"✅ Configuration is valid ({len(self.info)} info messages)"
        else:
            return f"❌ Configuration has {len(self.errors)} errors and {len(self.warnings)} warnings"
    
    def get_all_messages(self) -> List[str]:
        return self.errors + self.warnings + self.info


class ConfigValidator:
    """Comprehensive configuration validator"""
    
    def __init__(self, config_module):
        self.config = config_module
        self.result = ValidationResult()
    
    def validate_all(self) -> ValidationResult:
        """Run all validation checks"""
        self.result = ValidationResult()
        
        # Core validation checks
        self._validate_api_keys()
        self._validate_model_config()
        self._validate_world_config()
        self._validate_agent_configs()
        self._validate_simulation_settings()
        self._validate_component_types()
        self._validate_file_paths()
        self._validate_memory_settings()
        self._validate_generation_configs()
        
        return self.result
    
    def _validate_api_keys(self):
        """Validate API key configuration"""
        if not hasattr(self.config, 'GEMINI_API_KEY'):
            self.result.add_error("GEMINI_API_KEY not defined in config")
            return
        
        if not self.config.GEMINI_API_KEY:
            self.result.add_error("GEMINI_API_KEY is empty - check your .env file")
            return
        
        if self.config.GEMINI_API_KEY == "your_gemini_api_key_here":
            self.result.add_error("GEMINI_API_KEY still contains placeholder value")
            return
        
        if len(self.config.GEMINI_API_KEY) < 20:
            self.result.add_warning("GEMINI_API_KEY seems too short - verify it's correct")
        
        self.result.add_info("API key configuration looks valid")
    
    def _validate_model_config(self):
        """Validate model configuration"""
        if not hasattr(self.config, 'MODEL_NAME'):
            self.result.add_error("MODEL_NAME not defined")
            return
        
        valid_models = [
            'gemini-2.0-flash-lite', 'gemini-1.5-pro', 'gemini-1.5-flash',
            'gemini-pro', 'gemini-pro-vision'
        ]
        
        if self.config.MODEL_NAME not in valid_models:
            self.result.add_warning(f"MODEL_NAME '{self.config.MODEL_NAME}' not in known models: {valid_models}")
        
        self.result.add_info(f"Using model: {self.config.MODEL_NAME}")
    
    def _validate_generation_configs(self):
        """Validate LLM generation configurations"""
        configs_to_check = [
            'GENERATION_CONFIG', 'AGENT_PLANNING_GEN_CONFIG', 
            'ACTION_RESOLVER_GEN_CONFIG', 'STORY_GENERATOR_GEN_CONFIG',
            'DIRECTOR_GEN_CONFIG', 'AGENT_REFLECTION_GEN_CONFIG'
        ]
        
        for config_name in configs_to_check:
            if not hasattr(self.config, config_name):
                self.result.add_warning(f"Missing generation config: {config_name}")
                continue
            
            gen_config = getattr(self.config, config_name)
            if not isinstance(gen_config, dict):
                self.result.add_error(f"{config_name} must be a dictionary")
                continue
            
            # Validate temperature
            if 'temperature' in gen_config:
                temp = gen_config['temperature']
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                    self.result.add_error(f"{config_name} temperature must be between 0 and 2")
            
            # Validate max_output_tokens
            if 'max_output_tokens' in gen_config:
                tokens = gen_config['max_output_tokens']
                if not isinstance(tokens, int) or tokens <= 0:
                    self.result.add_error(f"{config_name} max_output_tokens must be positive integer")
                elif tokens > 8192:
                    self.result.add_warning(f"{config_name} max_output_tokens ({tokens}) is very high")
    
    def _validate_world_config(self):
        """Validate world configuration"""
        if not hasattr(self.config, 'KNOWN_LOCATIONS_DATA'):
            self.result.add_error("KNOWN_LOCATIONS_DATA not defined")
            return
        
        locations = self.config.KNOWN_LOCATIONS_DATA
        if not isinstance(locations, dict):
            self.result.add_error("KNOWN_LOCATIONS_DATA must be a dictionary")
            return
        
        if len(locations) == 0:
            self.result.add_error("No locations defined in KNOWN_LOCATIONS_DATA")
            return
        
        # Validate each location
        for loc_name, loc_data in locations.items():
            if not isinstance(loc_data, dict):
                self.result.add_error(f"Location '{loc_name}' data must be a dictionary")
                continue
            
            if 'description' not in loc_data:
                self.result.add_warning(f"Location '{loc_name}' missing description")
            
            # Validate exits
            if 'exits_to' in loc_data:
                exits = loc_data['exits_to']
                if not isinstance(exits, list):
                    self.result.add_error(f"Location '{loc_name}' exits_to must be a list")
                else:
                    # Check if exit destinations exist
                    for exit_dest in exits:
                        if exit_dest not in locations:
                            self.result.add_warning(f"Location '{loc_name}' has exit to undefined location '{exit_dest}'")
        
        self.result.add_info(f"World has {len(locations)} locations configured")
    
    def _validate_agent_configs(self):
        """Validate agent configurations"""
        if not hasattr(self.config, 'agent_configs'):
            self.result.add_error("agent_configs not defined")
            return
        
        agents = self.config.agent_configs
        if not isinstance(agents, list):
            self.result.add_error("agent_configs must be a list")
            return
        
        if len(agents) == 0:
            self.result.add_error("No agents configured")
            return
        
        agent_names = set()
        locations = getattr(self.config, 'KNOWN_LOCATIONS_DATA', {})
        
        for i, agent_config in enumerate(agents):
            if not isinstance(agent_config, dict):
                self.result.add_error(f"Agent {i+1} configuration must be a dictionary")
                continue
            
            # Check required fields
            required_fields = ['name', 'identity', 'initial_location']
            for field in required_fields:
                if field not in agent_config or not agent_config[field]:
                    self.result.add_error(f"Agent {i+1} missing required field: {field}")
            
            # Check for duplicate names
            agent_name = agent_config.get('name')
            if agent_name:
                if agent_name in agent_names:
                    self.result.add_error(f"Duplicate agent name: {agent_name}")
                agent_names.add(agent_name)
            
            # Validate initial location
            initial_loc = agent_config.get('initial_location')
            if initial_loc and initial_loc not in locations:
                self.result.add_error(f"Agent '{agent_name}' initial_location '{initial_loc}' not in KNOWN_LOCATIONS_DATA")
            
            # Check optional fields
            optional_fields = ['gender', 'personality', 'initial_goals', 'background', 'initial_context']
            for field in optional_fields:
                if field not in agent_config:
                    self.result.add_info(f"Agent '{agent_name}' missing optional field: {field}")
        
        self.result.add_info(f"Found {len(agents)} agent configurations")
    
    def _validate_simulation_settings(self):
        """Validate simulation settings"""
        if hasattr(self.config, 'SIMULATION_MAX_STEPS'):
            max_steps = self.config.SIMULATION_MAX_STEPS
            if not isinstance(max_steps, int) or max_steps <= 0:
                self.result.add_error("SIMULATION_MAX_STEPS must be a positive integer")
            elif max_steps > 1000:
                self.result.add_warning(f"SIMULATION_MAX_STEPS ({max_steps}) is very high - this may take a long time")
        else:
            self.result.add_warning("SIMULATION_MAX_STEPS not defined")
        
        if hasattr(self.config, 'SIMULATION_MODE'):
            mode = self.config.SIMULATION_MODE
            if mode not in ['debug', 'story']:
                self.result.add_warning(f"SIMULATION_MODE '{mode}' not in recommended values: ['debug', 'story']")
        
        # Validate memory settings
        if hasattr(self.config, 'MAX_MEMORY_TOKENS'):
            tokens = self.config.MAX_MEMORY_TOKENS
            if not isinstance(tokens, int) or tokens <= 0:
                self.result.add_error("MAX_MEMORY_TOKENS must be a positive integer")
    
    def _validate_component_types(self):
        """Validate component type selections"""
        component_types = {
            'AGENT_MEMORY_TYPE': ['SimpleMemory', 'ShortLongTMemory', 'ShortLongTMemoryIdentityOnly'],
            'AGENT_PLANNING_TYPE': ['SimplePlanning', 'SimplePlanningIdentityOnly'],
            'ACTION_RESOLVER_TYPE': ['LLMActionResolver', 'LLMActionResolverWithReason'],
            'EVENT_PERCEPTION_MODEL': ['DirectEventDispatcher'],
            'STORY_GENERATOR_TYPE': ['LLMLogStoryGenerator']
        }
        
        for config_name, valid_types in component_types.items():
            if hasattr(self.config, config_name):
                config_value = getattr(self.config, config_name)
                if config_value not in valid_types:
                    self.result.add_error(f"{config_name} '{config_value}' not in valid types: {valid_types}")
            else:
                self.result.add_warning(f"Component type {config_name} not defined")
    
    def _validate_file_paths(self):
        """Validate file paths and directories"""
        # Check if .env file exists
        env_file = Path('.env')
        if not env_file.exists():
            env_template = Path('.env.template')
            if env_template.exists():
                self.result.add_warning("No .env file found, but .env.template exists - copy and configure it")
            else:
                self.result.add_warning("No .env file found - create one with your API keys")
        
        # Check scenarios directory
        scenarios_dir = Path(__file__).parent.parent / "initial configs"
        if scenarios_dir.exists():
            scenario_files = list(scenarios_dir.glob("*.txt"))
            self.result.add_info(f"Found {len(scenario_files)} scenario files")
        else:
            self.result.add_warning("No 'initial configs' directory found")
    
    def _validate_memory_settings(self):
        """Validate memory-related settings"""
        if hasattr(self.config, 'MAX_RECENT_EVENTS'):
            max_events = self.config.MAX_RECENT_EVENTS
            if not isinstance(max_events, int) or max_events <= 0:
                self.result.add_error("MAX_RECENT_EVENTS must be a positive integer")
            elif max_events > 100:
                self.result.add_warning(f"MAX_RECENT_EVENTS ({max_events}) is very high")


def validate_config(config_module) -> ValidationResult:
    """Main validation function"""
    validator = ConfigValidator(config_module)
    return validator.validate_all()


def print_validation_results(result: ValidationResult, verbose: bool = True):
    """Print validation results in a formatted way"""
    print("\n" + "="*60)
    print("CONFIGURATION VALIDATION RESULTS")
    print("="*60)
    
    print(f"\n{result.get_summary()}")
    
    if verbose or not result.is_valid():
        messages = result.get_all_messages()
        if messages:
            print("\nDetails:")
            for message in messages:
                print(f"  {message}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Allow running this as a standalone script
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        import config
        result = validate_config(config)
        print_validation_results(result)
        
        if not result.is_valid():
            sys.exit(1)
    except ImportError as e:
        print(f"❌ Could not import config module: {e}")
        sys.exit(1)