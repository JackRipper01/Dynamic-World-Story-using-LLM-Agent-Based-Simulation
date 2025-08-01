"""
Enhanced story generation system with multiple output formats and advanced features
Extends the basic story generator with rich formatting, multiple export options, and analysis.
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

try:
    import markdown
    from markdown.extensions import codehilite, tables, toc
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    from jinja2 import Template, Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


@dataclass
class StoryMetadata:
    """Metadata for generated stories"""
    title: str
    generation_time: str
    total_steps: int
    agent_count: int
    word_count: int
    character_count: int
    model_used: str
    narrative_goal: str
    tone: str
    locations: List[str]
    agents: List[str]
    tags: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoryChapter:
    """Represents a chapter or section of the story"""
    title: str
    content: str
    step_range: tuple
    agents_involved: List[str]
    locations: List[str]
    key_events: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StoryFormatter(ABC):
    """Abstract base class for story formatters"""
    
    @abstractmethod
    def format_story(self, story_content: str, metadata: StoryMetadata, 
                    chapters: List[StoryChapter] = None) -> str:
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        pass


class PlainTextFormatter(StoryFormatter):
    """Plain text story formatter"""
    
    def format_story(self, story_content: str, metadata: StoryMetadata, 
                    chapters: List[StoryChapter] = None) -> str:
        output = []
        
        # Title and metadata
        output.append("=" * 60)
        output.append(f"TITLE: {metadata.title}")
        output.append("=" * 60)
        output.append(f"Generated: {metadata.generation_time}")
        output.append(f"Model: {metadata.model_used}")
        output.append(f"Steps: {metadata.total_steps}")
        output.append(f"Agents: {', '.join(metadata.agents)}")
        output.append(f"Locations: {', '.join(metadata.locations)}")
        output.append(f"Word Count: {metadata.word_count}")
        output.append("")
        
        # Narrative goal
        if metadata.narrative_goal:
            output.append("NARRATIVE GOAL:")
            output.append("-" * 20)
            output.append(metadata.narrative_goal)
            output.append("")
        
        # Story content
        output.append("STORY:")
        output.append("-" * 20)
        
        if chapters:
            for i, chapter in enumerate(chapters, 1):
                output.append(f"\nChapter {i}: {chapter.title}")
                output.append("-" * (len(chapter.title) + 12))
                output.append(chapter.content)
                output.append("")
        else:
            output.append(story_content)
        
        return "\n".join(output)
    
    def get_file_extension(self) -> str:
        return "txt"


class MarkdownFormatter(StoryFormatter):
    """Markdown story formatter"""
    
    def format_story(self, story_content: str, metadata: StoryMetadata, 
                    chapters: List[StoryChapter] = None) -> str:
        output = []
        
        # Title
        output.append(f"# {metadata.title}")
        output.append("")
        
        # Metadata table
        output.append("## Story Information")
        output.append("")
        output.append("| Field | Value |")
        output.append("|-------|-------|")
        output.append(f"| Generated | {metadata.generation_time} |")
        output.append(f"| Model | {metadata.model_used} |")
        output.append(f"| Steps | {metadata.total_steps} |")
        output.append(f"| Agents | {', '.join(metadata.agents)} |")
        output.append(f"| Locations | {', '.join(metadata.locations)} |")
        output.append(f"| Word Count | {metadata.word_count} |")
        output.append(f"| Character Count | {metadata.character_count} |")
        output.append("")
        
        # Narrative goal
        if metadata.narrative_goal:
            output.append("## Narrative Goal")
            output.append("")
            output.append(f"> {metadata.narrative_goal}")
            output.append("")
        
        # Tone
        if metadata.tone:
            output.append("## Tone")
            output.append("")
            output.append(f"*{metadata.tone}*")
            output.append("")
        
        # Story content
        output.append("## The Story")
        output.append("")
        
        if chapters:
            for i, chapter in enumerate(chapters, 1):
                output.append(f"### Chapter {i}: {chapter.title}")
                output.append("")
                
                # Chapter metadata
                if chapter.agents_involved or chapter.locations:
                    output.append("**Chapter Details:**")
                    if chapter.agents_involved:
                        output.append(f"- **Agents:** {', '.join(chapter.agents_involved)}")
                    if chapter.locations:
                        output.append(f"- **Locations:** {', '.join(chapter.locations)}")
                    if chapter.step_range:
                        output.append(f"- **Steps:** {chapter.step_range[0]}-{chapter.step_range[1]}")
                    output.append("")
                
                # Chapter content
                output.append(chapter.content)
                output.append("")
        else:
            output.append(story_content)
        
        # Tags
        if metadata.tags:
            output.append("---")
            output.append("")
            output.append("**Tags:** " + ", ".join(f"`{tag}`" for tag in metadata.tags))
        
        return "\n".join(output)
    
    def get_file_extension(self) -> str:
        return "md"


class HTMLFormatter(StoryFormatter):
    """HTML story formatter with styling"""
    
    def __init__(self, template_path: Optional[str] = None):
        self.template_path = template_path
        self.default_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ metadata.title }}</title>
    <style>
        body {
            font-family: 'Georgia', serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .metadata {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metadata table {
            width: 100%;
            border-collapse: collapse;
        }
        .metadata th, .metadata td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .metadata th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .narrative-goal {
            background: #e8f4f8;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
            font-style: italic;
        }
        .story-content {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            line-height: 1.8;
        }
        .chapter {
            margin-bottom: 40px;
        }
        .chapter h3 {
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .chapter-meta {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            font-size: 0.9em;
            color: #666;
        }
        .tags {
            margin-top: 30px;
            text-align: center;
        }
        .tag {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 8px;
            border-radius: 15px;
            font-size: 0.8em;
            margin: 2px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ metadata.title }}</h1>
        <p>Generated on {{ metadata.generation_time }}</p>
    </div>
    
    <div class="metadata">
        <h2>Story Information</h2>
        <table>
            <tr><th>Model Used</th><td>{{ metadata.model_used }}</td></tr>
            <tr><th>Total Steps</th><td>{{ metadata.total_steps }}</td></tr>
            <tr><th>Agents</th><td>{{ metadata.agents | join(', ') }}</td></tr>
            <tr><th>Locations</th><td>{{ metadata.locations | join(', ') }}</td></tr>
            <tr><th>Word Count</th><td>{{ metadata.word_count }}</td></tr>
            <tr><th>Character Count</th><td>{{ metadata.character_count }}</td></tr>
        </table>
    </div>
    
    {% if metadata.narrative_goal %}
    <div class="narrative-goal">
        <strong>Narrative Goal:</strong> {{ metadata.narrative_goal }}
    </div>
    {% endif %}
    
    <div class="story-content">
        <h2>The Story</h2>
        
        {% if chapters %}
            {% for chapter in chapters %}
            <div class="chapter">
                <h3>Chapter {{ loop.index }}: {{ chapter.title }}</h3>
                
                {% if chapter.agents_involved or chapter.locations %}
                <div class="chapter-meta">
                    {% if chapter.agents_involved %}
                    <strong>Agents:</strong> {{ chapter.agents_involved | join(', ') }}<br>
                    {% endif %}
                    {% if chapter.locations %}
                    <strong>Locations:</strong> {{ chapter.locations | join(', ') }}<br>
                    {% endif %}
                    {% if chapter.step_range %}
                    <strong>Steps:</strong> {{ chapter.step_range[0] }}-{{ chapter.step_range[1] }}
                    {% endif %}
                </div>
                {% endif %}
                
                <div>{{ chapter.content | replace('\n', '<br>') | safe }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div>{{ story_content | replace('\n', '<br>') | safe }}</div>
        {% endif %}
    </div>
    
    {% if metadata.tags %}
    <div class="tags">
        {% for tag in metadata.tags %}
        <span class="tag">{{ tag }}</span>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="footer">
        <p>Generated by Dynamic World Story LLM Agent-Based Simulation</p>
    </div>
</body>
</html>
        """
    
    def format_story(self, story_content: str, metadata: StoryMetadata, 
                    chapters: List[StoryChapter] = None) -> str:
        if JINJA2_AVAILABLE:
            if self.template_path and os.path.exists(self.template_path):
                with open(self.template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            else:
                template_content = self.default_template
            
            template = Template(template_content)
            return template.render(
                story_content=story_content,
                metadata=metadata,
                chapters=chapters
            )
        else:
            # Fallback to simple HTML without templating
            return self._simple_html_format(story_content, metadata, chapters)
    
    def _simple_html_format(self, story_content: str, metadata: StoryMetadata, 
                           chapters: List[StoryChapter] = None) -> str:
        """Simple HTML format without Jinja2"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{metadata.title}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #667eea; color: white; padding: 20px; border-radius: 10px; }}
        .story {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{metadata.title}</h1>
        <p>Generated: {metadata.generation_time}</p>
    </div>
    <div class="story">
        <h2>The Story</h2>
        <p>{story_content.replace(chr(10), '<br>')}</p>
    </div>
</body>
</html>
        """
        return html
    
    def get_file_extension(self) -> str:
        return "html"


class JSONFormatter(StoryFormatter):
    """JSON story formatter for programmatic use"""
    
    def format_story(self, story_content: str, metadata: StoryMetadata, 
                    chapters: List[StoryChapter] = None) -> str:
        data = {
            'metadata': metadata.to_dict(),
            'story_content': story_content,
            'chapters': [chapter.to_dict() for chapter in chapters] if chapters else None,
            'export_timestamp': datetime.now().isoformat(),
            'format_version': '1.0'
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def get_file_extension(self) -> str:
        return "json"


class EnhancedStoryGenerator:
    """Enhanced story generator with multiple output formats and advanced features"""
    
    def __init__(self, base_story_generator=None):
        self.base_generator = base_story_generator
        self.formatters = {
            'txt': PlainTextFormatter(),
            'md': MarkdownFormatter(),
            'html': HTMLFormatter(),
            'json': JSONFormatter()
        }
        self.output_dir = Path("stories")
        self.output_dir.mkdir(exist_ok=True)
    
    def add_formatter(self, format_name: str, formatter: StoryFormatter):
        """Add a custom formatter"""
        self.formatters[format_name] = formatter
    
    def analyze_story_content(self, story_content: str) -> Dict[str, Any]:
        """Analyze story content for metadata"""
        words = story_content.split()
        sentences = re.split(r'[.!?]+', story_content)
        paragraphs = story_content.split('\n\n')
        
        # Extract potential character names (capitalized words that appear multiple times)
        word_freq = {}
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word and clean_word[0].isupper() and len(clean_word) > 2:
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
        
        potential_characters = [word for word, freq in word_freq.items() if freq >= 3]
        
        # Extract locations (words after "at", "in", "to" etc.)
        location_pattern = r'\b(?:at|in|to|from|near)\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|\.|\!|\?|$)'
        potential_locations = re.findall(location_pattern, story_content)
        potential_locations = list(set([loc.strip() for loc in potential_locations if len(loc.strip()) > 2]))
        
        return {
            'word_count': len(words),
            'character_count': len(story_content),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'paragraph_count': len([p for p in paragraphs if p.strip()]),
            'potential_characters': potential_characters[:10],  # Top 10
            'potential_locations': potential_locations[:10],   # Top 10
            'avg_words_per_sentence': len(words) / max(len(sentences), 1),
            'avg_sentences_per_paragraph': len(sentences) / max(len(paragraphs), 1)
        }
    
    def create_chapters_from_events(self, events_log: List[Dict], 
                                  story_content: str, 
                                  chapter_size: int = 10) -> List[StoryChapter]:
        """Create story chapters based on simulation events"""
        if not events_log:
            return []
        
        chapters = []
        story_paragraphs = story_content.split('\n\n')
        
        # Group events into chapters
        for i in range(0, len(events_log), chapter_size):
            chapter_events = events_log[i:i + chapter_size]
            
            if not chapter_events:
                continue
            
            # Extract chapter info
            start_step = chapter_events[0].get('step', i)
            end_step = chapter_events[-1].get('step', i + len(chapter_events))
            
            agents_involved = list(set([
                event.get('triggered_by', '') 
                for event in chapter_events 
                if event.get('triggered_by')
            ]))
            
            locations = list(set([
                event.get('location', '') 
                for event in chapter_events 
                if event.get('location')
            ]))
            
            key_events = [
                event.get('description', '')[:100] + '...' 
                for event in chapter_events[:3]  # Top 3 events
                if event.get('description')
            ]
            
            # Estimate chapter content (this is simplified)
            chapter_start = max(0, i * len(story_paragraphs) // len(events_log))
            chapter_end = min(len(story_paragraphs), (i + chapter_size) * len(story_paragraphs) // len(events_log))
            chapter_content = '\n\n'.join(story_paragraphs[chapter_start:chapter_end])
            
            chapter = StoryChapter(
                title=f"Steps {start_step}-{end_step}",
                content=chapter_content,
                step_range=(start_step, end_step),
                agents_involved=agents_involved,
                locations=locations,
                key_events=key_events
            )
            
            chapters.append(chapter)
        
        return chapters
    
    def generate_enhanced_story(self, 
                              simulation_data: Dict[str, Any],
                              title: Optional[str] = None,
                              formats: List[str] = None,
                              create_chapters: bool = True) -> Dict[str, str]:
        """Generate enhanced story in multiple formats
        
        Args:
            simulation_data: Dictionary containing simulation results
            title: Custom title for the story
            formats: List of formats to generate ('txt', 'md', 'html', 'json')
            create_chapters: Whether to create chapters from events
            
        Returns:
            Dictionary mapping format names to file paths
        """
        if formats is None:
            formats = ['txt', 'md', 'html']
        
        # Extract data from simulation
        story_content = simulation_data.get('story', '')
        events_log = simulation_data.get('events', [])
        config_data = simulation_data.get('config', {})
        agents_data = simulation_data.get('agents', [])
        
        if not story_content:
            raise ValueError("No story content found in simulation data")
        
        # Analyze story content
        analysis = self.analyze_story_content(story_content)
        
        # Create metadata
        metadata = StoryMetadata(
            title=title or f"Dynamic World Story - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_steps=config_data.get('SIMULATION_MAX_STEPS', len(events_log)),
            agent_count=len(agents_data),
            word_count=analysis['word_count'],
            character_count=analysis['character_count'],
            model_used=config_data.get('MODEL_NAME', 'Unknown'),
            narrative_goal=config_data.get('NARRATIVE_GOAL', ''),
            tone=config_data.get('TONE', ''),
            locations=list(config_data.get('KNOWN_LOCATIONS_DATA', {}).keys()),
            agents=[agent.get('name', f'Agent_{i}') for i, agent in enumerate(agents_data)],
            tags=['ai-generated', 'llm-simulation', 'emergent-narrative']
        )
        
        # Create chapters if requested
        chapters = None
        if create_chapters and events_log:
            chapters = self.create_chapters_from_events(events_log, story_content)
        
        # Generate stories in requested formats
        generated_files = {}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for format_name in formats:
            if format_name not in self.formatters:
                print(f"⚠️  Unknown format: {format_name}")
                continue
            
            formatter = self.formatters[format_name]
            formatted_content = formatter.format_story(story_content, metadata, chapters)
            
            # Save to file
            filename = f"story_{timestamp}.{formatter.get_file_extension()}"
            file_path = self.output_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            generated_files[format_name] = str(file_path)
            print(f"✅ Generated {format_name.upper()} story: {file_path}")
        
        return generated_files
    
    def create_story_collection(self, stories_data: List[Dict[str, Any]], 
                              collection_title: str = "Story Collection") -> str:
        """Create a collection of multiple stories"""
        collection_dir = self.output_dir / f"collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        collection_dir.mkdir(exist_ok=True)
        
        # Generate individual stories
        story_files = []
        for i, story_data in enumerate(stories_data):
            story_title = f"{collection_title} - Story {i+1}"
            files = self.generate_enhanced_story(
                story_data, 
                title=story_title,
                formats=['html', 'md']
            )
            story_files.extend(files.values())
        
        # Create index file
        index_content = f"""# {collection_title}

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Stories in this Collection

"""
        
        for i, story_data in enumerate(stories_data, 1):
            index_content += f"- [Story {i}](story_{i}.html)\n"
        
        index_path = collection_dir / "index.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"✅ Created story collection: {collection_dir}")
        return str(collection_dir)


if __name__ == "__main__":
    # Example usage
    generator = EnhancedStoryGenerator()
    
    # Example simulation data
    example_data = {
        'story': """Mateo stood at the edge of his field, gazing at the ancient Abuelo Ceibo tree. 
        Its massive trunk and sprawling branches had watched over the valley for generations. 
        But now, economic pressures weighed heavily on his shoulders.
        
        Elena emerged from her cottage, her weathered hands carrying a cup of herbal tea. 
        She had lived beside this tree her entire life, just as her ancestors had. 
        The tree was more than wood and leaves to her - it was a guardian, a symbol of resilience.
        
        "We need to talk," Mateo called out, his voice carrying across the morning air.
        Elena nodded, knowing this conversation had been inevitable.""",
        
        'events': [
            {'step': 1, 'description': 'Mateo surveys his fields', 'triggered_by': 'Mateo', 'location': "Mateo's House"},
            {'step': 2, 'description': 'Elena tends her garden', 'triggered_by': 'Elena', 'location': "Elena's House"},
            {'step': 3, 'description': 'Mateo approaches the tree', 'triggered_by': 'Mateo', 'location': 'Abuelo Ceibo'},
        ],
        
        'config': {
            'MODEL_NAME': 'gemini-2.0-flash-lite',
            'SIMULATION_MAX_STEPS': 30,
            'NARRATIVE_GOAL': 'Explore the conflict between tradition and progress',
            'TONE': 'Reflective and empathetic',
            'KNOWN_LOCATIONS_DATA': {
                "Mateo's House": {},
                "Elena's House": {},
                "Abuelo Ceibo": {}
            }
        },
        
        'agents': [
            {'name': 'Mateo', 'identity': 'Young pragmatic farmer'},
            {'name': 'Elena', 'identity': 'Elder traditional woman'}
        ]
    }
    
    # Generate enhanced story
    files = generator.generate_enhanced_story(
        example_data,
        title="The Ancient Tree",
        formats=['txt', 'md', 'html', 'json']
    )
    
    print("\nGenerated files:")
    for format_name, file_path in files.items():
        print(f"  {format_name}: {file_path}")