"""Setup configuration for HydroSim package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read version from package
version = {}
with open("hydrosim/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            exec(line, version)
            break

setup(
    name="hydrosim",
    version=version["__version__"],
    author="J. Lillywh",
    author_email="",
    description="A Python framework for water resources planning with daily timestep simulation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jlillywh/hydrosim",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Hydrology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scipy>=1.10.0",
        "networkx>=3.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "hypothesis>=6.82.0",
            "pytest-cov>=4.1.0",
        ],
    },
    keywords="hydrology water-resources simulation optimization network-flow reservoir",
    project_urls={
        "Bug Reports": "https://github.com/jlillywh/hydrosim/issues",
        "Source": "https://github.com/jlillywh/hydrosim",
    },
)
