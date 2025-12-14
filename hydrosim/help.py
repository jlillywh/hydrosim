"""
Help system infrastructure for HydroSim.

This module provides environment detection utilities and base classes for
content formatting and display across different environments (terminal, Jupyter, Colab).
"""

import sys
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod


@dataclass
class Environment:
    """Environment detection results."""
    is_jupyter: bool
    is_colab: bool
    is_terminal: bool
    supports_html: bool
    supports_widgets: bool


@dataclass
class ExampleInfo:
    """Metadata for example scripts."""
    filename: str
    title: str
    description: str
    category: str
    difficulty: str  # "beginner", "intermediate", "advanced"
    notebook_friendly: bool
    code_snippet: str  # Ready-to-run code for notebooks


@dataclass
class HelpContent:
    """Content for help display with multiple format support."""
    text_content: str
    html_content: Optional[str] = None  # Rich formatting for Jupyter
    code_examples: List[str] = None
    links: List[str] = None
    
    def __post_init__(self):
        if self.code_examples is None:
            self.code_examples = []
        if self.links is None:
            self.links = []


class EnvironmentDetector:
    """Utility class for detecting the current execution environment."""
    
    @staticmethod
    def detect() -> Environment:
        """
        Detect the current execution environment.
        
        Returns:
            Environment: Object containing environment detection results
        """
        is_jupyter = EnvironmentDetector._is_jupyter()
        is_colab = EnvironmentDetector._is_colab()
        is_terminal = not (is_jupyter or is_colab)
        supports_html = is_jupyter or is_colab
        supports_widgets = is_jupyter or is_colab
        
        return Environment(
            is_jupyter=is_jupyter,
            is_colab=is_colab,
            is_terminal=is_terminal,
            supports_html=supports_html,
            supports_widgets=supports_widgets
        )
    
    @staticmethod
    def _is_jupyter() -> bool:
        """Check if running in Jupyter notebook environment."""
        try:
            # Check for IPython kernel
            from IPython import get_ipython
            ipython = get_ipython()
            if ipython is None:
                return False
            
            # Check if we're in a notebook kernel
            return hasattr(ipython, 'kernel')
        except ImportError:
            return False
    
    @staticmethod
    def _is_colab() -> bool:
        """Check if running in Google Colab environment."""
        try:
            import google.colab
            return True
        except ImportError:
            return False


class ContentFormatter(ABC):
    """Abstract base class for content formatting."""
    
    @abstractmethod
    def format_help_content(self, content: HelpContent) -> str:
        """Format help content for display."""
        pass
    
    @abstractmethod
    def format_code_example(self, code: str, language: str = "python") -> str:
        """Format code example for display."""
        pass
    
    @abstractmethod
    def format_link(self, url: str, text: str = None) -> str:
        """Format a link for display."""
        pass


class TerminalFormatter(ContentFormatter):
    """Content formatter for terminal environments."""
    
    def format_help_content(self, content: HelpContent) -> str:
        """Format help content for terminal display."""
        output = [content.text_content]
        
        if content.code_examples:
            output.append("\nCode Examples:")
            output.append("-" * 40)
            for i, example in enumerate(content.code_examples, 1):
                output.append(f"\nExample {i}:")
                output.append(self.format_code_example(example))
        
        if content.links:
            output.append("\nUseful Links:")
            output.append("-" * 40)
            for link in content.links:
                output.append(f"  • {link}")
        
        return "\n".join(output)
    
    def format_code_example(self, code: str, language: str = "python") -> str:
        """Format code example for terminal display."""
        lines = code.strip().split('\n')
        formatted_lines = [f"    {line}" for line in lines]
        return "\n".join(formatted_lines)
    
    def format_link(self, url: str, text: str = None) -> str:
        """Format a link for terminal display."""
        if text:
            return f"{text}: {url}"
        return url


class JupyterFormatter(ContentFormatter):
    """Content formatter for Jupyter notebook environments."""
    
    def format_help_content(self, content: HelpContent) -> str:
        """Format help content for Jupyter display."""
        if content.html_content:
            return self._display_html(content.html_content)
        
        # Fallback to enhanced text formatting
        output = [f"<div style='font-family: Arial, sans-serif;'>"]
        output.append(f"<p>{content.text_content.replace(chr(10), '<br>')}</p>")
        
        if content.code_examples:
            output.append("<h4>Code Examples:</h4>")
            for i, example in enumerate(content.code_examples, 1):
                output.append(f"<h5>Example {i}:</h5>")
                output.append(self.format_code_example(example))
        
        if content.links:
            output.append("<h4>Useful Links:</h4>")
            output.append("<ul>")
            for link in content.links:
                if "http" in link:
                    # Extract URL and text if formatted as "text: url"
                    if ": " in link:
                        text, url = link.split(": ", 1)
                        output.append(f"<li><a href='{url}' target='_blank'>{text}</a></li>")
                    else:
                        output.append(f"<li><a href='{link}' target='_blank'>{link}</a></li>")
                else:
                    output.append(f"<li>{link}</li>")
            output.append("</ul>")
        
        output.append("</div>")
        return self._display_html("".join(output))
    
    def format_code_example(self, code: str, language: str = "python") -> str:
        """Format code example for Jupyter display."""
        escaped_code = code.replace('<', '&lt;').replace('>', '&gt;')
        return f"""
        <pre style='background-color: #f8f8f8; padding: 10px; border-radius: 5px; overflow-x: auto;'>
        <code class='language-{language}'>{escaped_code}</code>
        </pre>
        """
    
    def format_link(self, url: str, text: str = None) -> str:
        """Format a link for Jupyter display."""
        display_text = text or url
        return f"<a href='{url}' target='_blank'>{display_text}</a>"
    
    def _display_html(self, html_content: str) -> str:
        """Display HTML content in Jupyter."""
        try:
            from IPython.display import HTML, display
            display(HTML(html_content))
            return ""  # Content is displayed, return empty string
        except ImportError:
            # Fallback to plain text if IPython not available
            return html_content


class ContentDisplayManager:
    """Manager for displaying content across different environments."""
    
    def __init__(self):
        self.environment = EnvironmentDetector.detect()
        self.formatter = self._get_formatter()
    
    def _get_formatter(self) -> ContentFormatter:
        """Get appropriate formatter for current environment."""
        if self.environment.supports_html:
            return JupyterFormatter()
        else:
            return TerminalFormatter()
    
    def display_content(self, content: HelpContent) -> None:
        """Display content using appropriate formatter."""
        formatted_content = self.formatter.format_help_content(content)
        if formatted_content:  # Only print if there's content to print
            print(formatted_content)
    
    def display_code_example(self, code: str, language: str = "python") -> None:
        """Display a code example using appropriate formatter."""
        formatted_code = self.formatter.format_code_example(code, language)
        if self.environment.supports_html:
            try:
                from IPython.display import HTML, display
                display(HTML(formatted_code))
            except ImportError:
                print(formatted_code)
        else:
            print(formatted_code)
    
    def display_link(self, url: str, text: str = None) -> None:
        """Display a link using appropriate formatter."""
        formatted_link = self.formatter.format_link(url, text)
        if self.environment.supports_html:
            try:
                from IPython.display import HTML, display
                display(HTML(formatted_link))
            except ImportError:
                print(formatted_link)
        else:
            print(formatted_link)


# Global instance for easy access
_display_manager = None


def get_display_manager() -> ContentDisplayManager:
    """Get the global display manager instance."""
    global _display_manager
    if _display_manager is None:
        _display_manager = ContentDisplayManager()
    return _display_manager


def help() -> None:
    """
    Display HydroSim overview with environment-appropriate formatting.
    
    Shows library overview, main modules summary, and quick start guide.
    Automatically detects environment (terminal vs Jupyter) and formats output accordingly.
    """
    display_manager = get_display_manager()
    
    # Create comprehensive help content
    text_content = """HydroSim: A Python-based water resources planning framework

HydroSim provides tools for daily timestep simulation of complex, interconnected water systems.
It supports network-based modeling with nodes (storage, demand, source, junction) and links,
climate data integration, optimization-based allocation, and comprehensive results analysis.

MAIN MODULES:
• Nodes & Links: StorageNode, DemandNode, SourceNode, JunctionNode, Link
• Climate: ClimateEngine, WGENClimateSource, TimeSeriesClimateSource  
• Strategies: HydrologyStrategy, DemandModel, GeneratorStrategy
• Simulation: SimulationEngine, NetworkSolver
• Results: ResultsWriter, ResultsVisualizer
• Configuration: YAMLParser, NetworkGraph

QUICK START:
1. Define your network using YAML configuration or Python objects
2. Set up climate data sources (time series or weather generator)
3. Configure demand and hydrology strategies
4. Run simulation with SimulationEngine
5. Analyze results with ResultsWriter and visualization tools"""

    # Enhanced HTML content for Jupyter environments
    html_content = """
    <div style='font-family: Arial, sans-serif; max-width: 800px;'>
        <h2 style='color: #2E86AB; border-bottom: 2px solid #2E86AB; padding-bottom: 10px;'>
            🌊 HydroSim: Water Resources Planning Framework
        </h2>
        
        <p style='font-size: 16px; line-height: 1.6; color: #333;'>
            HydroSim provides tools for <strong>daily timestep simulation</strong> of complex, 
            interconnected water systems. It supports network-based modeling with nodes and links,
            climate data integration, optimization-based allocation, and comprehensive results analysis.
        </p>
        
        <h3 style='color: #A23B72; margin-top: 25px;'>🔧 Main Modules</h3>
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;'>
            <ul style='margin: 0; padding-left: 20px; line-height: 1.8;'>
                <li><strong>Nodes & Links:</strong> <code>StorageNode</code>, <code>DemandNode</code>, <code>SourceNode</code>, <code>JunctionNode</code>, <code>Link</code></li>
                <li><strong>Climate:</strong> <code>ClimateEngine</code>, <code>WGENClimateSource</code>, <code>TimeSeriesClimateSource</code></li>
                <li><strong>Strategies:</strong> <code>HydrologyStrategy</code>, <code>DemandModel</code>, <code>GeneratorStrategy</code></li>
                <li><strong>Simulation:</strong> <code>SimulationEngine</code>, <code>NetworkSolver</code></li>
                <li><strong>Results:</strong> <code>ResultsWriter</code>, <code>ResultsVisualizer</code></li>
                <li><strong>Configuration:</strong> <code>YAMLParser</code>, <code>NetworkGraph</code></li>
            </ul>
        </div>
        
        <h3 style='color: #A23B72; margin-top: 25px;'>🚀 Quick Start</h3>
        <div style='background-color: #e8f4f8; padding: 15px; border-radius: 8px; border-left: 4px solid #2E86AB;'>
            <ol style='margin: 0; padding-left: 20px; line-height: 1.8;'>
                <li>Define your network using YAML configuration or Python objects</li>
                <li>Set up climate data sources (time series or weather generator)</li>
                <li>Configure demand and hydrology strategies</li>
                <li>Run simulation with <code>SimulationEngine</code></li>
                <li>Analyze results with <code>ResultsWriter</code> and visualization tools</li>
            </ol>
        </div>
        
        <div style='margin-top: 20px; padding: 10px; background-color: #fff3cd; border-radius: 5px; border-left: 4px solid #ffc107;'>
            <strong>💡 Next Steps:</strong> Try <code>hydrosim.examples()</code> to see working code examples, 
            or <code>hydrosim.docs()</code> to access full documentation.
        </div>
    </div>
    """
    
    # Code examples for quick reference
    code_examples = [
        """# Basic network setup
import hydrosim as hs

# Load network from YAML
network = hs.YAMLParser.load_network('my_network.yaml')

# Create simulation engine
engine = hs.SimulationEngine(network)

# Run simulation
results = engine.run(start_date='2020-01-01', end_date='2020-12-31')""",
        
        """# Create nodes programmatically
storage = hs.StorageNode('reservoir', capacity=1000)
demand = hs.DemandNode('city', demand_strategy=hs.MunicipalDemand())
link = hs.Link('pipe', from_node=storage, to_node=demand)"""
    ]
    
    # Useful links
    links = [
        "Documentation: https://github.com/jlillywh/hydrosim#readme",
        "Examples: https://github.com/jlillywh/hydrosim/tree/main/examples",
        "Issues: https://github.com/jlillywh/hydrosim/issues"
    ]
    
    # Create and display help content
    help_content = HelpContent(
        text_content=text_content,
        html_content=html_content,
        code_examples=code_examples,
        links=links
    )
    
    display_manager.display_content(help_content)


def about() -> None:
    """
    Display version information and project details.
    
    Shows version, license, and project links with appropriate formatting
    for the current environment (terminal vs Jupyter).
    """
    display_manager = get_display_manager()
    
    # Import version from main package
    try:
        from hydrosim import __version__
        version = __version__
    except ImportError:
        version = "unknown"
    
    # Create about content
    text_content = f"""HydroSim v{version}

A Python framework for water resources planning with daily timestep simulation.

LICENSE: MIT License
AUTHOR: J. Lillywh
PYTHON: Requires Python >=3.8

PROJECT LINKS:
• Homepage: https://github.com/jlillywh/hydrosim
• Repository: https://github.com/jlillywh/hydrosim
• Documentation: https://github.com/jlillywh/hydrosim#readme
• Bug Reports: https://github.com/jlillywh/hydrosim/issues

KEYWORDS: hydrology, water-resources, simulation, optimization, network-flow, reservoir"""

    # Enhanced HTML content for Jupyter
    html_content = f"""
    <div style='font-family: Arial, sans-serif; max-width: 600px;'>
        <h2 style='color: #2E86AB; border-bottom: 2px solid #2E86AB; padding-bottom: 10px;'>
            🌊 HydroSim v{version}
        </h2>
        
        <p style='font-size: 16px; line-height: 1.6; color: #333; margin-bottom: 20px;'>
            A Python framework for <strong>water resources planning</strong> with daily timestep simulation.
        </p>
        
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;'>
            <h4 style='margin-top: 0; color: #A23B72;'>📋 Project Information</h4>
            <ul style='margin: 0; padding-left: 20px; line-height: 1.8;'>
                <li><strong>License:</strong> MIT License</li>
                <li><strong>Author:</strong> J. Lillywh</li>
                <li><strong>Python:</strong> Requires Python ≥3.8</li>
            </ul>
        </div>
        
        <div style='background-color: #e8f4f8; padding: 15px; border-radius: 8px; border-left: 4px solid #2E86AB;'>
            <h4 style='margin-top: 0; color: #A23B72;'>🔗 Project Links</h4>
            <ul style='margin: 0; padding-left: 20px; line-height: 1.8;'>
                <li><a href='https://github.com/jlillywh/hydrosim' target='_blank' style='color: #2E86AB; text-decoration: none;'>🏠 Homepage</a></li>
                <li><a href='https://github.com/jlillywh/hydrosim' target='_blank' style='color: #2E86AB; text-decoration: none;'>📦 Repository</a></li>
                <li><a href='https://github.com/jlillywh/hydrosim#readme' target='_blank' style='color: #2E86AB; text-decoration: none;'>📚 Documentation</a></li>
                <li><a href='https://github.com/jlillywh/hydrosim/issues' target='_blank' style='color: #2E86AB; text-decoration: none;'>🐛 Bug Reports</a></li>
            </ul>
        </div>
        
        <div style='margin-top: 15px; padding: 10px; background-color: #f0f0f0; border-radius: 5px; font-size: 14px;'>
            <strong>Keywords:</strong> hydrology, water-resources, simulation, optimization, network-flow, reservoir
        </div>
    </div>
    """
    
    # Create and display about content
    about_content = HelpContent(
        text_content=text_content,
        html_content=html_content
    )
    
    display_manager.display_content(about_content)


def docs() -> None:
    """
    Open documentation or display inline based on environment.
    
    For terminal environments: attempts to open documentation in default browser.
    For Jupyter environments: displays inline documentation links.
    Handles network connectivity gracefully with fallback options.
    """
    display_manager = get_display_manager()
    
    # Documentation URLs
    main_docs_url = "https://github.com/jlillywh/hydrosim#readme"
    examples_url = "https://github.com/jlillywh/hydrosim/tree/main/examples"
    api_url = "https://github.com/jlillywh/hydrosim"
    
    if display_manager.environment.is_terminal:
        # Terminal environment - try to open browser
        try:
            import webbrowser
            print("Opening HydroSim documentation in your default browser...")
            success = webbrowser.open(main_docs_url)
            if success:
                print(f"Documentation opened: {main_docs_url}")
            else:
                print("Could not open browser automatically.")
                print(f"Please visit: {main_docs_url}")
        except Exception as e:
            print("Could not open browser automatically.")
            print(f"Please visit: {main_docs_url}")
            print(f"Error: {e}")
    else:
        # Jupyter environment - display inline links
        html_content = f"""
        <div style='font-family: Arial, sans-serif; max-width: 700px;'>
            <h3 style='color: #2E86AB; border-bottom: 2px solid #2E86AB; padding-bottom: 10px;'>
                📚 HydroSim Documentation
            </h3>
            
            <div style='background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;'>
                <h4 style='margin-top: 0; color: #A23B72;'>📖 Main Documentation</h4>
                <p style='margin-bottom: 10px;'>
                    <a href='{main_docs_url}' target='_blank' style='color: #2E86AB; text-decoration: none; font-size: 16px;'>
                        🏠 HydroSim README & Getting Started Guide
                    </a>
                </p>
                <p style='color: #666; font-size: 14px; margin: 0;'>
                    Complete overview, installation instructions, and basic usage examples.
                </p>
            </div>
            
            <div style='background-color: #e8f4f8; padding: 20px; border-radius: 8px; margin: 15px 0;'>
                <h4 style='margin-top: 0; color: #A23B72;'>💻 Code Examples</h4>
                <p style='margin-bottom: 10px;'>
                    <a href='{examples_url}' target='_blank' style='color: #2E86AB; text-decoration: none; font-size: 16px;'>
                        📁 Examples Directory
                    </a>
                </p>
                <p style='color: #666; font-size: 14px; margin: 0;'>
                    Working Python scripts demonstrating key features and use cases.
                </p>
            </div>
            
            <div style='background-color: #fff3cd; padding: 20px; border-radius: 8px; margin: 15px 0;'>
                <h4 style='margin-top: 0; color: #A23B72;'>🔧 API Reference</h4>
                <p style='margin-bottom: 10px;'>
                    <a href='{api_url}' target='_blank' style='color: #2E86AB; text-decoration: none; font-size: 16px;'>
                        📦 Source Code & API
                    </a>
                </p>
                <p style='color: #666; font-size: 14px; margin: 0;'>
                    Browse source code, docstrings, and detailed API documentation.
                </p>
            </div>
            
            <div style='margin-top: 20px; padding: 15px; background-color: #d4edda; border-radius: 5px; border-left: 4px solid #28a745;'>
                <strong>💡 Tip:</strong> Use <code>help(hydrosim.ModuleName)</code> for detailed information about specific modules,
                or <code>hydrosim.examples()</code> to see code examples you can run directly.
            </div>
        </div>
        """
        
        docs_content = HelpContent(
            text_content=f"HydroSim Documentation Links:\n\n• Main Documentation: {main_docs_url}\n• Examples: {examples_url}\n• API Reference: {api_url}",
            html_content=html_content
        )
        
        display_manager.display_content(docs_content)


def examples() -> None:
    """
    List available examples with notebook-friendly display.
    
    Shows available example scripts with descriptions, inline code snippets
    for Jupyter environments, and execution guidance for different environments.
    """
    display_manager = get_display_manager()
    
    # Define example metadata
    example_info = [
        ExampleInfo(
            filename="quick_start.py",
            title="Quick Start Example",
            description="Complete workflow demonstration: load YAML config, run simulation, export results",
            category="Getting Started",
            difficulty="beginner",
            notebook_friendly=True,
            code_snippet="""# Quick start with HydroSim
from hydrosim.config import YAMLParser
from hydrosim import SimulationEngine, ResultsWriter

# Load network configuration
network = YAMLParser.load_network('examples/simple_network.yaml')

# Create and run simulation
engine = SimulationEngine(network)
results = engine.run(start_date='2020-01-01', end_date='2020-12-31')

# Export results
writer = ResultsWriter(results)
writer.write_all_csv('output/')"""
        ),
        ExampleInfo(
            filename="network_visualization_demo.py",
            title="Network Visualization",
            description="Create interactive network topology maps and flow diagrams",
            category="Visualization",
            difficulty="beginner",
            notebook_friendly=True,
            code_snippet="""# Visualize network topology
import hydrosim as hs

network = hs.YAMLParser.load_network('examples/simple_network.yaml')
hs.visualize_network(network, output_file='network_map.html')"""
        ),
        ExampleInfo(
            filename="wgen_example.py",
            title="Weather Generator",
            description="Use WGEN for stochastic climate data generation",
            category="Climate",
            difficulty="intermediate",
            notebook_friendly=True,
            code_snippet="""# Weather generation example
from hydrosim import WGENClimateSource, WGENParams

# Load weather generator parameters
params = WGENParams.from_csv('examples/wgen_params_template.csv')

# Create climate source
climate = WGENClimateSource(params, seed=42)"""
        ),
        ExampleInfo(
            filename="storage_drawdown_demo.py",
            title="Storage Drawdown Analysis",
            description="Analyze reservoir drawdown patterns and storage reliability",
            category="Analysis",
            difficulty="intermediate",
            notebook_friendly=True,
            code_snippet="""# Storage analysis
from hydrosim import SimulationEngine, ResultsVisualizer

# Run simulation and analyze storage
engine = SimulationEngine(network)
results = engine.run(start_date='2020-01-01', end_date='2025-12-31')

# Visualize storage patterns
viz = ResultsVisualizer(results)
viz.plot_storage_timeseries('reservoir')"""
        ),
        ExampleInfo(
            filename="complex_network.yaml",
            title="Complex Network Configuration",
            description="Multi-reservoir system with various demand types and controls",
            category="Configuration",
            difficulty="advanced",
            notebook_friendly=False,
            code_snippet="""# Load complex network
network = hs.YAMLParser.load_network('examples/complex_network.yaml')

# Inspect network structure
print(f"Nodes: {len(network.nodes)}")
print(f"Links: {len(network.links)}")"""
        )
    ]
    
    if display_manager.environment.is_terminal:
        # Terminal display
        text_content = "HydroSim Examples\n" + "=" * 50 + "\n\n"
        
        categories = {}
        for example in example_info:
            if example.category not in categories:
                categories[example.category] = []
            categories[example.category].append(example)
        
        for category, examples in categories.items():
            text_content += f"{category.upper()}:\n" + "-" * 30 + "\n"
            for example in examples:
                text_content += f"• {example.title} ({example.filename})\n"
                text_content += f"  {example.description}\n"
                text_content += f"  Difficulty: {example.difficulty}\n\n"
        
        text_content += "\nEXECUTION:\n" + "-" * 30 + "\n"
        text_content += "Run examples from the project root directory:\n"
        text_content += "  python examples/quick_start.py\n"
        text_content += "  python examples/network_visualization_demo.py\n\n"
        text_content += "Or explore the examples/ directory for YAML configurations."
        
        examples_content = HelpContent(text_content=text_content)
        display_manager.display_content(examples_content)
        
    else:
        # Jupyter display with rich formatting and code snippets
        html_content = """
        <div style='font-family: Arial, sans-serif; max-width: 900px;'>
            <h2 style='color: #2E86AB; border-bottom: 2px solid #2E86AB; padding-bottom: 10px;'>
                📁 HydroSim Examples
            </h2>
            <p style='font-size: 16px; color: #333; margin-bottom: 25px;'>
                Working examples demonstrating key HydroSim features. Click the code snippets to copy them!
            </p>
        """
        
        # Group examples by category
        categories = {}
        for example in example_info:
            if example.category not in categories:
                categories[example.category] = []
            categories[example.category].append(example)
        
        category_colors = {
            "Getting Started": "#28a745",
            "Visualization": "#17a2b8", 
            "Climate": "#ffc107",
            "Analysis": "#6f42c1",
            "Configuration": "#fd7e14"
        }
        
        for category, examples in categories.items():
            color = category_colors.get(category, "#6c757d")
            html_content += f"""
            <h3 style='color: {color}; margin-top: 30px; margin-bottom: 15px;'>
                {category}
            </h3>
            """
            
            for example in examples:
                difficulty_badge_color = {
                    "beginner": "#28a745",
                    "intermediate": "#ffc107", 
                    "advanced": "#dc3545"
                }.get(example.difficulty, "#6c757d")
                
                html_content += f"""
                <div style='background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid {color};'>
                    <h4 style='margin-top: 0; color: #333;'>
                        {example.title}
                        <span style='background-color: {difficulty_badge_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px;'>
                            {example.difficulty}
                        </span>
                    </h4>
                    <p style='color: #666; margin-bottom: 15px;'>{example.description}</p>
                    <p style='font-size: 14px; color: #888; margin-bottom: 10px;'>
                        📄 <code>{example.filename}</code>
                    </p>
                """
                
                if example.notebook_friendly and example.code_snippet:
                    escaped_code = example.code_snippet.replace('<', '&lt;').replace('>', '&gt;')
                    html_content += f"""
                    <details style='margin-top: 10px;'>
                        <summary style='cursor: pointer; color: {color}; font-weight: bold;'>
                            💻 Show Code Snippet
                        </summary>
                        <pre style='background-color: #f1f3f4; padding: 15px; border-radius: 5px; overflow-x: auto; margin-top: 10px; font-size: 13px;'>
<code>{escaped_code}</code>
                        </pre>
                    </details>
                    """
                
                html_content += "</div>"
        
        html_content += """
            <div style='margin-top: 30px; padding: 20px; background-color: #e8f4f8; border-radius: 8px; border-left: 4px solid #2E86AB;'>
                <h4 style='margin-top: 0; color: #A23B72;'>🚀 Running Examples</h4>
                <p style='margin-bottom: 10px;'><strong>In Jupyter:</strong> Copy code snippets above and run in cells</p>
                <p style='margin-bottom: 10px;'><strong>From Terminal:</strong> <code>python examples/quick_start.py</code></p>
                <p style='margin: 0;'><strong>Browse Files:</strong> 
                    <a href='https://github.com/jlillywh/hydrosim/tree/main/examples' target='_blank' style='color: #2E86AB;'>
                        View all examples on GitHub
                    </a>
                </p>
            </div>
        </div>
        """
        
        examples_content = HelpContent(
            text_content="See examples above",
            html_content=html_content
        )
        
        display_manager.display_content(examples_content)


def quick_start() -> None:
    """
    Interactive getting started guide optimized for notebooks.
    
    Provides a step-by-step tutorial suitable for notebook execution with
    executable code cells, explanations, and sample data examples.
    """
    display_manager = get_display_manager()
    
    if display_manager.environment.is_terminal:
        # Terminal version - simplified text-based tutorial
        text_content = """HydroSim Quick Start Tutorial

This tutorial will guide you through creating and running your first water network simulation.

STEP 1: INSTALL HYDROSIM
------------------------
If you haven't already installed HydroSim:
    pip install hydrosim

STEP 2: BASIC IMPORTS
---------------------
Start by importing the essential modules:

    import hydrosim as hs
    from hydrosim.config import YAMLParser
    from hydrosim import SimulationEngine, ResultsWriter

STEP 3: LOAD A NETWORK
----------------------
Load a pre-configured network from YAML:

    # Load the simple example network
    parser = YAMLParser('examples/simple_network.yaml')
    network, climate_source, site_config = parser.parse()
    
    # Validate the network
    errors = network.validate()
    if errors:
        print("Network validation errors:", errors)
    else:
        print("Network is valid!")

STEP 4: SET UP SIMULATION
-------------------------
Create the simulation engine:

    from hydrosim import ClimateEngine
    from datetime import datetime
    
    # Create climate engine
    climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
    
    # Create simulation engine
    engine = SimulationEngine(network, climate_engine)

STEP 5: RUN SIMULATION
----------------------
Run the simulation and capture results:

    # Create results writer
    writer = ResultsWriter(output_dir="output", format="csv")
    
    # Run simulation for 30 days
    for day in range(30):
        result = engine.step()
        writer.add_timestep(result)
        
        if day % 10 == 0:  # Print progress every 10 days
            storage = result['node_states']['reservoir']['storage']
            print(f"Day {day + 1}: Storage = {storage:,.1f} m³")

STEP 6: EXPORT RESULTS
----------------------
Save results to files:

    # Write all results to CSV files
    files = writer.write_all(prefix="my_simulation")
    for file_type, filepath in files.items():
        print(f"{file_type}: {filepath}")

NEXT STEPS:
-----------
• Run 'python examples/quick_start.py' for a complete working example
• Try 'hydrosim.examples()' to see more code examples
• Modify 'examples/simple_network.yaml' to create your own network
• Use 'hydrosim.docs()' to access full documentation

For more detailed guidance, run this tutorial in a Jupyter notebook for interactive code cells."""
        
        quick_start_content = HelpContent(text_content=text_content)
        display_manager.display_content(quick_start_content)
        
    else:
        # Jupyter version - rich interactive tutorial with executable code cells
        html_content = """
        <div style='font-family: Arial, sans-serif; max-width: 1000px;'>
            <h1 style='color: #2E86AB; border-bottom: 3px solid #2E86AB; padding-bottom: 15px;'>
                🚀 HydroSim Quick Start Tutorial
            </h1>
            
            <div style='background-color: #e8f4f8; padding: 20px; border-radius: 8px; border-left: 4px solid #2E86AB; margin-bottom: 25px;'>
                <h3 style='margin-top: 0; color: #A23B72;'>Welcome to HydroSim!</h3>
                <p style='margin-bottom: 0; font-size: 16px; line-height: 1.6;'>
                    This interactive tutorial will guide you through creating and running your first water network simulation.
                    Each code cell below can be copied and executed in your notebook.
                </p>
            </div>
            
            <h2 style='color: #A23B72; margin-top: 35px;'>📦 Step 1: Install and Import</h2>
            <p>First, make sure HydroSim is installed and import the essential modules:</p>
        """
        
        # Step 1 code
        step1_code = """# Install HydroSim (run this if not already installed)
# !pip install hydrosim

# Essential imports
import hydrosim as hs
from hydrosim.config import YAMLParser
from hydrosim import SimulationEngine, ResultsWriter, ClimateEngine
from datetime import datetime
import os

print("✓ HydroSim imported successfully!")
print(f"Version: {hs.__version__ if hasattr(hs, '__version__') else 'unknown'}")"""
        
        html_content += f"""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;'>
                <pre style='margin: 0; font-size: 13px; overflow-x: auto;'><code>{step1_code}</code></pre>
            </div>
            
            <h2 style='color: #A23B72; margin-top: 35px;'>🏗️ Step 2: Create Sample Data</h2>
            <p>Let's create some sample data files to work with:</p>
        """
        
        # Step 2 code
        step2_code = """# Create sample climate data
import pandas as pd
import numpy as np

# Create output directory
os.makedirs('tutorial_output', exist_ok=True)

# Generate 30 days of sample climate data
dates = pd.date_range('2024-01-01', periods=30, freq='D')
climate_data = pd.DataFrame({
    'date': dates,
    'precip': np.random.exponential(2.0, 30),  # Precipitation (mm/day)
    't_max': 15 + 10 * np.sin(np.arange(30) * 2 * np.pi / 365) + np.random.normal(0, 2, 30),  # Max temp
    't_min': 5 + 8 * np.sin(np.arange(30) * 2 * np.pi / 365) + np.random.normal(0, 1.5, 30),   # Min temp
    'solar': 15 + 5 * np.sin(np.arange(30) * 2 * np.pi / 365) + np.random.normal(0, 1, 30)     # Solar radiation
})

# Generate sample inflow data
inflow_data = pd.DataFrame({
    'date': dates,
    'inflow': 1000 + 500 * np.sin(np.arange(30) * 2 * np.pi / 365) + np.random.normal(0, 100, 30)
})

# Save to CSV files
climate_data.to_csv('tutorial_output/climate_data.csv', index=False)
inflow_data.to_csv('tutorial_output/inflow_data.csv', index=False)

print("✓ Sample data files created:")
print("  - tutorial_output/climate_data.csv")
print("  - tutorial_output/inflow_data.csv")
print(f"\\nClimate data preview:")
print(climate_data.head())"""
        
        html_content += f"""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;'>
                <pre style='margin: 0; font-size: 13px; overflow-x: auto;'><code>{step2_code}</code></pre>
            </div>
            
            <h2 style='color: #A23B72; margin-top: 35px;'>⚙️ Step 3: Create Network Configuration</h2>
            <p>Now let's create a simple water network configuration:</p>
        """
        
        # Step 3 code
        step3_code = """# Create a simple network configuration
network_config = '''
model_name: "Tutorial Water Network"
author: "HydroSim Tutorial"

climate:
  source_type: timeseries
  filepath: tutorial_output/climate_data.csv
  site:
    latitude: 45.0
    elevation: 1000.0

nodes:
  # Source node (catchment inflow)
  catchment:
    type: source
    strategy: timeseries
    filepath: tutorial_output/inflow_data.csv
    column: inflow
  
  # Storage reservoir
  reservoir:
    type: storage
    initial_storage: 25000.0  # m³
    max_storage: 50000.0      # m³
    min_storage: 0.0          # m³
    eav_table:
      elevations: [100.0, 110.0, 120.0]  # meters
      areas: [1000.0, 2000.0, 3000.0]    # m²
      volumes: [0.0, 25000.0, 50000.0]   # m³
  
  # Municipal demand
  city:
    type: demand
    demand_type: municipal
    population: 5000.0         # people
    per_capita_demand: 0.3     # m³/person/day

links:
  # Inflow to reservoir
  catchment_to_reservoir:
    source: catchment
    target: reservoir
    capacity: 5000.0  # m³/day
    cost: 0.0
  
  # Reservoir to city
  reservoir_to_city:
    source: reservoir
    target: city
    capacity: 2000.0  # m³/day
'''

# Save configuration to file
with open('tutorial_output/tutorial_network.yaml', 'w') as f:
    f.write(network_config)

print("✓ Network configuration created: tutorial_output/tutorial_network.yaml")
print("\\nNetwork includes:")
print("  - 1 source node (catchment)")
print("  - 1 storage node (reservoir)")  
print("  - 1 demand node (city)")
print("  - 2 links connecting them")"""
        
        html_content += f"""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;'>
                <pre style='margin: 0; font-size: 13px; overflow-x: auto;'><code>{step3_code}</code></pre>
            </div>
            
            <h2 style='color: #A23B72; margin-top: 35px;'>🔧 Step 4: Load and Validate Network</h2>
            <p>Load the network configuration and validate it:</p>
        """
        
        # Step 4 code
        step4_code = """# Load network from YAML configuration
parser = YAMLParser('tutorial_output/tutorial_network.yaml')
network, climate_source, site_config = parser.parse()

print(f"✓ Network loaded successfully!")
print(f"  Nodes: {len(network.nodes)}")
print(f"  Links: {len(network.links)}")

# List nodes by type
node_types = {}
for node in network.nodes.values():
    node_type = node.node_type
    node_types[node_type] = node_types.get(node_type, 0) + 1

print("\\nNode composition:")
for node_type, count in sorted(node_types.items()):
    print(f"  - {count} {node_type} node(s)")

# Validate network topology
print("\\nValidating network...")
errors = network.validate()
if errors:
    print("❌ Validation errors found:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✅ Network topology is valid!")"""
        
        html_content += f"""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;'>
                <pre style='margin: 0; font-size: 13px; overflow-x: auto;'><code>{step4_code}</code></pre>
            </div>
            
            <h2 style='color: #A23B72; margin-top: 35px;'>🎯 Step 5: Set Up and Run Simulation</h2>
            <p>Create the simulation engine and run the simulation:</p>
        """
        
        # Step 5 code
        step5_code = """# Set up simulation engine
climate_engine = ClimateEngine(climate_source, site_config, datetime(2024, 1, 1))
engine = SimulationEngine(network, climate_engine)

print("✓ Simulation engine initialized")

# Create results writer
writer = ResultsWriter(output_dir="tutorial_output", format="csv")
print("✓ Results writer ready")

# Run simulation
print("\\n🏃 Running simulation for 30 days...")
print("Day | Storage (m³) | Inflow (m³/day) | Demand (m³/day) | Deficit (m³/day)")
print("-" * 75)

for day in range(30):
    result = engine.step()
    writer.add_timestep(result)
    
    # Extract key values for display
    storage = result['node_states']['reservoir']['storage']
    inflow = result['node_states']['catchment']['inflow']
    demand = result['node_states']['city']['request']
    deficit = result['node_states']['city']['deficit']
    
    # Print progress every 5 days
    if day % 5 == 0 or day == 29:
        print(f"{day+1:3d} | {storage:11,.0f} | {inflow:13,.0f} | {demand:14,.0f} | {deficit:14,.1f}")

print("\\n✅ Simulation completed successfully!")"""
        
        html_content += f"""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;'>
                <pre style='margin: 0; font-size: 13px; overflow-x: auto;'><code>{step5_code}</code></pre>
            </div>
            
            <h2 style='color: #A23B72; margin-top: 35px;'>📊 Step 6: Export and Analyze Results</h2>
            <p>Save results to files and perform basic analysis:</p>
        """
        
        # Step 6 code
        step6_code = """# Export results to CSV files
files = writer.write_all(prefix="tutorial")
print("📁 Results exported to:")
for file_type, filepath in files.items():
    print(f"  - {file_type}: {filepath}")

# Basic analysis
results = writer.get_results()
print(f"\\n📈 Simulation Summary (30 days):")
print("=" * 50)

# Storage analysis
initial_storage = results[0]['node_states']['reservoir']['storage']
final_storage = results[-1]['node_states']['reservoir']['storage']
max_storage = max(r['node_states']['reservoir']['storage'] for r in results)
min_storage = min(r['node_states']['reservoir']['storage'] for r in results)

print(f"Storage Analysis:")
print(f"  Initial: {initial_storage:,.0f} m³")
print(f"  Final:   {final_storage:,.0f} m³")
print(f"  Maximum: {max_storage:,.0f} m³")
print(f"  Minimum: {min_storage:,.0f} m³")
print(f"  Change:  {final_storage - initial_storage:+,.0f} m³")

# Demand analysis
total_demand = sum(r['node_states']['city']['request'] for r in results)
total_delivered = sum(r['node_states']['city']['delivered'] for r in results)
total_deficit = sum(r['node_states']['city']['deficit'] for r in results)
reliability = (total_delivered / total_demand * 100) if total_demand > 0 else 0

print(f"\\nDemand Analysis:")
print(f"  Total requested: {total_demand:,.0f} m³")
print(f"  Total delivered: {total_delivered:,.0f} m³")
print(f"  Total deficit:   {total_deficit:,.0f} m³")
print(f"  Reliability:     {reliability:.1f}%")

# Inflow analysis
total_inflow = sum(r['node_states']['catchment']['inflow'] for r in results)
avg_inflow = total_inflow / len(results)

print(f"\\nInflow Analysis:")
print(f"  Total inflow:    {total_inflow:,.0f} m³")
print(f"  Average inflow:  {avg_inflow:,.0f} m³/day")"""
        
        html_content += f"""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;'>
                <pre style='margin: 0; font-size: 13px; overflow-x: auto;'><code>{step6_code}</code></pre>
            </div>
            
            <h2 style='color: #A23B72; margin-top: 35px;'>📈 Step 7: Visualize Results (Optional)</h2>
            <p>Create simple plots to visualize the simulation results:</p>
        """
        
        # Step 7 code
        step7_code = """# Optional: Create simple plots with matplotlib
try:
    import matplotlib.pyplot as plt
    
    # Extract time series data
    days = list(range(1, 31))
    storage_values = [r['node_states']['reservoir']['storage'] for r in results]
    inflow_values = [r['node_states']['catchment']['inflow'] for r in results]
    demand_values = [r['node_states']['city']['request'] for r in results]
    deficit_values = [r['node_states']['city']['deficit'] for r in results]
    
    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('HydroSim Tutorial Results', fontsize=16, fontweight='bold')
    
    # Storage plot
    ax1.plot(days, storage_values, 'b-', linewidth=2, label='Storage')
    ax1.set_title('Reservoir Storage')
    ax1.set_xlabel('Day')
    ax1.set_ylabel('Storage (m³)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Inflow plot
    ax2.plot(days, inflow_values, 'g-', linewidth=2, label='Inflow')
    ax2.set_title('Catchment Inflow')
    ax2.set_xlabel('Day')
    ax2.set_ylabel('Inflow (m³/day)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Demand vs delivery
    ax3.plot(days, demand_values, 'r-', linewidth=2, label='Demand')
    delivered_values = [d - def_val for d, def_val in zip(demand_values, deficit_values)]
    ax3.plot(days, delivered_values, 'orange', linewidth=2, label='Delivered')
    ax3.set_title('Water Demand vs Delivery')
    ax3.set_xlabel('Day')
    ax3.set_ylabel('Flow (m³/day)')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Deficit plot
    ax4.plot(days, deficit_values, 'red', linewidth=2, label='Deficit')
    ax4.set_title('Water Deficit')
    ax4.set_xlabel('Day')
    ax4.set_ylabel('Deficit (m³/day)')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('tutorial_output/tutorial_results.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    print("✅ Plots created and saved to tutorial_output/tutorial_results.png")
    
except ImportError:
    print("📊 Matplotlib not available - install with: pip install matplotlib")
    print("    You can still view the CSV results in tutorial_output/")"""
        
        html_content += f"""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;'>
                <pre style='margin: 0; font-size: 13px; overflow-x: auto;'><code>{step7_code}</code></pre>
            </div>
            
            <div style='background-color: #d4edda; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745; margin-top: 30px;'>
                <h3 style='margin-top: 0; color: #155724;'>🎉 Congratulations!</h3>
                <p style='margin-bottom: 15px; font-size: 16px;'>
                    You've successfully completed the HydroSim tutorial! You now know how to:
                </p>
                <ul style='margin-bottom: 15px; padding-left: 20px;'>
                    <li>Create sample data and network configurations</li>
                    <li>Load and validate water network models</li>
                    <li>Run simulations and capture results</li>
                    <li>Export data and perform basic analysis</li>
                    <li>Visualize simulation results</li>
                </ul>
            </div>
            
            <div style='background-color: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; margin-top: 20px;'>
                <h3 style='margin-top: 0; color: #856404;'>🚀 Next Steps</h3>
                <ul style='margin: 0; padding-left: 20px;'>
                    <li><strong>Explore Examples:</strong> Try <code>hydrosim.examples()</code> for more advanced scenarios</li>
                    <li><strong>Read Documentation:</strong> Use <code>hydrosim.docs()</code> for comprehensive guides</li>
                    <li><strong>Modify Networks:</strong> Edit the YAML configuration to add more nodes and links</li>
                    <li><strong>Try Real Data:</strong> Replace sample data with your own climate and inflow data</li>
                    <li><strong>Advanced Features:</strong> Explore weather generation, optimization, and visualization</li>
                </ul>
            </div>
        </div>
        """
        
        quick_start_content = HelpContent(
            text_content="Interactive tutorial for Jupyter notebooks - see HTML output above",
            html_content=html_content
        )
        
        display_manager.display_content(quick_start_content)