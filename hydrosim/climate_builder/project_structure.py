"""
Project directory structure management for Climate Builder.

This module provides the ProjectStructure class that manages the standardized
directory layout for climate data projects. It ensures consistent organization
of raw data, processed data, configuration files, and outputs.

Directory Structure:
    project_root/
    ├── config/          # YAML configuration files
    ├── data/
    │   ├── raw/         # Original downloaded data files (.dly files)
    │   └── processed/   # Cleaned and processed data files (CSV, parameters)
    └── outputs/         # Simulation results

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from pathlib import Path
from typing import Optional


class ProjectStructure:
    """Manages standardized directory structure for climate data projects.
    
    This class creates and manages the directory layout required by Climate Builder.
    All file operations should use the paths provided by this class to ensure
    consistent organization across projects.
    
    Attributes:
        root_dir: Root directory of the project
        
    Example:
        >>> project = ProjectStructure("/path/to/my_project")
        >>> project.initialize_structure()
        >>> raw_dir = project.get_raw_data_dir()
        >>> # Save downloaded .dly file to raw_dir
    """
    
    def __init__(self, root_dir: Path | str):
        """Initialize project structure manager.
        
        Args:
            root_dir: Root directory for the project. Can be a Path object or string.
                     Will be created if it doesn't exist.
        
        Example:
            >>> project = ProjectStructure("./my_climate_project")
            >>> project = ProjectStructure(Path("/absolute/path/to/project"))
        """
        self.root_dir = Path(root_dir).resolve()
    
    def initialize_structure(self) -> None:
        """Create the standardized directory structure.
        
        Creates all required directories if they don't already exist:
        - config/: For YAML configuration files
        - data/raw/: For original downloaded data files
        - data/processed/: For cleaned and processed data files
        - outputs/: For simulation results
        
        This method is idempotent - it can be called multiple times safely.
        Existing directories and files will not be modified.
        
        Requirements: 7.1, 7.2, 7.3, 7.4
        
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> project.initialize_structure()
            >>> # All directories are now created
        """
        # Create root directory
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.get_config_dir().mkdir(parents=True, exist_ok=True)
        self.get_raw_data_dir().mkdir(parents=True, exist_ok=True)
        self.get_processed_data_dir().mkdir(parents=True, exist_ok=True)
        self.get_outputs_dir().mkdir(parents=True, exist_ok=True)
    
    def get_config_dir(self) -> Path:
        """Get path to configuration directory.
        
        Returns:
            Path to config/ directory
            
        Note:
            Directory is created if it doesn't exist.
            
        Requirements: 7.1
        
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> config_dir = project.get_config_dir()
            >>> yaml_path = config_dir / "simulation.yaml"
        """
        config_dir = self.root_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def get_raw_data_dir(self) -> Path:
        """Get path to raw data directory.
        
        Returns:
            Path to data/raw/ directory
            
        Note:
            Directory is created if it doesn't exist.
            This is where original downloaded .dly files should be saved.
            
        Requirements: 7.2, 7.5
        
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> raw_dir = project.get_raw_data_dir()
            >>> dly_path = raw_dir / "USW00024233.dly"
        """
        raw_dir = self.root_dir / "data" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        return raw_dir
    
    def get_processed_data_dir(self) -> Path:
        """Get path to processed data directory.
        
        Returns:
            Path to data/processed/ directory
            
        Note:
            Directory is created if it doesn't exist.
            This is where processed CSV files and WGEN parameters should be saved.
            
        Requirements: 7.3, 7.6
        
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> processed_dir = project.get_processed_data_dir()
            >>> csv_path = processed_dir / "observed_climate.csv"
            >>> params_path = processed_dir / "wgen_params.csv"
        """
        processed_dir = self.root_dir / "data" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        return processed_dir
    
    def get_outputs_dir(self) -> Path:
        """Get path to outputs directory.
        
        Returns:
            Path to outputs/ directory
            
        Note:
            Directory is created if it doesn't exist.
            This is where simulation results should be saved.
            
        Requirements: 7.4
        
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> outputs_dir = project.get_outputs_dir()
            >>> results_path = outputs_dir / "simulation_results.csv"
        """
        outputs_dir = self.root_dir / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        return outputs_dir
    
    def get_observed_climate_path(self) -> Path:
        """Get standard path for observed climate CSV file.
        
        Returns:
            Path to data/processed/observed_climate.csv
            
        Note:
            This is a convenience method that returns the standard filename
            in the processed data directory. The file may not exist yet.
            
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> csv_path = project.get_observed_climate_path()
            >>> # Save parsed data to csv_path
        """
        return self.get_processed_data_dir() / "observed_climate.csv"
    
    def get_wgen_params_path(self) -> Path:
        """Get standard path for WGEN parameters CSV file.
        
        Returns:
            Path to data/processed/wgen_params.csv
            
        Note:
            This is a convenience method that returns the standard filename
            in the processed data directory. The file may not exist yet.
            
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> params_path = project.get_wgen_params_path()
            >>> # Save generated parameters to params_path
        """
        return self.get_processed_data_dir() / "wgen_params.csv"
    
    def get_data_quality_report_path(self) -> Path:
        """Get standard path for data quality report file.
        
        Returns:
            Path to data/processed/data_quality_report.txt
            
        Note:
            This is a convenience method that returns the standard filename
            in the processed data directory. The file may not exist yet.
            
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> report_path = project.get_data_quality_report_path()
            >>> # Save quality report to report_path
        """
        return self.get_processed_data_dir() / "data_quality_report.txt"
    
    def get_dly_file_path(self, station_id: str) -> Path:
        """Get path for a GHCN .dly file.
        
        Args:
            station_id: GHCN station identifier (e.g., "USW00024233")
            
        Returns:
            Path to data/raw/{station_id}.dly
            
        Note:
            This is a convenience method that returns the standard filename
            for a station's .dly file. The file may not exist yet.
            
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> dly_path = project.get_dly_file_path("USW00024233")
            >>> # Download .dly file to dly_path
        """
        return self.get_raw_data_dir() / f"{station_id}.dly"
    
    def exists(self) -> bool:
        """Check if the project root directory exists.
        
        Returns:
            True if root directory exists, False otherwise
            
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> if not project.exists():
            ...     project.initialize_structure()
        """
        return self.root_dir.exists()
    
    def is_initialized(self) -> bool:
        """Check if the project structure has been initialized.
        
        Returns:
            True if all required directories exist, False otherwise
            
        Example:
            >>> project = ProjectStructure("./my_project")
            >>> if not project.is_initialized():
            ...     project.initialize_structure()
        """
        return (
            self.get_config_dir().exists() and
            self.get_raw_data_dir().exists() and
            self.get_processed_data_dir().exists() and
            self.get_outputs_dir().exists()
        )
    
    def __repr__(self) -> str:
        """Return string representation of project structure.
        
        Returns:
            String showing root directory and initialization status
        """
        status = "initialized" if self.is_initialized() else "not initialized"
        return f"ProjectStructure(root_dir={self.root_dir}, status={status})"
