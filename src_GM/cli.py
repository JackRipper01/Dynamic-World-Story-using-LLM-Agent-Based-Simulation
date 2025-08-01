#!/usr/bin/env python3
"""
Enhanced CLI interface for Dynamic World Story LLM Agent-Based Simulation
Provides interactive commands and configuration options for running simulations.
"""

import click
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
import importlib.util

# Add src_GM to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

import config
from main import run_simulation


class SimulationCLI:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.config_path = Path(__file__).parent / "config.py"
        
    def print_message(self, message: str, style: str = ""):
        """Print message with optional rich styling"""
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)
    
    def print_panel(self, content: str, title: str = "", style: str = ""):
        """Print content in a panel if rich is available"""
        if self.console:
            self.console.print(Panel(content, title=title, style=style))
        else:
            print(f"\n=== {title} ===")
            print(content)
            print("=" * (len(title) + 8))

    def show_config_status(self):
        """Display current configuration status"""
        status_info = []
        
        # Check API key
        api_key_status = "✅ Set" if config.GEMINI_API_KEY else "❌ Missing"
        status_info.append(f"Gemini API Key: {api_key_status}")
        
        # Check model configuration
        status_info.append(f"Model: {config.MODEL_NAME}")
        status_info.append(f"Max Steps: {config.SIMULATION_MAX_STEPS}")
        status_info.append(f"Memory Type: {config.AGENT_MEMORY_TYPE}")
        status_info.append(f"Planning Type: {config.AGENT_PLANNING_TYPE}")
        
        # Check agents
        agent_count = len(config.agent_configs) if hasattr(config, 'agent_configs') else 0
        status_info.append(f"Configured Agents: {agent_count}")
        
        # Check locations
        location_count = len(config.KNOWN_LOCATIONS_DATA)
        status_info.append(f"World Locations: {location_count}")
        
        content = "\n".join(status_info)
        self.print_panel(content, "Configuration Status", "blue")

    def list_scenarios(self):
        """List available scenario configurations"""
        scenarios_dir = Path(__file__).parent.parent / "initial configs"
        
        if not scenarios_dir.exists():
            self.print_message("No scenarios directory found", "red")
            return
        
        scenarios = list(scenarios_dir.glob("*.txt"))
        
        if not scenarios:
            self.print_message("No scenario files found", "yellow")
            return
        
        self.print_message("Available Scenarios:", "bold blue")
        for i, scenario in enumerate(scenarios, 1):
            self.print_message(f"  {i}. {scenario.stem}", "cyan")

    def show_agent_info(self):
        """Display information about configured agents"""
        if not hasattr(config, 'agent_configs') or not config.agent_configs:
            self.print_message("No agents configured", "red")
            return
        
        if self.console:
            table = Table(title="Configured Agents")
            table.add_column("Name", style="cyan")
            table.add_column("Location", style="green")
            table.add_column("Identity", style="yellow")
            
            for agent_config in config.agent_configs:
                identity_preview = agent_config.get('identity', '')[:50] + "..." if len(agent_config.get('identity', '')) > 50 else agent_config.get('identity', '')
                table.add_row(
                    agent_config.get('name', 'Unknown'),
                    agent_config.get('initial_location', 'Unknown'),
                    identity_preview
                )
            
            self.console.print(table)
        else:
            self.print_message("Configured Agents:", "bold")
            for agent_config in config.agent_configs:
                print(f"  - {agent_config.get('name', 'Unknown')} at {agent_config.get('initial_location', 'Unknown')}")

    def validate_environment(self) -> bool:
        """Validate that the environment is properly configured"""
        issues = []
        
        # Check API key
        if not config.GEMINI_API_KEY:
            issues.append("❌ GEMINI_API_KEY not set in environment")
        
        # Check required config attributes
        required_attrs = [
            'MODEL_NAME', 'GENERATION_CONFIG', 'KNOWN_LOCATIONS_DATA',
            'agent_configs', 'SIMULATION_MAX_STEPS'
        ]
        
        for attr in required_attrs:
            if not hasattr(config, attr):
                issues.append(f"❌ Missing configuration: {attr}")
        
        # Check agents configuration
        if hasattr(config, 'agent_configs'):
            if not config.agent_configs:
                issues.append("❌ No agents configured")
            else:
                for i, agent_config in enumerate(config.agent_configs):
                    required_agent_fields = ['name', 'identity', 'initial_location']
                    for field in required_agent_fields:
                        if not agent_config.get(field):
                            issues.append(f"❌ Agent {i+1} missing required field: {field}")
        
        if issues:
            self.print_message("Environment Validation Issues:", "red bold")
            for issue in issues:
                self.print_message(f"  {issue}", "red")
            return False
        else:
            self.print_message("✅ Environment validation passed!", "green bold")
            return True


@click.group()
@click.version_option(version="1.0.0", prog_name="Dynamic World Story Simulation")
def cli():
    """Dynamic World Story using LLM Agent-Based Simulation
    
    An interactive storytelling system where AI agents create emergent narratives
    through their interactions in a simulated world.
    """
    pass


@cli.command()
@click.option('--steps', '-s', default=None, type=int, help='Override maximum simulation steps')
@click.option('--mode', '-m', default=None, type=click.Choice(['debug', 'story']), help='Simulation mode')
@click.option('--validate/--no-validate', default=True, help='Validate environment before running')
def run(steps: Optional[int], mode: Optional[str], validate: bool):
    """Run the simulation with current configuration"""
    sim_cli = SimulationCLI()
    
    if validate and not sim_cli.validate_environment():
        sim_cli.print_message("❌ Environment validation failed. Use --no-validate to skip.", "red")
        return
    
    # Override config if specified
    if steps:
        config.SIMULATION_MAX_STEPS = steps
        sim_cli.print_message(f"Overriding max steps to: {steps}", "yellow")
    
    if mode:
        config.SIMULATION_MODE = mode
        sim_cli.print_message(f"Setting simulation mode to: {mode}", "yellow")
    
    sim_cli.print_message("🚀 Starting simulation...", "green bold")
    
    try:
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=sim_cli.console,
            ) as progress:
                task = progress.add_task("Running simulation...", total=None)
                run_simulation()
        else:
            run_simulation()
        
        sim_cli.print_message("✅ Simulation completed successfully!", "green bold")
        
    except KeyboardInterrupt:
        sim_cli.print_message("\n⚠️  Simulation interrupted by user", "yellow")
    except Exception as e:
        sim_cli.print_message(f"❌ Simulation failed: {str(e)}", "red bold")
        raise


@cli.command()
def status():
    """Show current configuration status"""
    sim_cli = SimulationCLI()
    sim_cli.show_config_status()


@cli.command()
def validate():
    """Validate environment configuration"""
    sim_cli = SimulationCLI()
    sim_cli.validate_environment()


@cli.command()
def agents():
    """Show information about configured agents"""
    sim_cli = SimulationCLI()
    sim_cli.show_agent_info()


@cli.command()
def scenarios():
    """List available scenario configurations"""
    sim_cli = SimulationCLI()
    sim_cli.list_scenarios()


@cli.command()
@click.argument('key')
@click.argument('value')
def config_set(key: str, value: str):
    """Set a configuration value (for this session only)"""
    sim_cli = SimulationCLI()
    
    # Convert string values to appropriate types
    if value.lower() in ('true', 'false'):
        value = value.lower() == 'true'
    elif value.isdigit():
        value = int(value)
    elif value.replace('.', '').isdigit():
        value = float(value)
    
    if hasattr(config, key):
        setattr(config, key, value)
        sim_cli.print_message(f"✅ Set {key} = {value}", "green")
    else:
        sim_cli.print_message(f"❌ Unknown configuration key: {key}", "red")


@cli.command()
def interactive():
    """Start interactive mode for step-by-step simulation control"""
    sim_cli = SimulationCLI()
    
    sim_cli.print_panel(
        "Interactive Mode - Control simulation step by step\n"
        "Commands: run, step, status, agents, quit",
        "Interactive Simulation Mode",
        "blue"
    )
    
    if not sim_cli.validate_environment():
        sim_cli.print_message("❌ Environment validation failed.", "red")
        return
    
    # This would require modifications to main.py to support step-by-step execution
    sim_cli.print_message("⚠️  Interactive mode requires additional implementation", "yellow")
    sim_cli.print_message("For now, use 'run' command for full simulation", "yellow")


if __name__ == '__main__':
    cli()