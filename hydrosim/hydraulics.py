"""
Hydraulic model abstractions for flow capacity calculations.

Hydraulic models calculate flow limits based on physical equations
(weir equations, pipe flow, etc.).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hydrosim.nodes import Node, StorageNode


class HydraulicModel(ABC):
    """Abstract base for hydraulic capacity calculations."""
    
    @abstractmethod
    def calculate_capacity(self, source_node: 'Node') -> float:
        """
        Calculate hydraulic capacity based on source state.
        
        Args:
            source_node: Source node providing hydraulic head
            
        Returns:
            Maximum hydraulic capacity
        """
        pass


class WeirModel(HydraulicModel):
    """Weir flow equation: Q = C * L * H^(3/2)"""
    
    def __init__(self, coefficient: float, length: float, crest_elevation: float):
        """
        Initialize a weir model.
        
        Args:
            coefficient: Weir discharge coefficient (C)
            length: Weir length (L)
            crest_elevation: Elevation of the weir crest
        """
        self.C = coefficient
        self.L = length
        self.crest_elev = crest_elevation
    
    def calculate_capacity(self, source_node: 'Node') -> float:
        """
        Calculate weir capacity based on upstream head.
        
        Args:
            source_node: Source node (must be StorageNode for head calculation)
            
        Returns:
            Maximum flow capacity based on weir equation
        """
        # Import here to avoid circular dependency
        from hydrosim.nodes import StorageNode
        
        if not isinstance(source_node, StorageNode):
            return float('inf')
        
        head = max(0.0, source_node.get_elevation() - self.crest_elev)
        return self.C * self.L * (head ** 1.5)


class PipeModel(HydraulicModel):
    """Pipe flow with fixed capacity."""
    
    def __init__(self, capacity: float):
        """
        Initialize a pipe model.
        
        Args:
            capacity: Fixed pipe capacity
        """
        self.capacity = capacity
    
    def calculate_capacity(self, source_node: 'Node') -> float:
        """
        Calculate pipe capacity (fixed value).
        
        Args:
            source_node: Source node (unused for fixed capacity)
            
        Returns:
            Fixed pipe capacity
        """
        return self.capacity
