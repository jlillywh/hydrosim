# PyPI Publishing Checklist for HydroSim

## Pre-Publishing Setup

### 1. Install Publishing Tools
```bash
pip install build twine
```

### 2. Create PyPI Accounts
- [ ] Create account at [PyPI](https://pypi.org/account/register/)
- [ ] Create account at [Test PyPI](https://test.pypi.org/account/register/) (for testing)
- [ ] Enable 2FA on both accounts (recommended)

### 3. Configure API Tokens (Recommended)
1. Go to PyPI Account Settings → API tokens
2. Create a new token with scope "Entire account" or specific to your project
3. Save the token securely
4. Configure in `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-api-token-here
```

## Pre-Publishing Checklist

### Code Quality
- [ ] All tests pass: `pytest`
- [ ] Code is properly documented
- [ ] Version number updated in `hydrosim/__init__.py`
- [ ] CHANGELOG.md updated with new version

### Package Configuration
- [ ] `pyproject.toml` has correct metadata
- [ ] `README.md` is comprehensive and up-to-date
- [ ] `LICENSE` file exists
- [ ] Dependencies are correctly specified
- [ ] Package excludes test/example files appropriately

### Version Management
- [ ] Version follows semantic versioning (MAJOR.MINOR.PATCH)
- [ ] Version is consistent across:
  - [ ] `hydrosim/__init__.py` (currently: 0.3.0)
  - [ ] `pyproject.toml` (currently: 0.3.0)
- [ ] Git tag created for the version: `git tag v0.3.0`

### Documentation
- [ ] README.md includes:
  - [ ] Clear description
  - [ ] Installation instructions
  - [ ] Usage examples
  - [ ] API documentation links
- [ ] Examples work with current version
- [ ] Docstrings are complete

## Publishing Process

### Option 1: Using the Publishing Script (Recommended)
```bash
python publish.py
```

### Option 2: Manual Process

#### 1. Clean Previous Builds
```bash
rm -rf build/ dist/ *.egg-info/
```

#### 2. Build Package
```bash
python -m build
```

#### 3. Check Package
```bash
twine check dist/*
```

#### 4. Upload to Test PyPI (First Time)
```bash
twine upload --repository testpypi dist/*
```

#### 5. Test Installation from Test PyPI
```bash
pip install --index-url https://test.pypi.org/simple/ hydrosim
```

#### 6. Upload to PyPI (Production)
```bash
twine upload dist/*
```

## Post-Publishing

### Verify Installation
- [ ] Install from PyPI: `pip install hydrosim`
- [ ] Test basic functionality
- [ ] Check package page on PyPI

### Update Repository
- [ ] Push version tag to GitHub: `git push origin v0.3.0`
- [ ] Create GitHub release with changelog
- [ ] Update documentation if needed

### Announce Release
- [ ] Update project README with new version
- [ ] Announce on relevant channels
- [ ] Update any dependent projects

## Troubleshooting

### Common Issues

**Build Fails:**
- Check `pyproject.toml` syntax
- Ensure all dependencies are available
- Check file permissions

**Upload Fails:**
- Verify credentials in `~/.pypirc`
- Check if package name already exists
- Ensure version number is unique

**Import Fails After Installation:**
- Check package structure
- Verify `__init__.py` exports
- Check for missing dependencies

### Version Conflicts
If you need to fix a version after uploading:
1. You cannot overwrite existing versions on PyPI
2. Increment the patch version (e.g., 0.3.0 → 0.3.1)
3. Upload the fixed version

## Security Notes

- Never commit API tokens to version control
- Use API tokens instead of passwords
- Enable 2FA on PyPI accounts
- Regularly rotate API tokens
- Use scoped tokens when possible

## Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [setuptools Documentation](https://setuptools.pypa.io/)