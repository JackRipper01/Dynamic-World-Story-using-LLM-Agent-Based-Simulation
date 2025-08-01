"""
Visualization module for Dynamic World Story Simulation
Provides various visualization capabilities for simulation data and results.
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import re

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.animation import FuncAnimation
    import seaborn as sns
    import pandas as pd
    import numpy as np
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    plt = None
    sns = None
    pd = None
    np = None

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None


class SimulationVisualizer:
    """Main visualization class for simulation data"""
    
    def __init__(self, output_dir: str = "visualizations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        if not VISUALIZATION_AVAILABLE:
            print("⚠️  Visualization libraries not available. Install matplotlib, seaborn, pandas, numpy for full functionality.")
    
    def create_world_map(self, locations_data: Dict[str, Any], agent_locations: Dict[str, str] = None, 
                        save_path: Optional[str] = None) -> Optional[str]:
        """Create a visual map of the world locations and connections"""
        if not VISUALIZATION_AVAILABLE or not NETWORKX_AVAILABLE:
            print("❌ World map visualization requires matplotlib and networkx")
            return None
        
        # Create a graph from location data
        G = nx.Graph()
        
        # Add nodes (locations)
        for loc_name, loc_data in locations_data.items():
            G.add_node(loc_name, description=loc_data.get('description', ''))
        
        # Add edges (connections)
        for loc_name, loc_data in locations_data.items():
            exits = loc_data.get('exits_to', [])
            for exit_dest in exits:
                if exit_dest in locations_data:
                    G.add_edge(loc_name, exit_dest)
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        # Use spring layout for automatic positioning
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                              node_size=3000, alpha=0.7)
        nx.draw_networkx_edges(G, pos, edge_color='gray', 
                              width=2, alpha=0.5)
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
        
        # Add agent positions if provided
        if agent_locations:
            agent_pos = {}
            for agent_name, location in agent_locations.items():
                if location in pos:
                    # Offset agent position slightly from location center
                    offset_x = np.random.uniform(-0.1, 0.1)
                    offset_y = np.random.uniform(-0.1, 0.1)
                    agent_pos[agent_name] = (pos[location][0] + offset_x, 
                                           pos[location][1] + offset_y)
            
            # Draw agents as red dots
            if agent_pos:
                agent_x = [pos[0] for pos in agent_pos.values()]
                agent_y = [pos[1] for pos in agent_pos.values()]
                plt.scatter(agent_x, agent_y, c='red', s=100, alpha=0.8, zorder=5)
                
                # Add agent labels
                for agent_name, (x, y) in agent_pos.items():
                    plt.annotate(agent_name, (x, y), xytext=(5, 5), 
                               textcoords='offset points', fontsize=8,
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        plt.title("World Map - Locations and Connections", fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        
        # Save the plot
        if save_path is None:
            save_path = self.output_dir / f"world_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(save_path)
    
    def create_agent_interaction_timeline(self, events_log: List[Dict], 
                                        save_path: Optional[str] = None) -> Optional[str]:
        """Create a timeline visualization of agent interactions"""
        if not VISUALIZATION_AVAILABLE:
            print("❌ Timeline visualization requires matplotlib and pandas")
            return None
        
        # Parse events to extract interactions
        interactions = []
        for event in events_log:
            if 'step' in event and 'triggered_by' in event:
                interactions.append({
                    'step': event['step'],
                    'agent': event.get('triggered_by', 'Unknown'),
                    'location': event.get('location', 'Unknown'),
                    'description': event.get('description', '')[:50] + '...'
                })
        
        if not interactions:
            print("⚠️  No interaction data found for timeline")
            return None
        
        df = pd.DataFrame(interactions)
        
        # Create the timeline plot
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Get unique agents and assign colors
        agents = df['agent'].unique()
        colors = plt.cm.Set3(np.linspace(0, 1, len(agents)))
        agent_colors = dict(zip(agents, colors))
        
        # Plot interactions
        for i, (_, row) in enumerate(df.iterrows()):
            agent = row['agent']
            step = row['step']
            y_pos = list(agents).index(agent)
            
            ax.scatter(step, y_pos, c=[agent_colors[agent]], s=100, alpha=0.7)
            
            # Add hover-like annotation (simplified)
            if i % 5 == 0:  # Only show every 5th annotation to avoid clutter
                ax.annotate(row['description'], (step, y_pos), 
                           xytext=(10, 10), textcoords='offset points',
                           fontsize=8, alpha=0.7,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        ax.set_xlabel('Simulation Step', fontsize=12)
        ax.set_ylabel('Agents', fontsize=12)
        ax.set_yticks(range(len(agents)))
        ax.set_yticklabels(agents)
        ax.set_title('Agent Interaction Timeline', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save the plot
        if save_path is None:
            save_path = self.output_dir / f"interaction_timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(save_path)
    
    def create_story_sentiment_analysis(self, story_text: str, 
                                      save_path: Optional[str] = None) -> Optional[str]:
        """Create a sentiment analysis visualization of the story"""
        if not VISUALIZATION_AVAILABLE:
            print("❌ Sentiment analysis visualization requires matplotlib")
            return None
        
        # Simple sentiment analysis based on word patterns
        # This is a basic implementation - could be enhanced with proper NLP libraries
        
        sentences = re.split(r'[.!?]+', story_text)
        sentiments = []
        
        positive_words = ['happy', 'joy', 'love', 'wonderful', 'amazing', 'great', 'excellent', 
                         'beautiful', 'peaceful', 'harmony', 'success', 'triumph', 'hope']
        negative_words = ['sad', 'angry', 'hate', 'terrible', 'awful', 'bad', 'horrible',
                         'conflict', 'fight', 'war', 'death', 'fear', 'worry', 'problem']
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            words = sentence.lower().split()
            pos_count = sum(1 for word in words if any(pw in word for pw in positive_words))
            neg_count = sum(1 for word in words if any(nw in word for nw in negative_words))
            
            if pos_count > neg_count:
                sentiment = 1  # Positive
            elif neg_count > pos_count:
                sentiment = -1  # Negative
            else:
                sentiment = 0  # Neutral
            
            sentiments.append(sentiment)
        
        if not sentiments:
            print("⚠️  No sentences found for sentiment analysis")
            return None
        
        # Create the plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Sentiment over time
        ax1.plot(range(len(sentiments)), sentiments, marker='o', linewidth=2, markersize=4)
        ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax1.set_xlabel('Sentence Number')
        ax1.set_ylabel('Sentiment')
        ax1.set_title('Story Sentiment Over Time')
        ax1.set_ylim(-1.5, 1.5)
        ax1.grid(True, alpha=0.3)
        
        # Sentiment distribution
        sentiment_counts = pd.Series(sentiments).value_counts().sort_index()
        colors = ['red', 'gray', 'green']
        labels = ['Negative', 'Neutral', 'Positive']
        
        bars = ax2.bar(sentiment_counts.index, sentiment_counts.values, 
                      color=[colors[i+1] for i in sentiment_counts.index])
        ax2.set_xlabel('Sentiment')
        ax2.set_ylabel('Count')
        ax2.set_title('Sentiment Distribution')
        ax2.set_xticks([-1, 0, 1])
        ax2.set_xticklabels(labels)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Save the plot
        if save_path is None:
            save_path = self.output_dir / f"sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(save_path)
    
    def create_agent_memory_heatmap(self, agents_data: List[Dict], 
                                   save_path: Optional[str] = None) -> Optional[str]:
        """Create a heatmap showing agent memory/interaction patterns"""
        if not VISUALIZATION_AVAILABLE:
            print("❌ Heatmap visualization requires matplotlib and seaborn")
            return None
        
        # This is a placeholder implementation
        # In a real scenario, you'd extract memory data from agents
        
        agent_names = [agent.get('name', f'Agent_{i}') for i, agent in enumerate(agents_data)]
        
        # Create a mock interaction matrix
        n_agents = len(agent_names)
        interaction_matrix = np.random.rand(n_agents, n_agents)
        
        # Make it symmetric and zero diagonal
        interaction_matrix = (interaction_matrix + interaction_matrix.T) / 2
        np.fill_diagonal(interaction_matrix, 0)
        
        # Create the heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(interaction_matrix, 
                   xticklabels=agent_names, 
                   yticklabels=agent_names,
                   annot=True, 
                   cmap='YlOrRd',
                   square=True,
                   cbar_kws={'label': 'Interaction Strength'})
        
        plt.title('Agent Interaction Heatmap', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save the plot
        if save_path is None:
            save_path = self.output_dir / f"agent_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(save_path)
    
    def generate_simulation_report(self, simulation_data: Dict[str, Any], 
                                 output_path: Optional[str] = None) -> str:
        """Generate a comprehensive HTML report of the simulation"""
        
        if output_path is None:
            output_path = self.output_dir / f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Extract data
        config_data = simulation_data.get('config', {})
        events_log = simulation_data.get('events', [])
        story_text = simulation_data.get('story', '')
        agents_data = simulation_data.get('agents', [])
        
        # Generate visualizations
        visualizations = {}
        
        if 'locations' in simulation_data:
            world_map_path = self.create_world_map(
                simulation_data['locations'], 
                simulation_data.get('final_agent_locations', {})
            )
            if world_map_path:
                visualizations['world_map'] = world_map_path
        
        if events_log:
            timeline_path = self.create_agent_interaction_timeline(events_log)
            if timeline_path:
                visualizations['timeline'] = timeline_path
        
        if story_text:
            sentiment_path = self.create_story_sentiment_analysis(story_text)
            if sentiment_path:
                visualizations['sentiment'] = sentiment_path
        
        if agents_data:
            heatmap_path = self.create_agent_memory_heatmap(agents_data)
            if heatmap_path:
                visualizations['heatmap'] = heatmap_path
        
        # Generate HTML report
        html_content = self._generate_html_report(simulation_data, visualizations)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def _generate_html_report(self, simulation_data: Dict[str, Any], 
                            visualizations: Dict[str, str]) -> str:
        """Generate HTML content for the simulation report"""
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Dynamic World Story Simulation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                .section {{ margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
                .visualization {{ text-align: center; margin: 20px 0; }}
                .visualization img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px; }}
                .config-table {{ width: 100%; border-collapse: collapse; }}
                .config-table th, .config-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .config-table th {{ background-color: #f2f2f2; }}
                .story-text {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; 
                             font-style: italic; border-left: 4px solid #667eea; }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎭 Dynamic World Story Simulation Report</h1>
                <p class="timestamp">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """
        
        # Configuration section
        config_data = simulation_data.get('config', {})
        if config_data:
            html += """
            <div class="section">
                <h2>📋 Configuration</h2>
                <table class="config-table">
            """
            for key, value in config_data.items():
                html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
            html += "</table></div>"
        
        # Agents section
        agents_data = simulation_data.get('agents', [])
        if agents_data:
            html += """
            <div class="section">
                <h2>🤖 Agents</h2>
            """
            for agent in agents_data:
                name = agent.get('name', 'Unknown')
                identity = agent.get('identity', 'No identity provided')
                location = agent.get('initial_location', 'Unknown')
                html += f"""
                <div style="margin-bottom: 15px; padding: 10px; background-color: #f5f5f5; border-radius: 5px;">
                    <h4>{name}</h4>
                    <p><strong>Location:</strong> {location}</p>
                    <p><strong>Identity:</strong> {identity}</p>
                </div>
                """
            html += "</div>"
        
        # Visualizations section
        if visualizations:
            html += """
            <div class="section">
                <h2>📊 Visualizations</h2>
            """
            
            for viz_type, viz_path in visualizations.items():
                viz_name = viz_type.replace('_', ' ').title()
                # Convert absolute path to relative for HTML
                rel_path = os.path.relpath(viz_path, os.path.dirname(output_path))
                html += f"""
                <div class="visualization">
                    <h3>{viz_name}</h3>
                    <img src="{rel_path}" alt="{viz_name}">
                </div>
                """
            
            html += "</div>"
        
        # Story section
        story_text = simulation_data.get('story', '')
        if story_text:
            html += f"""
            <div class="section">
                <h2>📖 Generated Story</h2>
                <div class="story-text">
                    {story_text.replace('\n', '<br>')}
                </div>
            </div>
            """
        
        # Events log section (abbreviated)
        events_log = simulation_data.get('events', [])
        if events_log:
            html += """
            <div class="section">
                <h2>📝 Events Log (Last 10 Events)</h2>
                <ul>
            """
            for event in events_log[-10:]:  # Show last 10 events
                step = event.get('step', '?')
                description = event.get('description', 'No description')
                triggered_by = event.get('triggered_by', 'Unknown')
                html += f"<li><strong>Step {step}:</strong> {description} <em>(by {triggered_by})</em></li>"
            html += "</ul></div>"
        
        html += """
        </body>
        </html>
        """
        
        return html


def create_visualization_from_logs(log_file_path: str, output_dir: str = "visualizations"):
    """Create visualizations from existing log files"""
    if not os.path.exists(log_file_path):
        print(f"❌ Log file not found: {log_file_path}")
        return
    
    visualizer = SimulationVisualizer(output_dir)
    
    # This would need to be implemented based on the actual log format
    print(f"⚠️  Log parsing not yet implemented for: {log_file_path}")
    print(f"Visualization output directory: {output_dir}")


if __name__ == "__main__":
    # Example usage
    visualizer = SimulationVisualizer()
    
    # Example data structure
    example_data = {
        'config': {
            'MODEL_NAME': 'gemini-2.0-flash-lite',
            'SIMULATION_MAX_STEPS': 30,
            'AGENT_MEMORY_TYPE': 'ShortLongTMemoryIdentityOnly'
        },
        'agents': [
            {'name': 'Mateo', 'identity': 'Young farmer', 'initial_location': "Mateo's House"},
            {'name': 'Elena', 'identity': 'Elder woman', 'initial_location': "Elena's House"}
        ],
        'locations': {
            "Mateo's House": {'description': 'Modern farm', 'exits_to': ["Abuelo Ceibo"]},
            "Elena's House": {'description': 'Traditional home', 'exits_to': ["Abuelo Ceibo"]},
            "Abuelo Ceibo": {'description': 'Ancient tree', 'exits_to': ["Mateo's House", "Elena's House"]}
        },
        'story': 'This is an example story about Mateo and Elena...',
        'events': [
            {'step': 1, 'description': 'Mateo looks at the tree', 'triggered_by': 'Mateo', 'location': "Mateo's House"},
            {'step': 2, 'description': 'Elena tends her garden', 'triggered_by': 'Elena', 'location': "Elena's House"}
        ]
    }
    
    print("🎨 Generating example visualization report...")
    report_path = visualizer.generate_simulation_report(example_data)
    print(f"✅ Report generated: {report_path}")