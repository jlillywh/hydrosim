#!/usr/bin/env python3
"""
HydroSim Development Tools

Simple command-line tools for managing development workflow.
"""

import subprocess
import sys
import argparse
import re
from pathlib import Path


def run_command(cmd, description=None):
    """Run a command and handle errors."""
    if description:
        print(f"🔄 {description}...")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {cmd}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def start_issue(issue_number, issue_type, description):
    """Start working on a new issue."""
    print(f"🚀 Starting work on issue #{issue_number}")
    
    # Ensure we're on develop branch
    if not run_command("git checkout develop", "Switching to develop branch"):
        return False
    
    if not run_command("git pull origin develop", "Pulling latest changes"):
        return False
    
    # Create new branch
    branch_name = f"{issue_type}/issue-{issue_number}-{description.lower().replace(' ', '-')}"
    if not run_command(f"git checkout -b {branch_name}", f"Creating branch {branch_name}"):
        return False
    
    print(f"✅ Ready to work on issue #{issue_number}")
    print(f"   Branch: {branch_name}")
    print(f"   Next steps:")
    print(f"   1. Make your changes")
    print(f"   2. Run tests: python -m pytest")
    print(f"   3. Commit: git commit -m 'Fix: description (closes #{issue_number})'")
    print(f"   4. Push: git push -u origin {branch_name}")
    
    return True


def run_tests(pattern=None):
    """Run the test suite."""
    print("🧪 Running tests...")
    
    cmd = "python -m pytest"
    if pattern:
        cmd += f" -k {pattern}"
    
    return run_command(cmd, "Running test suite")


def check_status():
    """Check current development status."""
    print("📊 Development Status")
    print("=" * 50)
    
    # Current branch
    result = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Current branch: {result.stdout.strip()}")
    
    # Git status
    run_command("git status --short", "Git status")
    
    # Test status
    print("\n🧪 Running quick test check...")
    run_command("python -c 'import hydrosim; print(f\"HydroSim {hydrosim.__version__} imported successfully\")'")


def finish_issue(issue_number):
    """Finish working on an issue."""
    print(f"🏁 Finishing work on issue #{issue_number}")
    
    # Check if there are uncommitted changes
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  You have uncommitted changes:")
        print(result.stdout)
        response = input("Do you want to commit them? (y/N): ")
        if response.lower() == 'y':
            message = input("Commit message: ")
            if not run_command(f'git add . && git commit -m "{message}"'):
                return False
        else:
            print("Please commit or stash your changes first.")
            return False
    
    # Get current branch
    result = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Could not determine current branch")
        return False
    
    current_branch = result.stdout.strip()
    
    if current_branch == "main" or current_branch == "develop":
        print("❌ You're on a main branch. Switch to your feature branch first.")
        return False
    
    # Push current branch
    if not run_command(f"git push -u origin {current_branch}", "Pushing branch"):
        return False
    
    print(f"✅ Issue #{issue_number} ready for review!")
    print(f"   Branch: {current_branch}")
    print(f"   Next steps:")
    print(f"   1. Create PR on GitHub: develop ← {current_branch}")
    print(f"   2. Add reviewers and description")
    print(f"   3. After merge, run: python scripts/dev_tools.py cleanup")
    
    return True


def cleanup_branches():
    """Clean up merged branches."""
    print("🧹 Cleaning up merged branches...")
    
    # Switch to develop
    if not run_command("git checkout develop"):
        return False
    
    # Pull latest
    if not run_command("git pull origin develop"):
        return False
    
    # List merged branches
    result = subprocess.run("git branch --merged", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        branches = [b.strip() for b in result.stdout.split('\n') if b.strip() and not b.strip().startswith('*') and b.strip() not in ['main', 'develop']]
        
        if branches:
            print("Merged branches found:")
            for branch in branches:
                print(f"  - {branch}")
            
            response = input("Delete these branches? (y/N): ")
            if response.lower() == 'y':
                for branch in branches:
                    run_command(f"git branch -d {branch}")
        else:
            print("No merged branches to clean up.")
    
    print("✅ Cleanup complete!")


def get_current_version():
    """Get current version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("❌ pyproject.toml not found")
        return None
    
    content = pyproject_path.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    
    print("❌ Could not find version in pyproject.toml")
    return None


def increment_version(version_type="patch"):
    """Increment version number."""
    current_version = get_current_version()
    if not current_version:
        return False
    
    print(f"📦 Current version: {current_version}")
    
    # Parse version (assuming semantic versioning)
    try:
        major, minor, patch = map(int, current_version.split('.'))
    except ValueError:
        print(f"❌ Invalid version format: {current_version}")
        return False
    
    # Increment based on type
    if version_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    elif version_type == "patch":
        patch += 1
    else:
        print(f"❌ Invalid version type: {version_type}")
        return False
    
    new_version = f"{major}.{minor}.{patch}"
    print(f"📦 New version: {new_version}")
    
    # Update pyproject.toml
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    updated_content = re.sub(
        r'version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content
    )
    pyproject_path.write_text(updated_content)
    
    # Update __init__.py
    init_path = Path("hydrosim/__init__.py")
    if init_path.exists():
        content = init_path.read_text()
        updated_content = re.sub(
            r'__version__\s*=\s*"[^"]+"',
            f'__version__ = "{new_version}"',
            content
        )
        init_path.write_text(updated_content)
    
    print(f"✅ Version updated to {new_version}")
    return new_version


def release(version_type="patch", skip_tests=False):
    """Create a new release with version increment, GitHub push, and PyPI publishing."""
    print("🚀 Starting release process...")
    
    # Check if we're on main/master branch
    result = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Could not determine current branch")
        return False
    
    current_branch = result.stdout.strip()
    if current_branch not in ["main", "master"]:
        print(f"❌ You must be on main/master branch for release. Current: {current_branch}")
        return False
    
    # Check for uncommitted changes
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("❌ You have uncommitted changes. Please commit or stash them first.")
        return False
    
    # Pull latest changes
    if not run_command("git pull origin main", "Pulling latest changes"):
        return False
    
    # Run tests unless skipped
    if not skip_tests:
        print("🧪 Running tests before release...")
        if not run_command("python -m pytest", "Running test suite"):
            print("❌ Tests failed. Fix tests before releasing.")
            return False
    
    # Increment version
    new_version = increment_version(version_type)
    if not new_version:
        return False
    
    # Commit version changes
    commit_msg = f"Bump version to {new_version}"
    if not run_command(f'git add pyproject.toml hydrosim/__init__.py && git commit -m "{commit_msg}"', "Committing version bump"):
        return False
    
    # Create git tag
    tag_name = f"v{new_version}"
    if not run_command(f'git tag -a {tag_name} -m "Release {new_version}"', f"Creating tag {tag_name}"):
        return False
    
    # Push to GitHub
    if not run_command("git push origin main", "Pushing to GitHub"):
        return False
    
    if not run_command(f"git push origin {tag_name}", "Pushing tag to GitHub"):
        return False
    
    # Build package
    print("📦 Building package...")
    if not run_command("python -m pip install --upgrade build twine", "Installing build tools"):
        return False
    
    if not run_command("python -m build", "Building package"):
        return False
    
    # Upload to PyPI
    print("🚀 Uploading to PyPI...")
    if not run_command("python -m twine upload dist/*", "Uploading to PyPI"):
        print("⚠️  PyPI upload failed. You may need to:")
        print("   1. Configure PyPI credentials: pip install keyring")
        print("   2. Or upload manually: python -m twine upload dist/*")
        return False
    
    print(f"🎉 Release {new_version} completed successfully!")
    print(f"   - Version bumped to {new_version}")
    print(f"   - Changes committed and pushed to GitHub")
    print(f"   - Tag {tag_name} created and pushed")
    print(f"   - Package uploaded to PyPI")
    
    return True


def build_package():
    """Build the package for testing."""
    print("📦 Building package...")
    
    # Install build tools
    if not run_command("python -m pip install --upgrade build", "Installing build tools"):
        return False
    
    # Clean previous builds
    import shutil
    for path in ["dist", "build", "*.egg-info"]:
        if Path(path).exists():
            if Path(path).is_dir():
                shutil.rmtree(path)
            else:
                Path(path).unlink()
    
    # Build package
    if not run_command("python -m build", "Building package"):
        return False
    
    print("✅ Package built successfully!")
    print("   Files created in dist/ directory")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="HydroSim Development Tools")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start issue command
    start_parser = subparsers.add_parser('start', help='Start working on an issue')
    start_parser.add_argument('issue_number', type=int, help='Issue number')
    start_parser.add_argument('issue_type', choices=['feature', 'bugfix', 'docs', 'test'], help='Type of issue')
    start_parser.add_argument('description', help='Brief description for branch name')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run tests')
    test_parser.add_argument('--pattern', '-p', help='Test pattern to match')
    
    # Status command
    subparsers.add_parser('status', help='Check development status')
    
    # Finish command
    finish_parser = subparsers.add_parser('finish', help='Finish working on an issue')
    finish_parser.add_argument('issue_number', type=int, help='Issue number')
    
    # Cleanup command
    subparsers.add_parser('cleanup', help='Clean up merged branches')
    
    # Version command
    version_parser = subparsers.add_parser('version', help='Show current version')
    
    # Release command
    release_parser = subparsers.add_parser('release', help='Create a new release')
    release_parser.add_argument('--type', choices=['major', 'minor', 'patch'], default='patch', 
                               help='Version increment type (default: patch)')
    release_parser.add_argument('--skip-tests', action='store_true', 
                               help='Skip running tests before release')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build package for testing')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'start':
        start_issue(args.issue_number, args.issue_type, args.description)
    elif args.command == 'test':
        run_tests(args.pattern)
    elif args.command == 'status':
        check_status()
    elif args.command == 'finish':
        finish_issue(args.issue_number)
    elif args.command == 'cleanup':
        cleanup_branches()
    elif args.command == 'version':
        version = get_current_version()
        if version:
            print(f"Current version: {version}")
    elif args.command == 'release':
        release(args.type, args.skip_tests)
    elif args.command == 'build':
        build_package()


if __name__ == "__main__":
    main()