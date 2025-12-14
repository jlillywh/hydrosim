# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2024-12-13

### Added
- **Interactive Help System**: Comprehensive help functions for improved developer experience
  - `hydrosim.help()`: Environment-aware help with rich formatting for Jupyter notebooks
  - `hydrosim.about()`: Version information and project details
  - `hydrosim.docs()`: Documentation access with browser integration
  - `hydrosim.examples()`: Interactive examples browser with code snippets
  - `hydrosim.quick_start()`: Step-by-step tutorial optimized for Jupyter notebooks
- **Enhanced CLI Interface**: Improved command-line interface with help system integration
  - `hydrosim --help`: Display usage information and quick-start examples
  - `hydrosim --examples`: List available example scripts with descriptions
  - `hydrosim --about`: Show version and project information
- **Jupyter Notebook Optimization**: Enhanced support for notebook environments
  - Automatic environment detection (terminal vs Jupyter vs Colab)
  - Rich HTML formatting for notebook display
  - Interactive code snippets with copy-paste functionality
  - Notebook-friendly example files with markdown documentation
- **Enhanced Package Metadata**: Improved discoverability and documentation integration
  - Complete project URLs in package metadata
  - Enhanced docstrings for all public modules
  - Console script entry point for CLI access
  - Improved distribution file inclusion

### Changed
- **Examples Enhancement**: Updated existing examples with notebook-friendly formatting
  - Added markdown-style documentation headers
  - Improved progress output with emojis and clear formatting
  - Better step-by-step structure for learning
  - Enhanced explanations for both terminal and notebook users
- **Public API**: Expanded public API with help system functions
  - Added help functions to `__all__` declarations
  - Updated main docstring with quick start examples
  - Improved module-level documentation

### Documentation
- **Interactive Tutorial**: New `quick_start()` function provides comprehensive tutorial
  - 7-step interactive guide from installation to visualization
  - Executable code cells for hands-on learning
  - Sample data generation and network configuration
  - Results analysis and visualization examples
- **Notebook Examples**: Created `notebook_quick_start.py` for optimal Jupyter experience
  - Cell-by-cell structure with clear explanations
  - Comprehensive workflow demonstration
  - Visualization examples with matplotlib integration
  - Clear next steps and learning path guidance

## [0.4.0] - 2024-12-10

### Added
- **Look-ahead Optimization**: Implemented multi-timestep optimization using time-expanded graphs
  - New `LookaheadSolver` class with configurable horizon (1-365 days)
  - Perfect foresight assumption for future inflows and demands
  - Rolling horizon approach for operational planning
  - Hedging capability to save water for future high-priority demands
- **Optimization Configuration**: Added YAML configuration section for optimization parameters
  - `lookahead_days`: Number of days to look ahead (default: 1 for myopic behavior)
  - `solver_type`: Solver selection (linear_programming, network_simplex)
  - `perfect_foresight`: Enable/disable perfect foresight assumption
  - `carryover_cost`: Cost for storing water between timesteps (hedging penalty)
  - `rolling_horizon`: Enable/disable rolling horizon optimization
- **Automatic Solver Selection**: SimulationEngine now auto-selects solver based on YAML config
- **Future Data Extraction**: Added methods to extract future inflows and demands for look-ahead
  - `TimeSeriesStrategy.get_future_values()` for source nodes
  - `MunicipalDemand.get_future_demands()` and `AgricultureDemand.get_future_demands()` for demand nodes
- **Comprehensive Test Suite**: Added hedging behavior validation tests
  - Test that myopic solver fails to hedge properly
  - Test that look-ahead solver hedges successfully
  - Regression test ensuring `lookahead_days=1` matches myopic behavior

### Changed
- **SimulationEngine**: Constructor now accepts optional solver parameter (auto-selected if not provided)
- **Examples**: Updated `quick_start.py` to use automatic solver selection
- **Complex Network Example**: Added 7-day look-ahead optimization configuration
- **Extended Inflow Data**: Created 365-day inflow dataset for year-long simulations

### Fixed
- **Issue #1**: Implemented look-ahead optimization to enable hedging decisions
- **Solver Integration**: Proper integration between look-ahead solver and simulation engine
- **State Management**: Correct handling of storage updates with look-ahead optimization

## [0.3.1] - 2024-12-10

### Added
- PyPI publishing configuration with modern `pyproject.toml`
- Automated publishing script (`publish.py`) with safety checks
- Comprehensive installation verification script (`verify_installation.py`)
- Complete publishing documentation and checklists

### Changed
- **BREAKING**: Updated all documentation to prioritize PyPI installation (`pip install hydrosim`)
- Reorganized installation instructions across all README files
- Examples now require repository clone (not included in PyPI package)
- Updated dependency management for PyPI distribution

### Fixed
- Fixed license configuration for modern Python packaging standards
- Updated test version assertions
- Improved error handling in verification scripts

### Documentation
- Complete rewrite of installation sections in all documentation
- Added PyPI-first user workflows
- Created comprehensive publishing guides
- Added installation verification tools

## [0.3.0] - 2024-12-05

### Added
- Climate Builder module for WGEN parameter generation from GHCN-Daily data
  - GHCN-Daily data fetcher with automatic station discovery
  - DLY file parser for GHCN-Daily format
  - Temperature parameter calculator (mean, standard deviation, lag-1 autocorrelation)
  - Precipitation parameter calculator (wet/dry probabilities, gamma distribution)
  - Solar radiation parameter calculator (mean, standard deviation)
  - Parameter CSV generator for WGEN integration
  - Comprehensive data quality validation and reporting
- WGEN CSV parameter file parser
- Network visualization tools with matplotlib
- Results visualization module for time series analysis
- Example project structure with configuration templates
- Comprehensive test suite for climate builder components

### Changed
- Enhanced WGEN integration with CSV parameter support
- Improved documentation with climate builder examples
- Updated requirements with visualization dependencies

### Fixed
- WGEN parameter handling and validation

## [0.2.0] - 2024-12-04

### Added
- Active storage drawdown using virtual link architecture
- Storage nodes can now draw down and refill based on network optimization
- Virtual sink and carryover link components for realistic reservoir operations
- `max_storage` and `min_storage` (dead pool) parameters for storage nodes
- Comprehensive test suite with property-based testing using Hypothesis
- Results output system with CSV and JSON export formats
- YAML configuration parser for network definition
- Example configurations and demonstration scripts
- Complete documentation in README

### Features
- Multiple node types: Storage, Junction, Source, Demand
- Flexible link modeling with capacity, hydraulic, and control constraints
- Climate integration with time series and WGEN stochastic generation
- Network optimization using minimum cost flow solver
- Pluggable strategies for generation and demand models
- Hargreaves ET0 calculation
- Daily timestep simulation engine

## [0.1.0] - Initial Development

### Added
- Core framework architecture
- Basic node and link abstractions
- Linear programming solver integration
- Climate engine foundation
- Strategy pattern for extensibility
