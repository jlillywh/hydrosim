#!/usr/bin/env python3
"""
Publishing script for HydroSim package to PyPI.

This script helps automate the process of building and uploading
the package to PyPI (Python Package Index).
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def check_prerequisites():
    """Check if required tools are installed."""
    print("🔍 Checking prerequisites...")
    
    # Check if build and twine are installed
    try:
        import build
        print("✅ build package is available")
    except ImportError:
        print("❌ build package not found. Install with: pip install build")
        return False
    
    try:
        subprocess.run(["twine", "--version"], check=True, capture_output=True)
        print("✅ twine is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ twine not found. Install with: pip install twine")
        return False
    
    return True


def clean_build():
    """Clean previous build artifacts."""
    print("\n🧹 Cleaning previous build artifacts...")
    
    # Remove build directories
    for dir_name in ["build", "dist", "*.egg-info"]:
        if os.path.exists(dir_name):
            if dir_name.endswith("*.egg-info"):
                # Handle glob pattern for egg-info
                import glob
                for path in glob.glob(dir_name):
                    if os.path.isdir(path):
                        import shutil
                        shutil.rmtree(path)
                        print(f"Removed {path}")
            else:
                import shutil
                shutil.rmtree(dir_name)
                print(f"Removed {dir_name}")
    
    print("✅ Build artifacts cleaned")


def run_tests():
    """Run the test suite."""
    if not run_command("python -m pytest", "Running tests"):
        print("⚠️  Tests failed. Continue anyway? (y/N): ", end="")
        if input().lower() != 'y':
            return False
    return True


def build_package():
    """Build the package."""
    return run_command("python -m build", "Building package")


def check_package():
    """Check the built package."""
    return run_command("twine check dist/*", "Checking package")


def upload_to_test_pypi():
    """Upload to Test PyPI."""
    print("\n📤 Uploading to Test PyPI...")
    print("You'll need your Test PyPI credentials.")
    return run_command("twine upload --repository testpypi dist/*", "Uploading to Test PyPI")


def upload_to_pypi():
    """Upload to PyPI."""
    print("\n📤 Uploading to PyPI...")
    print("You'll need your PyPI credentials.")
    print("⚠️  This will make the package publicly available!")
    print("Continue? (y/N): ", end="")
    if input().lower() != 'y':
        print("Upload cancelled.")
        return False
    
    return run_command("twine upload dist/*", "Uploading to PyPI")


def main():
    """Main publishing workflow."""
    print("🚀 HydroSim PyPI Publishing Script")
    print("=" * 40)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Clean previous builds
    clean_build()
    
    # Run tests
    print("\n🧪 Running tests...")
    if not run_tests():
        print("Exiting due to test failures.")
        sys.exit(1)
    
    # Build package
    if not build_package():
        print("Build failed. Exiting.")
        sys.exit(1)
    
    # Check package
    if not check_package():
        print("Package check failed. Exiting.")
        sys.exit(1)
    
    # Ask what to do next
    print("\n🎯 Package built successfully!")
    print("What would you like to do?")
    print("1. Upload to Test PyPI (recommended first)")
    print("2. Upload to PyPI (production)")
    print("3. Exit")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        if upload_to_test_pypi():
            print("\n✅ Successfully uploaded to Test PyPI!")
            print("Test installation with:")
            print("pip install --index-url https://test.pypi.org/simple/ hydrosim")
    elif choice == "2":
        if upload_to_pypi():
            print("\n🎉 Successfully published to PyPI!")
            print("Install with: pip install hydrosim")
    elif choice == "3":
        print("Exiting without upload.")
    else:
        print("Invalid choice. Exiting.")
    
    print("\n📁 Build artifacts are in the 'dist/' directory")


if __name__ == "__main__":
    main()