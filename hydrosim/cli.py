"""
CLI module for HydroSim terminal access.

This module provides command-line interface functionality for HydroSim,
allowing users to access help, examples, and project information from the terminal.
"""

import sys
import argparse
from typing import Optional, List

# Import help system functions to reuse
from hydrosim.help import help, about, docs, examples


def main() -> None:
    """
    Main CLI entry point for HydroSim console script.
    
    Handles command-line argument parsing and dispatches to appropriate
    command handlers that reuse the help system functions.
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Dispatch to appropriate command handler
    try:
        if args.command == 'help' or args.command is None:
            show_help()
        elif args.command == 'examples':
            list_examples()
        elif args.command == 'about':
            show_about()
        elif args.command == 'docs':
            open_docs()
        else:
            # Default to help if no valid command
            show_help()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for CLI commands.
    
    Returns:
        argparse.ArgumentParser: Configured parser with all CLI commands
    """
    parser = argparse.ArgumentParser(
        prog='hydrosim',
        description='HydroSim: A Python framework for water resources planning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,  # Disable default help to add custom help
        epilog="""
Examples:
  hydrosim --help      Show comprehensive help information
  hydrosim --examples  List available example scripts
  hydrosim --about     Display version and project information
  hydrosim --docs      Open documentation in browser

For more information, visit: https://github.com/jlillywh/hydrosim
        """
    )
    
    # Add custom help argument
    parser.add_argument(
        '--help', '-h',
        action='store_const',
        const='help',
        dest='command',
        help='Show comprehensive help information and quick start guide'
    )
    
    parser.add_argument(
        '--examples', '-e',
        action='store_const',
        const='examples',
        dest='command',
        help='List available example scripts with descriptions'
    )
    
    parser.add_argument(
        '--about', '-a',
        action='store_const',
        const='about',
        dest='command',
        help='Display version information, license, and project links'
    )
    
    parser.add_argument(
        '--docs', '-d',
        action='store_const',
        const='docs',
        dest='command',
        help='Open documentation in default browser'
    )
    
    return parser


def show_help() -> None:
    """
    Display comprehensive help information using the help system.
    
    Reuses the help() function from hydrosim.help module to provide
    consistent help content across CLI and Python interfaces.
    """
    print("HydroSim Command Line Interface")
    print("=" * 50)
    print()
    
    # Call the main help function from help system
    help()
    
    print()
    print("CLI COMMANDS:")
    print("-" * 30)
    print("  hydrosim --help      Show this help information")
    print("  hydrosim --examples  List available examples")
    print("  hydrosim --about     Show version and project info")
    print("  hydrosim --docs      Open documentation in browser")
    print()
    print("For Python usage: import hydrosim; hydrosim.help()")


def list_examples() -> None:
    """
    List available example scripts with descriptions.
    
    Reuses the examples() function from hydrosim.help module to provide
    consistent example information across CLI and Python interfaces.
    """
    print("HydroSim Examples")
    print("=" * 50)
    print()
    
    # Call the examples function from help system
    examples()
    
    print()
    print("USAGE:")
    print("-" * 30)
    print("Run examples from the project root directory:")
    print("  python examples/quick_start.py")
    print("  python examples/network_visualization_demo.py")
    print()
    print("Or explore the examples/ directory for YAML configurations.")


def show_about() -> None:
    """
    Display version and project information.
    
    Reuses the about() function from hydrosim.help module to provide
    consistent project information across CLI and Python interfaces.
    """
    print("HydroSim Project Information")
    print("=" * 50)
    print()
    
    # Call the about function from help system
    about()


def open_docs() -> None:
    """
    Open documentation in browser or display links.
    
    Reuses the docs() function from hydrosim.help module to provide
    consistent documentation access across CLI and Python interfaces.
    """
    print("HydroSim Documentation")
    print("=" * 50)
    print()
    
    # Call the docs function from help system
    docs()


if __name__ == '__main__':
    main()