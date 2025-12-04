"""
Custom exceptions for the HydroSim framework.

This module defines specific exception types for different error conditions
in the water resources simulation framework.
"""


class HydroSimError(Exception):
    """Base exception for all HydroSim errors."""
    pass


class NegativeStorageError(HydroSimError):
    """Raised when storage would become negative."""
    
    def __init__(self, node_id: str, current_storage: float, 
                 attempted_outflow: float, evaporation: float):
        """
        Initialize negative storage error.
        
        Args:
            node_id: Identifier of the storage node
            current_storage: Current storage volume
            attempted_outflow: Attempted outflow that would cause negative storage
            evaporation: Evaporation loss
        """
        self.node_id = node_id
        self.current_storage = current_storage
        self.attempted_outflow = attempted_outflow
        self.evaporation = evaporation
        
        available = current_storage - evaporation
        deficit = attempted_outflow - available
        
        message = (
            f"Storage node '{node_id}' would have negative storage. "
            f"Current storage: {current_storage:.2f}, "
            f"Evaporation: {evaporation:.2f}, "
            f"Available for outflow: {available:.2f}, "
            f"Attempted outflow: {attempted_outflow:.2f}, "
            f"Deficit: {deficit:.2f}"
        )
        super().__init__(message)


class InfeasibleNetworkError(HydroSimError):
    """Raised when network flow optimization is infeasible."""
    
    def __init__(self, message: str, conflicting_constraints: list = None):
        """
        Initialize infeasible network error.
        
        Args:
            message: Error message from solver
            conflicting_constraints: List of potentially conflicting constraints
        """
        self.conflicting_constraints = conflicting_constraints or []
        
        full_message = f"Network flow optimization is infeasible: {message}"
        
        if self.conflicting_constraints:
            full_message += "\n\nPotentially conflicting constraints:"
            for constraint in self.conflicting_constraints:
                full_message += f"\n  - {constraint}"
        
        super().__init__(full_message)


class ClimateDataError(HydroSimError):
    """Raised when climate data is missing or unavailable."""
    
    def __init__(self, requested_date, available_range=None, source_type=None):
        """
        Initialize climate data error.
        
        Args:
            requested_date: Date that was requested
            available_range: Tuple of (start_date, end_date) if known
            source_type: Type of climate source (timeseries, wgen, etc.)
        """
        self.requested_date = requested_date
        self.available_range = available_range
        self.source_type = source_type
        
        message = f"Climate data not available for date {requested_date}"
        
        if source_type:
            message += f" from {source_type} source"
        
        if available_range:
            start, end = available_range
            message += f". Available data range: {start} to {end}"
        
        super().__init__(message)


class EAVInterpolationError(HydroSimError):
    """Raised when EAV table interpolation is out of bounds."""
    
    def __init__(self, node_id: str, storage: float, 
                 min_volume: float, max_volume: float, 
                 interpolation_type: str = "elevation"):
        """
        Initialize EAV interpolation error.
        
        Args:
            node_id: Identifier of the storage node
            storage: Storage volume that is out of bounds
            min_volume: Minimum volume in EAV table
            max_volume: Maximum volume in EAV table
            interpolation_type: Type of interpolation (elevation or area)
        """
        self.node_id = node_id
        self.storage = storage
        self.min_volume = min_volume
        self.max_volume = max_volume
        self.interpolation_type = interpolation_type
        
        if storage < min_volume:
            bound_type = "below minimum"
            distance = min_volume - storage
        else:
            bound_type = "above maximum"
            distance = storage - max_volume
        
        message = (
            f"Storage node '{node_id}' has storage {bound_type} EAV table bounds. "
            f"Storage: {storage:.2f}, "
            f"Table range: [{min_volume:.2f}, {max_volume:.2f}], "
            f"Distance from bounds: {distance:.2f}. "
            f"Cannot interpolate {interpolation_type}."
        )
        super().__init__(message)


class ConfigurationError(HydroSimError):
    """Raised when node or network configuration is invalid."""
    
    def __init__(self, message: str):
        """
        Initialize configuration error.
        
        Args:
            message: Description of the configuration error
        """
        super().__init__(message)
