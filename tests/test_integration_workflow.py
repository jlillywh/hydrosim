"""
Integration tests for complete HydroSim workflow across different environments.

Tests the complete developer experience workflow including CLI commands,
help functions, package installation, and console script registration.
This validates Requirements: All from the developer-experience-improvements spec.
"""

import pytest
import subprocess
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from io import StringIO
import importlib.util

# Import modules to test
import hydrosim
from hydrosim import cli
import sys
import importlib
help_module = importlib.import_module('hydrosim.help')


class TestCLIWorkflow:
    """Test CLI commands work correctly in terminal environment."""
    
    def test_cli_help_command_produces_complete_output(self):
        """Test hydrosim --help produces comprehensive output."""
        # Test CLI help command
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('sys.argv', ['hydrosim', '--help']):
                cli.main()
        
        output = mock_stdout.getvalue()
        
        # Verify all required sections are present
        assert 'HydroSim Command Line Interface' in output
        assert 'HydroSim: A Python-based water resources planning framework' in output
        assert 'MAIN MODULES:' in output
        assert 'QUICK START:' in output
        assert 'CLI COMMANDS:' in output
        assert 'hydrosim --help' in output
        assert 'hydrosim --examples' in output
        assert 'hydrosim --about' in output
        assert 'hydrosim --docs' in output
    
    def test_cli_examples_command_produces_complete_output(self):
        """Test hydrosim --examples produces comprehensive output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('sys.argv', ['hydrosim', '--examples']):
                cli.main()
        
        output = mock_stdout.getvalue()
        
        # Verify examples content is present
        assert 'HydroSim Examples' in output
        assert 'Quick Start Example' in output
        assert 'Network Visualization' in output
        assert 'Weather Generator' in output
        assert 'USAGE:' in output
        assert 'python examples/' in output
    
    def test_cli_about_command_produces_complete_output(self):
        """Test hydrosim --about produces comprehensive output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('sys.argv', ['hydrosim', '--about']):
                cli.main()
        
        output = mock_stdout.getvalue()
        
        # Verify about content is present
        assert 'HydroSim Project Information' in output
        assert 'HydroSim v' in output
        assert 'LICENSE: MIT License' in output
        assert 'AUTHOR: J. Lillywh' in output
        assert 'PROJECT LINKS:' in output
        assert 'github.com/jlillywh/hydrosim' in output
    
    def test_cli_docs_command_produces_complete_output(self):
        """Test hydrosim --docs produces comprehensive output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('sys.argv', ['hydrosim', '--docs']):
                # Mock webbrowser to avoid actually opening browser
                with patch('webbrowser.open', return_value=True):
                    cli.main()
        
        output = mock_stdout.getvalue()
        
        # Verify docs content is present
        assert 'HydroSim Documentation' in output
        assert 'Opening HydroSim documentation' in output
        assert 'github.com/jlillywh/hydrosim' in output


class TestHelpSystemWorkflow:
    """Test help functions work correctly in Python environment."""
    
    def test_help_function_produces_complete_output(self):
        """Test hydrosim.help() produces comprehensive output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Mock environment detection to simulate terminal
            with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
                mock_env = MagicMock()
                mock_env.is_terminal = True
                mock_env.supports_html = False
                mock_detect.return_value = mock_env
                
                help_module.help()
        
        output = mock_stdout.getvalue()
        
        # Verify comprehensive help content
        assert 'HydroSim: A Python-based water resources planning framework' in output
        assert 'MAIN MODULES:' in output
        assert 'StorageNode' in output
        assert 'ClimateEngine' in output
        assert 'SimulationEngine' in output
        assert 'QUICK START:' in output
        assert 'Code Examples:' in output
        assert 'import hydrosim' in output
    
    def test_about_function_produces_complete_output(self):
        """Test hydrosim.about() produces comprehensive output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Mock environment detection to simulate terminal
            with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
                mock_env = MagicMock()
                mock_env.is_terminal = True
                mock_env.supports_html = False
                mock_detect.return_value = mock_env
                
                help_module.about()
        
        output = mock_stdout.getvalue()
        
        # Verify about content
        assert 'HydroSim v' in output
        assert 'LICENSE: MIT License' in output
        assert 'AUTHOR: J. Lillywh' in output
        assert 'PROJECT LINKS:' in output
        assert 'github.com/jlillywh/hydrosim' in output
    
    def test_examples_function_produces_complete_output(self):
        """Test hydrosim.examples() produces comprehensive output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Mock environment detection to simulate terminal
            with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
                mock_env = MagicMock()
                mock_env.is_terminal = True
                mock_env.supports_html = False
                mock_detect.return_value = mock_env
                
                help_module.examples()
        
        output = mock_stdout.getvalue()
        
        # Verify examples content
        assert 'HydroSim Examples' in output
        assert 'GETTING STARTED:' in output
        assert 'Quick Start Example' in output
        assert 'Network Visualization' in output
        assert 'EXECUTION:' in output
        assert 'python examples/' in output
    
    def test_docs_function_terminal_environment(self):
        """Test hydrosim.docs() in terminal environment."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Mock environment detection to simulate terminal
            with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
                mock_env = MagicMock()
                mock_env.is_terminal = True
                mock_env.supports_html = False
                mock_detect.return_value = mock_env
                
                # Mock webbrowser to avoid actually opening browser
                with patch('webbrowser.open', return_value=True):
                    help_module.docs()
        
        output = mock_stdout.getvalue()
        
        # Verify docs behavior in terminal
        assert 'Opening HydroSim documentation' in output
        assert 'github.com/jlillywh/hydrosim' in output
    
    def test_quick_start_function_produces_complete_output(self):
        """Test hydrosim.quick_start() produces comprehensive output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Mock environment detection to simulate terminal
            with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
                mock_env = MagicMock()
                mock_env.is_terminal = True
                mock_env.supports_html = False
                mock_detect.return_value = mock_env
                
                help_module.quick_start()
        
        output = mock_stdout.getvalue()
        
        # Verify quick start content
        assert 'HydroSim Quick Start Tutorial' in output
        assert 'STEP 1: INSTALL HYDROSIM' in output
        assert 'STEP 2: BASIC IMPORTS' in output
        assert 'STEP 3: LOAD A NETWORK' in output
        assert 'STEP 4: SET UP SIMULATION' in output
        assert 'STEP 5: RUN SIMULATION' in output
        assert 'STEP 6: EXPORT RESULTS' in output
        assert 'NEXT STEPS:' in output


class TestJupyterEnvironmentWorkflow:
    """Test help functions work correctly in Jupyter notebook environment."""
    
    def test_help_function_jupyter_environment(self):
        """Test hydrosim.help() in Jupyter environment produces HTML output."""
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        # Mock environment detection to simulate Jupyter
        with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
            mock_env = MagicMock()
            mock_env.is_terminal = False
            mock_env.is_jupyter = True
            mock_env.supports_html = True
            mock_detect.return_value = mock_env
            
            # Mock IPython display at the import level
            mock_html = MagicMock()
            mock_display = MagicMock()
            
            with patch.dict('sys.modules', {'IPython.display': MagicMock(HTML=mock_html, display=mock_display)}):
                help_module.help()
            
            # Verify HTML display was called
            mock_display.assert_called()
            mock_html.assert_called()
            
            # Check that HTML content contains expected elements
            html_call_args = mock_html.call_args[0][0]
            assert 'HydroSim: Water Resources Planning Framework' in html_call_args
            assert '<h2' in html_call_args  # HTML formatting
            assert 'color:' in html_call_args  # CSS styling
    
    def test_examples_function_jupyter_environment(self):
        """Test hydrosim.examples() in Jupyter environment produces rich HTML."""
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        # Mock environment detection to simulate Jupyter
        with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
            mock_env = MagicMock()
            mock_env.is_terminal = False
            mock_env.is_jupyter = True
            mock_env.supports_html = True
            mock_detect.return_value = mock_env
            
            # Mock IPython display at the import level
            mock_html = MagicMock()
            mock_display = MagicMock()
            
            with patch.dict('sys.modules', {'IPython.display': MagicMock(HTML=mock_html, display=mock_display)}):
                help_module.examples()
            
            # Verify HTML display was called
            mock_display.assert_called()
            mock_html.assert_called()
            
            # Check that HTML content contains expected elements
            html_call_args = mock_html.call_args[0][0]
            assert 'HydroSim Examples' in html_call_args
            assert '<pre' in html_call_args  # Code formatting
            assert 'import hydrosim' in html_call_args  # Code examples
    
    def test_docs_function_jupyter_environment(self):
        """Test hydrosim.docs() in Jupyter environment displays inline links."""
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        # Mock environment detection to simulate Jupyter
        with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
            mock_env = MagicMock()
            mock_env.is_terminal = False
            mock_env.is_jupyter = True
            mock_env.supports_html = True
            mock_detect.return_value = mock_env
            
            # Mock IPython display at the import level
            mock_html = MagicMock()
            mock_display = MagicMock()
            
            with patch.dict('sys.modules', {'IPython.display': MagicMock(HTML=mock_html, display=mock_display)}):
                help_module.docs()
            
            # Verify HTML display was called
            mock_display.assert_called()
            mock_html.assert_called()
            
            # Check that HTML content contains expected elements
            html_call_args = mock_html.call_args[0][0]
            assert 'HydroSim Documentation' in html_call_args
            assert '<a href=' in html_call_args  # Links
            assert 'target=\'_blank\'' in html_call_args  # External links
    
    def test_quick_start_function_jupyter_environment(self):
        """Test hydrosim.quick_start() in Jupyter environment produces interactive tutorial."""
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        # Mock environment detection to simulate Jupyter
        with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
            mock_env = MagicMock()
            mock_env.is_terminal = False
            mock_env.is_jupyter = True
            mock_env.supports_html = True
            mock_detect.return_value = mock_env
            
            # Mock IPython display at the import level
            mock_html = MagicMock()
            mock_display = MagicMock()
            
            with patch.dict('sys.modules', {'IPython.display': MagicMock(HTML=mock_html, display=mock_display)}):
                help_module.quick_start()
            
            # Verify HTML display was called
            mock_display.assert_called()
            mock_html.assert_called()
            
            # Check that HTML content contains expected elements
            html_call_args = mock_html.call_args[0][0]
            assert 'HydroSim Quick Start Tutorial' in html_call_args
            assert 'Step 1:' in html_call_args
            assert '<pre' in html_call_args  # Code blocks
            assert 'import hydrosim' in html_call_args  # Code examples


class TestPackageInstallationWorkflow:
    """Test package installation and console script registration."""
    
    def test_package_metadata_completeness(self):
        """Test package metadata contains all required information."""
        # Test version is accessible
        assert hasattr(hydrosim, '__version__')
        assert hydrosim.__version__ is not None
        assert len(hydrosim.__version__) > 0
        
        # Test __all__ is properly defined
        assert hasattr(hydrosim, '__all__')
        assert isinstance(hydrosim.__all__, list)
        assert len(hydrosim.__all__) > 0
        
        # Test help functions are in __all__
        assert 'help' in hydrosim.__all__
        assert 'about' in hydrosim.__all__
        assert 'docs' in hydrosim.__all__
        assert 'examples' in hydrosim.__all__
        assert 'quick_start' in hydrosim.__all__
    
    def test_help_functions_importable_from_main_package(self):
        """Test help functions can be imported from main hydrosim package."""
        # Test direct import
        from hydrosim import help, about, docs, examples, quick_start
        
        # Test functions are callable
        assert callable(help)
        assert callable(about)
        assert callable(docs)
        assert callable(examples)
        assert callable(quick_start)
        
        # Test functions can be accessed via hydrosim.function_name
        assert callable(hydrosim.help)
        assert callable(hydrosim.about)
        assert callable(hydrosim.docs)
        assert callable(hydrosim.examples)
        assert callable(hydrosim.quick_start)
    
    def test_console_script_entry_point_exists(self):
        """Test console script entry point is properly configured."""
        # Test that cli.main function exists and is callable
        assert hasattr(cli, 'main')
        assert callable(cli.main)
        
        # Test that main function can be called without errors (with mocked args)
        with patch('sys.argv', ['hydrosim', '--help']):
            with patch('sys.stdout', new_callable=StringIO):
                try:
                    cli.main()
                except SystemExit:
                    pass  # Expected for help command
    
    def test_package_docstring_completeness(self):
        """Test main package docstring is comprehensive."""
        docstring = hydrosim.__doc__
        assert docstring is not None
        assert len(docstring) > 100  # Substantial docstring
        
        # Check for key content
        assert 'HydroSim' in docstring
        assert 'water resources' in docstring
        assert 'Quick Start:' in docstring
        assert 'Main Components:' in docstring
        assert 'hs.help()' in docstring


class TestEnvironmentDetection:
    """Test environment detection works correctly."""
    
    def test_terminal_environment_detection(self):
        """Test environment detection correctly identifies terminal."""
        # Mock IPython not available
        with patch('hydrosim.help.EnvironmentDetector._is_jupyter', return_value=False):
            with patch('hydrosim.help.EnvironmentDetector._is_colab', return_value=False):
                env = help_module.EnvironmentDetector.detect()
                
                assert env.is_terminal is True
                assert env.is_jupyter is False
                assert env.is_colab is False
                assert env.supports_html is False
                assert env.supports_widgets is False
    
    def test_jupyter_environment_detection(self):
        """Test environment detection correctly identifies Jupyter."""
        # Mock Jupyter environment
        with patch('hydrosim.help.EnvironmentDetector._is_jupyter', return_value=True):
            with patch('hydrosim.help.EnvironmentDetector._is_colab', return_value=False):
                env = help_module.EnvironmentDetector.detect()
                
                assert env.is_terminal is False
                assert env.is_jupyter is True
                assert env.is_colab is False
                assert env.supports_html is True
                assert env.supports_widgets is True
    
    def test_colab_environment_detection(self):
        """Test environment detection correctly identifies Google Colab."""
        # Mock Colab environment
        with patch('hydrosim.help.EnvironmentDetector._is_jupyter', return_value=False):
            with patch('hydrosim.help.EnvironmentDetector._is_colab', return_value=True):
                env = help_module.EnvironmentDetector.detect()
                
                assert env.is_terminal is False
                assert env.is_jupyter is False
                assert env.is_colab is True
                assert env.supports_html is True
                assert env.supports_widgets is True


class TestCrossEnvironmentConsistency:
    """Test that functionality works consistently across environments."""
    
    def test_help_content_consistency_across_environments(self):
        """Test help content is consistent between terminal and Jupyter."""
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        # Capture terminal output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout_terminal:
            with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
                mock_env = MagicMock()
                mock_env.is_terminal = True
                mock_env.supports_html = False
                mock_detect.return_value = mock_env
                help_module.help()
        
        terminal_output = mock_stdout_terminal.getvalue()
        
        # Capture Jupyter HTML output
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
            mock_env = MagicMock()
            mock_env.is_terminal = False
            mock_env.supports_html = True
            mock_detect.return_value = mock_env
            
            mock_html = MagicMock()
            mock_display = MagicMock()
            
            with patch.dict('sys.modules', {'IPython.display': MagicMock(HTML=mock_html, display=mock_display)}):
                help_module.help()
        
        jupyter_html = mock_html.call_args[0][0] if mock_html.call_args else ""
        
        # Check that core content appears in both (case-insensitive)
        core_content = [
            'HydroSim',
            'water resources',
            'MAIN MODULES',
            'StorageNode',
            'ClimateEngine',
            'QUICK START'
        ]
        
        for content in core_content:
            assert content.lower() in terminal_output.lower(), f"'{content}' missing from terminal output"
            assert content.lower() in jupyter_html.lower(), f"'{content}' missing from Jupyter HTML"
    
    def test_examples_content_consistency_across_environments(self):
        """Test examples content is consistent between terminal and Jupyter."""
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        # Capture terminal output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout_terminal:
            with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
                mock_env = MagicMock()
                mock_env.is_terminal = True
                mock_env.supports_html = False
                mock_detect.return_value = mock_env
                help_module.examples()
        
        terminal_output = mock_stdout_terminal.getvalue()
        
        # Capture Jupyter HTML output
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
            mock_env = MagicMock()
            mock_env.is_terminal = False
            mock_env.supports_html = True
            mock_detect.return_value = mock_env
            
            mock_html = MagicMock()
            mock_display = MagicMock()
            
            with patch.dict('sys.modules', {'IPython.display': MagicMock(HTML=mock_html, display=mock_display)}):
                help_module.examples()
        
        jupyter_html = mock_html.call_args[0][0] if mock_html.call_args else ""
        
        # Check that core examples appear in both
        core_examples = [
            'Quick Start Example',
            'Network Visualization',
            'Weather Generator',
            'Storage Drawdown'
        ]
        
        for example in core_examples:
            assert example in terminal_output, f"'{example}' missing from terminal output"
            assert example in jupyter_html, f"'{example}' missing from Jupyter HTML"


class TestErrorHandling:
    """Test error handling in different scenarios."""
    
    def test_help_system_handles_missing_ipython(self):
        """Test help system gracefully handles missing IPython in Jupyter-like environment."""
        # Mock environment as Jupyter but IPython import fails
        with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
            mock_env = MagicMock()
            mock_env.is_terminal = False
            mock_env.supports_html = True
            mock_detect.return_value = mock_env
            
            # Mock IPython import failure
            with patch('hydrosim.help.HTML', create=True, side_effect=ImportError("No module named 'IPython'")):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    # Should not raise exception, should fallback to text output
                    help_module.help()
                    
                    # Should have some output (fallback text)
                    output = mock_stdout.getvalue()
                    assert len(output) > 0
    
    def test_docs_function_handles_browser_failure(self):
        """Test docs function handles browser launch failure gracefully."""
        # Reset global display manager to ensure fresh environment detection
        help_module._display_manager = None
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('hydrosim.help.EnvironmentDetector.detect') as mock_detect:
                mock_env = MagicMock()
                mock_env.is_terminal = True
                mock_env.supports_html = False
                mock_detect.return_value = mock_env
                
                # Mock webbrowser failure
                with patch('webbrowser.open', side_effect=Exception("Browser not found")):
                    help_module.docs()
        
        output = mock_stdout.getvalue()
        
        # Should handle error gracefully and provide fallback
        assert 'Could not open browser automatically' in output
        assert 'Please visit:' in output
        assert 'github.com/jlillywh/hydrosim' in output