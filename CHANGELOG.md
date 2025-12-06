# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
