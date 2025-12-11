# HydroSim Issues Tracker

*Last updated: Automatically synced from GitHub*

## 🐛 Bug Fixes

## ✨ Enhancements

### Medium Priority
- [ ] **Issue #5**: specify the start and end date of the simulation period in the model yaml file
  - **Status**: Open
  - **Priority**: Medium
  - **Labels**: enhancement
  - **GitHub**: https://github.com/jlillywh/hydrosim/issues/5
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: currently, end user cannot specify simulation start and end date of the simulation from the yaml file. allow this to be done in that file.

- [x] **Issue #4**: network graph is too spread out
  - **Status**: ✅ RESOLVED
  - **Priority**: Medium
  - **Labels**: enhancement
  - **GitHub**: https://github.com/jlillywh/hydrosim/issues/4
  - **Assignee**: Kiro AI
  - **Branch**: bugfix/issue-3-fix-plot-axis-title-characters
  - **Notes**: ✅ FIXED - Implemented compact node spacing (3x reduction) and fixed axis ranges to prevent auto-scaling. Network graphs now display nodes close together while maintaining responsive canvas control.

- [ ] **Issue #2**: show 1 plot-specific legend to the right of each chart
  - **Status**: Open
  - **Priority**: Medium
  - **Labels**: enhancement
  - **GitHub**: https://github.com/jlillywh/hydrosim/issues/2
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: currently 1 single legend is shown at the top right side of the results chart page and so when we scroll down the page to see each plot, we are not able to see the legend for each plot because we scro...

- [ ] **Issue #1**: Implement Look-ahead Optimization
  - **Status**: Open
  - **Priority**: Medium
  - **Labels**: enhancement
  - **GitHub**: https://github.com/jlillywh/hydrosim/issues/1
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: Multi-Timestep "Look-ahead" Optimization  I need the model to anticipate future constraints (e.g., upcoming droughts or demand spikes) so that reservoir release decisions made today account for risks ...

---

## Development Workflow

To work on an issue:

```bash
# Start working on issue
python dev_tools.py start <issue_number> <type> "<description>"

# Example:
python dev_tools.py start 1 bugfix "fix temperature validation"
python dev_tools.py start 2 feature "add uncertainty analysis"
```

## Issue Types for dev_tools.py

- `bugfix` - For bug fixes
- `feature` - For new features/enhancements  
- `docs` - For documentation improvements
- `test` - For testing improvements

## Sync with GitHub

To refresh this file with latest GitHub issues:

```bash
python fetch_github_issues.py
```

## Status Definitions

- **Open**: Issue identified, not yet started
- **In Progress**: Actively being worked on  
- **Review**: Code complete, needs review/testing
- **Closed**: Issue resolved and merged

## Priority Guidelines

- **High**: Critical bugs, security issues, blocking other work
- **Medium**: Important features, non-critical bugs, performance improvements
- **Low**: Nice-to-have features, code cleanup, minor improvements