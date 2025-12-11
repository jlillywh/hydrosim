# HydroSim Issues Tracker

*Last updated: Manually updated after Issue #2 completion*

## 🐛 Bug Fixes

## ✨ Enhancements

### Medium Priority

- [x] **Issue #2**: show 1 plot-specific legend to the right of each chart
  - **Status**: ✅ RESOLVED
  - **Priority**: Medium
  - **Labels**: enhancement
  - **GitHub**: https://github.com/jlillywh/hydrosim/issues/2
  - **Assignee**: Kiro AI
  - **Branch**: feature/issue-2-show-plot-specific-legend-to-the-right-of-each-chart
  - **Notes**: ✅ FIXED - Implemented custom legend annotations positioned to the right of each subplot. Replaced problematic native Plotly legend with HTML-styled annotations that show proper colors and line styles. Each subplot now has its own legend with clear visual indicators and proper positioning that won't be cut off.

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

## Status Definitions

- **Open**: Issue identified, not yet started
- **In Progress**: Actively being worked on  
- **Review**: Code complete, needs review/testing
- **Closed**: Issue resolved and merged

## Priority Guidelines

- **High**: Critical bugs, security issues, blocking other work
- **Medium**: Important features, non-critical bugs, performance improvements
- **Low**: Nice-to-have features, code cleanup, minor improvements

## Recent Completions

✅ **Issue #4** (Network Layout): Fixed spread-out network graphs with compact spacing
✅ **Issue #2** (Subplot Legends): Implemented individual legends for each plot