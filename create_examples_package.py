#!/usr/bin/env python3
"""
Create HydroSim Examples Package for GitHub Releases

This script creates a zip file containing all examples and necessary files
for users to get started with HydroSim without cloning the repository.
"""

import os
import shutil
import zipfile
from pathlib import Path
import hydrosim

def create_examples_package():
    """Create a zip package with all examples and dependencies."""
    
    version = hydrosim.__version__
    package_name = f"hydrosim-examples-v{version}"
    
    print(f"🎁 Creating HydroSim Examples Package v{version}")
    print("=" * 50)
    
    # Create temporary directory
    temp_dir = Path(package_name)
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    print(f"📁 Created temporary directory: {temp_dir}")
    
    # Copy example files
    examples_dir = Path("examples")
    essential_files = [
        # Starter files
        "hydrosim_starter_notebook.py",  # Our self-contained starter
        
        # Core examples
        "quick_start.py",
        "notebook_quick_start.py",
        "network_visualization_demo.py",
        "storage_drawdown_demo.py",
        "results_visualization_demo.py",
        "results_output_example.py",
        
        # YAML configurations
        "simple_network.yaml",
        "complex_network.yaml",
        "storage_drawdown_example.yaml",
        "wgen_example.yaml",
        
        # Data files
        "climate_data.csv",
        "inflow_data.csv",
        "inflow_data_365.csv",
        "wgen_params_template.csv",
        
        # Weather generation
        "wgen_example.py",
        
        # Climate builder examples
        "climate_builder_fetch_example.py",
        "parameter_generator_example.py",
        "data_quality_example.py",
        "precipitation_params_example.py",
        "temperature_params_example.py",
        "solar_params_example.py",
        
        # Documentation
        "README.md",
        "CLIMATE_BUILDER_README.md",
    ]
    
    # Copy files that exist
    copied_files = []
    for filename in essential_files:
        source_path = examples_dir / filename if filename != "hydrosim_starter_notebook.py" else Path(filename)
        target_path = temp_dir / filename
        
        if source_path.exists():
            shutil.copy2(source_path, target_path)
            copied_files.append(filename)
            print(f"   ✅ {filename}")
        else:
            print(f"   ⚠️  {filename} (not found, skipping)")
    
    # Create a comprehensive README for the package
    readme_content = f"""# HydroSim Examples Package v{version}

Welcome to HydroSim! This package contains everything you need to get started with water resources modeling.

## 🚀 Quick Start (Recommended for Beginners)

### Option 1: Self-Contained Starter (No external files needed)
```bash
pip install hydrosim matplotlib jupyter
python hydrosim_starter_notebook.py
```

### Option 2: Jupyter Notebook (Interactive)
```bash
pip install hydrosim matplotlib jupyter
jupyter notebook
# Copy sections from hydrosim_starter_notebook.py into notebook cells
```

## 📚 Example Files

### 🎯 Beginner Examples
- **`hydrosim_starter_notebook.py`** - Complete self-contained example (START HERE!)
- **`notebook_quick_start.py`** - Jupyter-optimized tutorial
- **`quick_start.py`** - Original quick start with YAML files

### 🏗️ Network Examples
- **`network_visualization_demo.py`** - Create interactive network diagrams
- **`storage_drawdown_demo.py`** - Reservoir operation scenarios
- **`results_visualization_demo.py`** - Analyze and plot results

### ⚙️ Configuration Files
- **`simple_network.yaml`** - Basic reservoir-city system
- **`complex_network.yaml`** - Multi-reservoir system with controls
- **`storage_drawdown_example.yaml`** - Storage operation examples

### 🌤️ Weather & Climate
- **`wgen_example.py`** - Weather generation with WGEN
- **`climate_builder_fetch_example.py`** - Download real climate data
- **`parameter_generator_example.py`** - Generate WGEN parameters

### 📊 Data Files
- **`climate_data.csv`** - Sample climate data
- **`inflow_data.csv`** - Sample river inflow (30 days)
- **`inflow_data_365.csv`** - Sample river inflow (1 year)
- **`wgen_params_template.csv`** - Weather generator parameters

## 🎓 Learning Path

### Step 1: Get Started
```bash
python hydrosim_starter_notebook.py
```

### Step 2: Explore Networks
```bash
python network_visualization_demo.py
python storage_drawdown_demo.py
```

### Step 3: Try YAML Configuration
```bash
python quick_start.py
```

### Step 4: Advanced Topics
```bash
python wgen_example.py
python climate_builder_fetch_example.py
```

## 📖 Documentation

- **Main Documentation**: https://github.com/jlillywh/hydrosim#readme
- **API Reference**: Use `help(hydrosim)` in Python
- **Interactive Help**: Use `hydrosim.help()` and `hydrosim.quick_start()`

## 🆘 Getting Help

```python
import hydrosim as hs
hs.help()        # Comprehensive help
hs.quick_start() # Interactive tutorial
hs.examples()    # Browse examples
hs.about()       # Version info
```

## 🐛 Issues & Support

- **GitHub Issues**: https://github.com/jlillywh/hydrosim/issues
- **Discussions**: https://github.com/jlillywh/hydrosim/discussions

## 📦 Installation

```bash
# Basic installation
pip install hydrosim

# With visualization support
pip install hydrosim matplotlib plotly

# For Jupyter notebooks
pip install hydrosim matplotlib plotly jupyter
```

---

**Happy modeling! 🌊**
"""
    
    # Write the README
    with open(temp_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"   ✅ README.md (package guide)")
    
    # Create the zip file
    zip_filename = f"{package_name}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                arc_name = file_path.relative_to(temp_dir.parent)
                zipf.write(file_path, arc_name)
    
    # Clean up temp directory
    shutil.rmtree(temp_dir)
    
    # Get file size
    zip_size = os.path.getsize(zip_filename) / 1024  # KB
    
    print(f"\n🎉 Package created successfully!")
    print(f"   📦 File: {zip_filename}")
    print(f"   📏 Size: {zip_size:.1f} KB")
    print(f"   📁 Files: {len(copied_files)} examples + README")
    
    print(f"\n📋 Next Steps:")
    print(f"   1. Upload {zip_filename} to GitHub Releases")
    print(f"   2. Tag the release as v{version}")
    print(f"   3. Add release notes describing the examples")
    print(f"   4. Update documentation to mention the examples package")
    
    return zip_filename

if __name__ == "__main__":
    create_examples_package()