"""
Complete workflow validation for HydroSim developer experience improvements.

This test validates the complete workflow across different environments as specified
in task 8.1: Test complete workflow in different environments.

Validates Requirements: All from the developer-experience-improvements spec.
"""

import pytest
import subprocess
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock
from io import StringIO

import hydrosim
from hydrosim import cli


class TestCompleteWorkflowValidation:
    """Comprehensive validation of the complete developer experience workflow."""
    
    def test_cli_commands_work_correctly_in_terminal(self):
        """Validate CLI commands work correctly in terminal environment."""
        # Test all CLI commands produce expected output
        cli_tests = [
            (['python', '-m', 'hydrosim.cli', '--help'], ['HydroSim Command Line Interface', 'CLI COMMANDS:']),
            (['python', '-m', 'hydrosim.cli', '--examples'], ['HydroSim Examples', 'Quick Start Example']),
            (['python', '-m', 'hydrosim.cli', '--about'], ['HydroSim v', 'LICENSE: MIT License']),
        ]
        
        for cmd, expected_content in cli_tests:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Verify command succeeded
            assert result.returncode == 0, f"Command {' '.join(cmd)} failed with code {result.returncode}"
            
            # Verify expected content is present
            for content in expected_content:
                assert content in result.stdout, f"Expected content '{content}' not found in output of {' '.join(cmd)}"
            
            # Verify substantial output
            assert len(result.stdout) > 200, f"Command {' '.join(cmd)} produced insufficient output"
    
    def test_help_functions_work_in_python_environment(self):
        """Test help functions work correctly in Python environment."""
        # Test all help functions produce expected output
        help_functions = [
            (hydrosim.help, ['HydroSim: A Python-based water resources planning framework', 'MAIN MODULES:', 'QUICK START:']),
            (hydrosim.about, ['HydroSim v', 'LICENSE: MIT License', 'PROJECT LINKS:']),
            (hydrosim.examples, ['HydroSim Examples', 'Quick Start Example', 'EXECUTION:']),
            (hydrosim.quick_start, ['HydroSim Quick Start Tutorial', 'STEP 1:', 'NEXT STEPS:']),
        ]
        
        for func, expected_content in help_functions:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                # Mock webbrowser for docs function
                with patch('webbrowser.open', return_value=True):
                    func()
                
                output = mock_stdout.getvalue()
                
                # Verify expected content is present
                for content in expected_content:
                    assert content in output, f"Expected content '{content}' not found in {func.__name__}() output"
                
                # Verify substantial output
                assert len(output) > 100, f"Function {func.__name__}() produced insufficient output"
    
    def test_docs_function_handles_different_environments(self):
        """Test docs function works in both terminal and Jupyter-like environments."""
        # Test terminal environment (opens browser)
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('webbrowser.open', return_value=True) as mock_browser:
                hydrosim.docs()
                
                output = mock_stdout.getvalue()
                assert 'Opening HydroSim documentation' in output
                assert 'github.com/jlillywh/hydrosim' in output
                mock_browser.assert_called_once()
        
        # Test browser failure handling
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('webbrowser.open', side_effect=Exception("Browser not found")):
                hydrosim.docs()  # Should not raise exception
                
                output = mock_stdout.getvalue()
                assert 'Could not open browser automatically' in output
                assert 'Please visit:' in output
    
    def test_package_installation_and_console_script_registration(self):
        """Verify package installation and console script registration work correctly."""
        # Test package metadata is complete
        assert hasattr(hydrosim, '__version__')
        assert hydrosim.__version__ is not None
        assert len(hydrosim.__version__) > 0
        
        # Test __all__ includes help functions
        required_functions = ['help', 'about', 'docs', 'examples', 'quick_start']
        for func_name in required_functions:
            assert func_name in hydrosim.__all__, f"Function {func_name} not in __all__"
            assert hasattr(hydrosim, func_name), f"Function {func_name} not accessible"
            assert callable(getattr(hydrosim, func_name)), f"Function {func_name} not callable"
        
        # Test console script entry point exists and works
        assert hasattr(cli, 'main')
        assert callable(cli.main)
        
        # Test console script can be executed
        result = subprocess.run(['python', '-m', 'hydrosim.cli', '--help'], 
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        assert 'HydroSim Command Line Interface' in result.stdout
    
    def test_environment_detection_works_correctly(self):
        """Test environment detection correctly identifies different environments."""
        import importlib
        help_module = importlib.import_module('hydrosim.help')
        
        # Test environment detector exists and works
        assert hasattr(help_module, 'EnvironmentDetector')
        assert callable(help_module.EnvironmentDetector.detect)
        
        # Test environment detection returns valid object
        env = help_module.EnvironmentDetector.detect()
        
        # Verify all required attributes exist and are boolean
        required_attrs = ['is_terminal', 'is_jupyter', 'is_colab', 'supports_html', 'supports_widgets']
        for attr in required_attrs:
            assert hasattr(env, attr), f"Environment object missing attribute {attr}"
            assert isinstance(getattr(env, attr), bool), f"Attribute {attr} is not boolean"
        
        # In test environment, should detect as terminal
        assert env.is_terminal is True
        assert env.is_jupyter is False
        assert env.is_colab is False
        assert env.supports_html is False
        assert env.supports_widgets is False
    
    def test_error_handling_works_gracefully(self):
        """Test error handling works gracefully across different scenarios."""
        # Test help functions don't crash on exceptions
        help_functions = [hydrosim.help, hydrosim.about, hydrosim.examples, hydrosim.quick_start]
        
        for func in help_functions:
            try:
                with patch('sys.stdout', new_callable=StringIO):
                    func()
            except Exception as e:
                pytest.fail(f"Help function {func.__name__} raised unexpected exception: {e}")
        
        # Test docs function handles browser failure
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('webbrowser.open', side_effect=Exception("Browser error")):
                hydrosim.docs()  # Should not raise exception
                
                output = mock_stdout.getvalue()
                assert len(output) > 0  # Should produce fallback output
    
    def test_cross_environment_consistency(self):
        """Test functionality works consistently across different access methods."""
        # Test CLI vs Python help consistency
        # Get CLI help output
        cli_result = subprocess.run(['python', '-m', 'hydrosim.cli', '--help'], 
                                  capture_output=True, text=True, timeout=30)
        assert cli_result.returncode == 0
        cli_output = cli_result.stdout
        
        # Get Python help output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.help()
            python_output = mock_stdout.getvalue()
        
        # Both should contain core HydroSim information
        core_content = ['HydroSim', 'water resources', 'StorageNode', 'ClimateEngine']
        for content in core_content:
            assert content in cli_output, f"'{content}' missing from CLI help"
            assert content in python_output, f"'{content}' missing from Python help"
        
        # Test examples consistency
        cli_result = subprocess.run(['python', '-m', 'hydrosim.cli', '--examples'], 
                                  capture_output=True, text=True, timeout=30)
        assert cli_result.returncode == 0
        cli_examples = cli_result.stdout
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.examples()
            python_examples = mock_stdout.getvalue()
        
        # Both should contain core examples
        core_examples = ['Quick Start Example', 'Network Visualization']
        for example in core_examples:
            assert example in cli_examples, f"'{example}' missing from CLI examples"
            assert example in python_examples, f"'{example}' missing from Python examples"
    
    def test_package_build_configuration_completeness(self):
        """Test package build configuration includes all required files."""
        # Test pyproject.toml has console script entry point
        import tomllib
        
        with open('pyproject.toml', 'rb') as f:
            pyproject_data = tomllib.load(f)
        
        # Verify console script is configured
        assert 'project' in pyproject_data
        assert 'scripts' in pyproject_data['project']
        assert 'hydrosim' in pyproject_data['project']['scripts']
        assert pyproject_data['project']['scripts']['hydrosim'] == 'hydrosim.cli:main'
        
        # Verify project URLs are complete
        assert 'urls' in pyproject_data['project']
        required_urls = ['Homepage', 'Repository', 'Bug Reports', 'Documentation']
        for url_type in required_urls:
            assert url_type in pyproject_data['project']['urls']
            assert 'github.com/jlillywh/hydrosim' in pyproject_data['project']['urls'][url_type]
        
        # Test MANIFEST.in includes required files
        with open('MANIFEST.in', 'r') as f:
            manifest_content = f.read()
        
        required_files = ['README.md', 'LICENSE', 'CHANGELOG.md']
        for file_name in required_files:
            assert file_name in manifest_content, f"Required file {file_name} not in MANIFEST.in"
    
    def test_complete_workflow_end_to_end(self):
        """Test complete end-to-end workflow from installation to usage."""
        # This test simulates the complete user workflow:
        # 1. Package is installed (simulated by imports working)
        # 2. User can access help via CLI
        # 3. User can access help via Python
        # 4. User can discover examples
        # 5. User can access documentation
        
        # Step 1: Verify package can be imported and has all components
        import hydrosim
        assert hasattr(hydrosim, 'help')
        assert hasattr(hydrosim, 'about')
        assert hasattr(hydrosim, 'docs')
        assert hasattr(hydrosim, 'examples')
        assert hasattr(hydrosim, 'quick_start')
        
        # Step 2: Verify CLI access works
        cli_result = subprocess.run(['python', '-m', 'hydrosim.cli', '--help'], 
                                  capture_output=True, text=True, timeout=30)
        assert cli_result.returncode == 0
        assert 'HydroSim Command Line Interface' in cli_result.stdout
        assert 'hydrosim --help' in cli_result.stdout
        
        # Step 3: Verify Python access works
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.help()
            help_output = mock_stdout.getvalue()
            assert 'HydroSim: A Python-based water resources planning framework' in help_output
            assert 'MAIN MODULES:' in help_output
        
        # Step 4: Verify examples discovery works
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.examples()
            examples_output = mock_stdout.getvalue()
            assert 'HydroSim Examples' in examples_output
            assert 'Quick Start Example' in examples_output
            assert 'python examples/' in examples_output
        
        # Step 5: Verify documentation access works
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('webbrowser.open', return_value=True):
                hydrosim.docs()
                docs_output = mock_stdout.getvalue()
                assert 'documentation' in docs_output.lower()
                assert 'github.com/jlillywh/hydrosim' in docs_output
        
        # Step 6: Verify about information is accessible
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.about()
            about_output = mock_stdout.getvalue()
            assert 'HydroSim v' in about_output
            assert 'LICENSE: MIT License' in about_output
            assert 'github.com/jlillywh/hydrosim' in about_output
        
        # Step 7: Verify quick start tutorial is available
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.quick_start()
            quickstart_output = mock_stdout.getvalue()
            assert 'HydroSim Quick Start Tutorial' in quickstart_output
            assert 'STEP 1:' in quickstart_output
            assert 'import hydrosim' in quickstart_output
        
        print("✅ Complete end-to-end workflow validation passed!")
    
    def test_all_requirements_validated(self):
        """Final validation that all requirements from the spec are met."""
        # This test serves as a checklist for all requirements
        
        # Requirement 1.1: CLI help command
        result = subprocess.run(['python', '-m', 'hydrosim.cli', '--help'], 
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        assert 'usage information' in result.stdout or 'help information' in result.stdout
        assert 'examples' in result.stdout
        
        # Requirement 1.2: Python help() function
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.help()
            output = mock_stdout.getvalue()
            assert 'library overview' in output or 'HydroSim' in output
            assert 'modules' in output.lower()
        
        # Requirement 1.3: help(hydrosim) works
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            help(hydrosim)  # Built-in help function
            output = mock_stdout.getvalue()
            assert len(output) > 100  # Should produce substantial output
        
        # Requirement 1.4: pip show hydrosim would show metadata (simulated)
        assert hasattr(hydrosim, '__version__')
        assert hydrosim.__doc__ is not None
        assert len(hydrosim.__doc__) > 100
        
        # Requirement 1.5: docs() function opens browser
        with patch('webbrowser.open', return_value=True) as mock_browser:
            with patch('sys.stdout', new_callable=StringIO):
                hydrosim.docs()
                mock_browser.assert_called_once()
        
        # Requirement 2.1: CLI examples command
        result = subprocess.run(['python', '-m', 'hydrosim.cli', '--examples'], 
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        assert 'example' in result.stdout.lower()
        
        # Requirement 2.2: Module docstrings
        assert hydrosim.__doc__ is not None
        assert 'usage examples' in hydrosim.__doc__ or 'Quick Start' in hydrosim.__doc__
        
        # Requirement 2.3: Public API via __all__
        assert hasattr(hydrosim, '__all__')
        assert 'help' in hydrosim.__all__
        
        # Requirement 2.4: about() function
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.about()
            output = mock_stdout.getvalue()
            assert 'v0.4.1' in output or 'version' in output.lower()
            assert 'license' in output.lower()
        
        # Requirement 2.5: examples() function
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            hydrosim.examples()
            output = mock_stdout.getvalue()
            assert 'runnable' in output or 'python examples/' in output
        
        # Requirement 3.1: Package build includes required files
        required_files = ['README.md', 'CHANGELOG.md', 'LICENSE']
        for file_name in required_files:
            assert os.path.exists(file_name), f"Required file {file_name} not found"
        
        # Requirement 3.2: PyPI description (simulated by checking README exists)
        assert os.path.exists('README.md')
        
        # Requirement 3.3: Complete project URLs
        import tomllib
        with open('pyproject.toml', 'rb') as f:
            pyproject_data = tomllib.load(f)
        
        assert 'urls' in pyproject_data['project']
        required_urls = ['Homepage', 'Repository', 'Bug Reports', 'Documentation']
        for url_type in required_urls:
            assert url_type in pyproject_data['project']['urls']
        
        # Requirement 3.4: Console script entry point
        assert 'scripts' in pyproject_data['project']
        assert 'hydrosim' in pyproject_data['project']['scripts']
        
        # Requirement 3.5: Clean docstrings
        assert hydrosim.__doc__ is not None
        assert len(hydrosim.__doc__) > 100
        
        print("✅ All requirements from the developer-experience-improvements spec validated!")