# HydroSim Issues Tracker

## ✅ Completed Issues

- [x] **Issue #1**: Implement Look-ahead Optimization
  - **Status**: Closed ✅
  - **Priority**: High
  - **Type**: Enhancement
  - **Completed**: 2024-12-10
  - **Version**: v0.4.0
  - **Notes**: Successfully implemented multi-timestep optimization using time-expanded graphs. Added LookaheadSolver class with configurable horizon, perfect foresight, and hedging capability. All tests passing.

- [x] **Issue #2**: Implement subplot-specific legends
  - **Status**: Closed ✅
  - **Priority**: Medium
  - **Type**: Enhancement
  - **Completed**: 2024-12-10
  - **Version**: v0.3.1
  - **Notes**: Implemented custom legend system using HTML-styled annotations with proper positioning and visual indicators.

- [x] **Issue #3**: Fix plot axis title character encoding
  - **Status**: Closed ✅
  - **Priority**: Medium
  - **Type**: Bug
  - **Completed**: 2024-12-10
  - **Version**: v0.3.1
  - **Notes**: Fixed Unicode character corruption by implementing ASCII-safe formatting and updating all YAML files.

- [x] **Issue #4**: Fix network graph spacing
  - **Status**: Closed ✅
  - **Priority**: Low
  - **Type**: Bug
  - **Completed**: 2024-12-10
  - **Version**: v0.3.1
  - **Notes**: Fixed network graph spacing with 3x reduction in node spacing and proper axis ranges.

- [x] **Issue #5**: Implement simulation date configuration in YAML files
  - **Status**: Closed ✅
  - **Priority**: Medium
  - **Type**: Enhancement
  - **Completed**: 2024-12-10
  - **Version**: v0.3.1
  - **Notes**: Added simulation configuration parsing with date range and duration options.

## 🐛 Open Bug Fixes

### High Priority
- [ ] **Issue #6**: [Description of critical bug]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

### Medium Priority
- [ ] **Issue #7**: [Description of bug]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

### Low Priority
- [ ] **Issue #8**: [Description of minor bug]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

## ✨ Open Enhancements

### High Priority
- [ ] **Issue #9**: [Description of important enhancement]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

### Medium Priority
- [ ] **Issue #10**: [Description of enhancement]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

### Low Priority
- [ ] **Issue #11**: [Description of nice-to-have enhancement]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

## 📚 Documentation

- [ ] **Issue #7**: [Documentation improvement]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

## 🧪 Testing

- [ ] **Issue #8**: [Testing improvement]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

## 🔧 Infrastructure

- [ ] **Issue #9**: [Infrastructure improvement]
  - **Status**: Open
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: 

---

## Issue Template

When adding new issues, use this template:

```markdown
- [ ] **Issue #X**: [Brief description]
  - **Status**: Open/In Progress/Review/Closed
  - **Priority**: High/Medium/Low
  - **Type**: Bug/Enhancement/Documentation/Testing/Infrastructure
  - **Assignee**: [Your name or team member]
  - **Branch**: [feature/issue-X-description or bugfix/issue-X-description]
  - **Estimated Time**: [hours/days]
  - **Dependencies**: [Other issues this depends on]
  - **Notes**: [Additional context, links, etc.]
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