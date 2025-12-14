# Development Scripts

This folder contains development and maintenance scripts for HydroSim.

## Scripts

### `dev_tools.py`
Development workflow automation tool for managing issues and branches.

**Usage:**
```bash
# Start working on an issue
python scripts/dev_tools.py start 123 feature "add new solver"

# Run tests
python scripts/dev_tools.py test

# Check development status
python scripts/dev_tools.py status

# Finish working on an issue
python scripts/dev_tools.py finish 123

# Clean up merged branches
python scripts/dev_tools.py cleanup
```

**Commands:**
- `start` - Create a new branch for an issue
- `test` - Run the test suite
- `status` - Check current development status
- `finish` - Prepare issue for PR submission
- `cleanup` - Clean up merged branches

This tool follows the development workflow outlined in `docs/DEVELOPMENT.md`.