#!/usr/bin/env python3
"""
HydroSim Development Tools

Simple command-line tools for managing development workflow.
"""

import subprocess
import sys
import argparse
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
    print(f"   3. After merge, run: python dev_tools.py cleanup")
    
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


if __name__ == "__main__":
    main()