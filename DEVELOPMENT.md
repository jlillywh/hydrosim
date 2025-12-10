# HydroSim Development Guide

## Development Workflow

### Branch Strategy
- `main`: Production-ready code, matches PyPI releases
- `develop`: Integration branch for new features
- `feature/issue-X`: Individual feature branches
- `bugfix/issue-X`: Individual bug fix branches

### Working on Issues

1. **Start from develop branch**:
   ```bash
   git checkout develop
   git pull origin develop
   ```

2. **Create feature/bugfix branch**:
   ```bash
   # For new features
   git checkout -b feature/issue-123-add-new-feature
   
   # For bug fixes
   git checkout -b bugfix/issue-456-fix-calculation-error
   ```

3. **Make changes and test**:
   ```bash
   # Make your changes
   # Run tests
   python -m pytest
   
   # Add and commit
   git add .
   git commit -m "Fix: Description of what was fixed (closes #456)"
   ```

4. **Push and create PR**:
   ```bash
   git push -u origin feature/issue-123-add-new-feature
   # Create PR on GitHub: develop ← feature/issue-123
   ```

5. **After PR is merged**:
   ```bash
   git checkout develop
   git pull origin develop
   git branch -d feature/issue-123-add-new-feature
   ```

### Testing Requirements

Before submitting any PR:
- [ ] All existing tests pass: `python -m pytest`
- [ ] New tests added for new functionality
- [ ] Code follows existing style patterns
- [ ] Documentation updated if needed

### Release Process

1. **Prepare release on develop**:
   - Update version numbers
   - Update CHANGELOG.md
   - Run full test suite

2. **Merge to main**:
   ```bash
   git checkout main
   git merge develop
   git tag v0.3.2
   git push origin main --tags
   ```

3. **Publish to PyPI**:
   ```bash
   python publish.py
   ```

## Issue Categories

### 🐛 Bug Fixes
- Calculation errors
- Unexpected behavior
- Performance issues
- Memory leaks

### ✨ Enhancements
- New features
- Improved algorithms
- Better user experience
- Performance optimizations

### 📚 Documentation
- API documentation
- Examples
- Tutorials
- README improvements

### 🧪 Testing
- Unit tests
- Integration tests
- Performance tests
- Test coverage improvements

### 🔧 Infrastructure
- Build system
- CI/CD
- Development tools
- Package management

## Current Development Priorities

### High Priority
- [ ] Critical bug fixes
- [ ] Performance improvements
- [ ] Documentation gaps

### Medium Priority
- [ ] New features
- [ ] Code refactoring
- [ ] Test coverage

### Low Priority
- [ ] Nice-to-have features
- [ ] Code cleanup
- [ ] Development tools

## Getting Started with Development

1. **Set up development environment**:
   ```bash
   git clone https://github.com/jlillywh/hydrosim.git
   cd hydrosim
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -e .
   pip install -r requirements.txt
   ```

2. **Run tests to verify setup**:
   ```bash
   python -m pytest
   ```

3. **Check code style**:
   ```bash
   # Add linting tools if desired
   # pip install flake8 black
   # flake8 hydrosim/
   # black --check hydrosim/
   ```

## Useful Commands

```bash
# Run specific test file
python -m pytest tests/test_climate_engine.py

# Run tests with coverage
python -m pytest --cov=hydrosim

# Run tests in parallel
python -m pytest -n auto

# Run only failed tests
python -m pytest --lf

# Run tests matching pattern
python -m pytest -k "test_storage"
```