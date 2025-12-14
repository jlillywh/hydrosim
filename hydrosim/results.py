"""
Results output system for HydroSim simulations.

The results writer provides structured output of simulation results in
CSV or JSON format for time series analysis. It captures all key simulation
outputs including flows, storage levels, demand deficits, and inflows.

Example:
    >>> import hydrosim as hs
    >>> 
    >>> # Run simulation
    >>> engine = hs.SimulationEngine(network, climate_engine)
    >>> results = engine.run(start_date='2020-01-01', end_date='2020-12-31')
    >>> 
    >>> # Create results writer
    >>> writer = hs.ResultsWriter(results, output_dir='output/')
    >>> 
    >>> # Write all results to CSV files
    >>> writer.write_all_csv()
    >>> 
    >>> # Or write specific components
    >>> writer.write_flows_csv('flows.csv')
    >>> writer.write_storage_csv('storage.csv')
    >>> writer.write_demands_csv('demands.csv')
    >>> 
    >>> # Export to JSON for programmatic analysis
    >>> writer.write_json('results.json')

Output Files:
    - flows.csv: Daily flow values for all links
    - storage.csv: Daily storage volumes for all StorageNodes  
    - demands.csv: Daily demand and deficit values for all DemandNodes
    - inflows.csv: Daily inflow values for all SourceNodes
    - results.json: Complete results in structured JSON format

All outputs include timestamps and are suitable for time series analysis
and visualization tools.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from hydrosim.nodes import StorageNode, DemandNode, SourceNode


class ResultsWriter:
    """
    Structured output writer for simulation results.
    
    The ResultsWriter collects and writes simulation results including:
    - Flow values for all links at each timestep
    - Storage volumes for all StorageNodes at each timestep
    - Demand deficits for all DemandNodes at each timestep
    - Inflows for all SourceNodes at each timestep
    
    All outputs are at daily resolution as required by the framework.
    
    Attributes:
        output_dir: Directory for output files
        format: Output format ('csv' or 'json')
        results: Accumulated results from simulation timesteps
    """
    
    def __init__(self, output_dir: str = ".", format: str = "csv"):
        """
        Initialize results writer.
        
        Args:
            output_dir: Directory path for output files
            format: Output format, either 'csv' or 'json'
        
        Raises:
            ValueError: If format is not 'csv' or 'json'
        """
        if format not in ['csv', 'json']:
            raise ValueError(f"Format must be 'csv' or 'json', got '{format}'")
        
        self.output_dir = Path(output_dir)
        self.format = format
        self.results: List[Dict[str, Any]] = []
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def add_timestep(self, timestep_results: Dict[str, Any]) -> None:
        """
        Add results from a single timestep.
        
        Args:
            timestep_results: Dictionary containing timestep results from
                            SimulationEngine.step(), including:
                            - timestep: Timestep number
                            - date: Date of timestep
                            - climate: Climate state
                            - node_states: State of all nodes
                            - flows: Flow allocations for all links
        """
        self.results.append(timestep_results)
    
    def write_all(self, prefix: str = "results") -> Dict[str, str]:
        """
        Write all accumulated results to files.
        
        This method writes separate files for:
        - Link flows
        - Storage node states
        - Demand node states
        - Source node states
        
        Args:
            prefix: Prefix for output filenames
        
        Returns:
            Dictionary mapping output type to filename
        """
        if not self.results:
            return {}
        
        written_files = {}
        
        if self.format == 'csv':
            written_files['flows'] = self._write_flows_csv(prefix)
            written_files['storage'] = self._write_storage_csv(prefix)
            written_files['demands'] = self._write_demands_csv(prefix)
            written_files['sources'] = self._write_sources_csv(prefix)
        else:  # json
            written_files['all'] = self._write_json(prefix)
        
        return written_files
    
    def _write_flows_csv(self, prefix: str) -> str:
        """
        Write link flows to CSV file.
        
        Output format:
        timestep, date, link_id, flow
        
        Args:
            prefix: Filename prefix
        
        Returns:
            Path to written file
        """
        filename = self.output_dir / f"{prefix}_flows.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestep', 'date', 'link_id', 'flow'])
            
            for result in self.results:
                timestep = result['timestep']
                date = result['date'].strftime('%Y-%m-%d')
                
                for link_id, flow in result['flows'].items():
                    writer.writerow([timestep, date, link_id, flow])
        
        return str(filename)
    
    def _write_storage_csv(self, prefix: str) -> str:
        """
        Write storage node states to CSV file.
        
        Output format:
        timestep, date, node_id, storage, elevation, surface_area, evap_loss
        
        Args:
            prefix: Filename prefix
        
        Returns:
            Path to written file
        """
        filename = self.output_dir / f"{prefix}_storage.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestep', 'date', 'node_id', 'storage', 
                           'elevation', 'surface_area', 'evap_loss'])
            
            for result in self.results:
                timestep = result['timestep']
                date = result['date'].strftime('%Y-%m-%d')
                
                for node_id, state in result['node_states'].items():
                    # Only write storage nodes (they have 'storage' key)
                    if 'storage' in state:
                        writer.writerow([
                            timestep, date, node_id,
                            state['storage'],
                            state['elevation'],
                            state['surface_area'],
                            state['evap_loss']
                        ])
        
        return str(filename)
    
    def _write_demands_csv(self, prefix: str) -> str:
        """
        Write demand node states to CSV file.
        
        Output format:
        timestep, date, node_id, request, delivered, deficit
        
        Args:
            prefix: Filename prefix
        
        Returns:
            Path to written file
        """
        filename = self.output_dir / f"{prefix}_demands.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestep', 'date', 'node_id', 'request', 
                           'delivered', 'deficit'])
            
            for result in self.results:
                timestep = result['timestep']
                date = result['date'].strftime('%Y-%m-%d')
                
                for node_id, state in result['node_states'].items():
                    # Only write demand nodes (they have 'deficit' key)
                    if 'deficit' in state:
                        writer.writerow([
                            timestep, date, node_id,
                            state['request'],
                            state['delivered'],
                            state['deficit']
                        ])
        
        return str(filename)
    
    def _write_sources_csv(self, prefix: str) -> str:
        """
        Write source node states to CSV file.
        
        Output format:
        timestep, date, node_id, inflow
        
        Args:
            prefix: Filename prefix
        
        Returns:
            Path to written file
        """
        filename = self.output_dir / f"{prefix}_sources.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestep', 'date', 'node_id', 'inflow'])
            
            for result in self.results:
                timestep = result['timestep']
                date = result['date'].strftime('%Y-%m-%d')
                
                for node_id, state in result['node_states'].items():
                    # Only write source nodes (they have 'inflow' key and not 'deficit')
                    if 'inflow' in state and 'deficit' not in state:
                        writer.writerow([
                            timestep, date, node_id,
                            state['inflow']
                        ])
        
        return str(filename)
    
    def _write_json(self, prefix: str) -> str:
        """
        Write all results to JSON file.
        
        The JSON format includes all data in a structured format suitable
        for programmatic analysis.
        
        Args:
            prefix: Filename prefix
        
        Returns:
            Path to written file
        """
        filename = self.output_dir / f"{prefix}_all.json"
        
        # Convert datetime objects to strings for JSON serialization
        json_results = []
        for result in self.results:
            json_result = {
                'timestep': result['timestep'],
                'date': result['date'].strftime('%Y-%m-%d'),
                'flows': result['flows'],
                'node_states': result['node_states']
            }
            json_results.append(json_result)
        
        with open(filename, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        return str(filename)
    
    def clear(self) -> None:
        """Clear accumulated results."""
        self.results = []
    
    def get_results(self) -> List[Dict[str, Any]]:
        """
        Get accumulated results.
        
        Returns:
            List of timestep results dictionaries
        """
        return self.results
