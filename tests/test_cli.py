"""
Tests for CLI module functionality.

Tests the command-line interface for HydroSim, including argument parsing,
command handling, and integration with the help system.
"""

import pytest
import sys
import argparse
from unittest.mock import patch, MagicMock, call
from io import StringIO

# Import the CLI module
from hydrosim.cli import (
    main, create_argument_parser, show_help, list_examples, 
    show_about, open_docs
)


class TestArgumentParser:
    """Test argument parser creation and configuration."""
    
    def test_parser_creation(self):
        """Test that argument parser is created with correct configuration."""
        parser = create_argument_parser()
        
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.prog == 'hydrosim'
        assert 'water resources planning' in parser.description
        assert 'github.com/jlillywh/hydrosim' in parser.epilog
    
    def test_help_argument(self):
        """Test --help and -h argument parsing."""
        parser = create_argument_parser()
        
        args = parser.parse_args(['--help'])
        assert args.command == 'help'
        
        args = parser.parse_args(['-h'])
        assert args.command == 'help'
    
    def test_examples_argument(self):
        """Test --examples and -e argument parsing."""
        parser = create_argument_parser()
        
        args = parser.parse_args(['--examples'])
        assert args.command == 'examples'
        
        args = parser.parse_args(['-e'])
        assert args.command == 'examples'
    
    def test_about_argument(self):
        """Test --about and -a argument parsing."""
        parser = create_argument_parser()
        
        args = parser.parse_args(['--about'])
        assert args.command == 'about'
        
        args = parser.parse_args(['-a'])
        assert args.command == 'about'
    
    def test_docs_argument(self):
        """Test --docs and -d argument parsing."""
        parser = create_argument_parser()
        
        args = parser.parse_args(['--docs'])
        assert args.command == 'docs'
        
        args = parser.parse_args(['-d'])
        assert args.command == 'docs'
    
    def test_no_arguments(self):
        """Test parsing with no arguments."""
        parser = create_argument_parser()
        
        args = parser.parse_args([])
        assert args.command is None


class TestCommandHandlers:
    """Test individual command handler functions."""
    
    @patch('hydrosim.cli.help')
    @patch('sys.stdout', new_callable=StringIO)
    def test_show_help(self, mock_stdout, mock_help):
        """Test show_help function calls help system and displays CLI info."""
        show_help()
        
        # Verify help() function was called
        mock_help.assert_called_once()
        
        # Verify CLI-specific content was printed
        output = mock_stdout.getvalue()
        assert 'HydroSim Command Line Interface' in output
        assert 'CLI COMMANDS:' in output
        assert 'hydrosim --help' in output
        assert 'hydrosim --examples' in output
    
    @patch('hydrosim.cli.examples')
    @patch('sys.stdout', new_callable=StringIO)
    def test_list_examples(self, mock_stdout, mock_examples):
        """Test list_examples function calls help system and displays usage info."""
        list_examples()
        
        # Verify examples() function was called
        mock_examples.assert_called_once()
        
        # Verify CLI-specific content was printed
        output = mock_stdout.getvalue()
        assert 'HydroSim Examples' in output
        assert 'USAGE:' in output
        assert 'python examples/' in output
    
    @patch('hydrosim.cli.about')
    @patch('sys.stdout', new_callable=StringIO)
    def test_show_about(self, mock_stdout, mock_about):
        """Test show_about function calls help system."""
        show_about()
        
        # Verify about() function was called
        mock_about.assert_called_once()
        
        # Verify header was printed
        output = mock_stdout.getvalue()
        assert 'HydroSim Project Information' in output
    
    @patch('hydrosim.cli.docs')
    @patch('sys.stdout', new_callable=StringIO)
    def test_open_docs(self, mock_stdout, mock_docs):
        """Test open_docs function calls help system."""
        open_docs()
        
        # Verify docs() function was called
        mock_docs.assert_called_once()
        
        # Verify header was printed
        output = mock_stdout.getvalue()
        assert 'HydroSim Documentation' in output


class TestMainFunction:
    """Test main CLI entry point function."""
    
    @patch('hydrosim.cli.show_help')
    @patch('sys.argv', ['hydrosim'])
    def test_main_no_args_calls_help(self, mock_show_help):
        """Test main() calls show_help when no arguments provided."""
        main()
        mock_show_help.assert_called_once()
    
    @patch('hydrosim.cli.show_help')
    @patch('sys.argv', ['hydrosim', '--help'])
    def test_main_help_command(self, mock_show_help):
        """Test main() calls show_help for --help command."""
        main()
        mock_show_help.assert_called_once()
    
    @patch('hydrosim.cli.list_examples')
    @patch('sys.argv', ['hydrosim', '--examples'])
    def test_main_examples_command(self, mock_list_examples):
        """Test main() calls list_examples for --examples command."""
        main()
        mock_list_examples.assert_called_once()
    
    @patch('hydrosim.cli.show_about')
    @patch('sys.argv', ['hydrosim', '--about'])
    def test_main_about_command(self, mock_show_about):
        """Test main() calls show_about for --about command."""
        main()
        mock_show_about.assert_called_once()
    
    @patch('hydrosim.cli.open_docs')
    @patch('sys.argv', ['hydrosim', '--docs'])
    def test_main_docs_command(self, mock_open_docs):
        """Test main() calls open_docs for --docs command."""
        main()
        mock_open_docs.assert_called_once()
    
    @patch('hydrosim.cli.show_help')
    @patch('sys.argv', ['hydrosim', '--invalid'])
    def test_main_invalid_command_calls_help(self, mock_show_help):
        """Test main() calls show_help for invalid commands."""
        # This will raise SystemExit due to argparse, but we can catch it
        with pytest.raises(SystemExit):
            main()
        # show_help should not be called because argparse exits first
        mock_show_help.assert_not_called()
    
    @patch('hydrosim.cli.show_help')
    @patch('sys.argv', ['hydrosim'])
    @patch('builtins.print')
    def test_main_keyboard_interrupt(self, mock_print, mock_show_help):
        """Test main() handles KeyboardInterrupt gracefully."""
        mock_show_help.side_effect = KeyboardInterrupt()
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        mock_print.assert_called_with("\nOperation cancelled by user.")
    
    @patch('hydrosim.cli.show_help')
    @patch('sys.argv', ['hydrosim'])
    @patch('builtins.print')
    def test_main_exception_handling(self, mock_print, mock_show_help):
        """Test main() handles exceptions gracefully."""
        mock_show_help.side_effect = Exception("Test error")
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        mock_print.assert_called_with("Error: Test error")


class TestCLIIntegration:
    """Test CLI integration with help system."""
    
    def test_all_command_handlers_exist(self):
        """Test that all required command handler functions exist."""
        assert callable(show_help)
        assert callable(list_examples)
        assert callable(show_about)
        assert callable(open_docs)
        assert callable(main)
    
    @patch('hydrosim.cli.help')
    @patch('hydrosim.cli.about')
    @patch('hydrosim.cli.docs')
    @patch('hydrosim.cli.examples')
    def test_help_system_integration(self, mock_examples, mock_docs, mock_about, mock_help):
        """Test that CLI properly integrates with help system functions."""
        # Test each command handler calls the appropriate help function
        show_help()
        mock_help.assert_called_once()
        
        show_about()
        mock_about.assert_called_once()
        
        open_docs()
        mock_docs.assert_called_once()
        
        list_examples()
        mock_examples.assert_called_once()