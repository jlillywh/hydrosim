# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
