"""
Control system abstractions for link flow management.

Controls allow modeling of operational rules and automated control logic
that modify link capacities based on system state. They enable realistic
representation of operational policies and physical constraints.

Example:
    >>> import hydrosim as hs
    >>> 
    >>> # Create nodes
    >>> eav = hs.ElevationAreaVolume([100, 110], [1000, 2000], [0, 10000])
    >>> reservoir = hs.StorageNode('reservoir', initial_storage=5000, 
    ...                           eav_table=eav, max_storage=10000)
    >>> city = hs.DemandNode('city', hs.MunicipalDemand(population=1000, per_capita_demand=0.2))
    >>> 
    >>> # Create link with control
    >>> pipeline = hs.Link('pipeline', reservoir, city, 
    ...                    physical_capacity=100, cost=0.01)
    >>> 
    >>> # Add fractional control (reduce capacity to 80%)
    >>> pipeline.control = hs.FractionalControl(fraction=0.8)
    >>> 
    >>> # Add absolute control (limit to 60 units regardless of capacity)
    >>> pipeline.control = hs.AbsoluteControl(limit=60.0)
    >>> 
    >>> # Add switch control (on/off based on storage level)
    >>> pipeline.control = hs.SwitchControl(
    ...     reference_node=reservoir,
    ...     threshold=200.0,
    ...     above_threshold=True  # on when storage > 200
    ... )

Available Controls:
    - FractionalControl: Scale capacity by a fraction (0.0 to 1.0)
    - AbsoluteControl: Set absolute capacity limit
    - SwitchControl: Binary on/off based on node state
    
Controls are evaluated each timestep and can represent operational
policies, physical constraints, or automated control systems.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hydrosim.nodes import Node


class Control(ABC):
    """Abstract base for link control logic."""
    
    @abstractmethod
    def calculate_limit(self, base_capacity: float, source: 'Node', 
                       target: 'Node') -> float:
        """
        Calculate controlled flow limit.
        
        Args:
            base_capacity: Base capacity before control is applied
            source: Source node
            target: Target node
            
        Returns:
            Controlled flow limit
        """
        pass


class FractionalControl(Control):
    """Throttle capacity by a fraction (0.0 to 1.0)."""
    
    def __init__(self, fraction: float):
        """
        Initialize fractional control.
        
        Args:
            fraction: Throttle fraction between 0.0 and 1.0
            
        Raises:
            ValueError: If fraction is not in [0.0, 1.0]
        """
        if not 0.0 <= fraction <= 1.0:
            raise ValueError(f"Fraction must be between 0.0 and 1.0, got {fraction}")
        self.fraction = fraction
    
    def calculate_limit(self, base_capacity: float, source: 'Node', 
                       target: 'Node') -> float:
        """
        Calculate controlled flow limit by applying fraction.
        
        Args:
            base_capacity: Base capacity before control is applied
            source: Source node (unused)
            target: Target node (unused)
            
        Returns:
            Base capacity multiplied by fraction
        """
        return base_capacity * self.fraction


class AbsoluteControl(Control):
    """Set a hard flow cap in absolute units."""
    
    def __init__(self, max_flow: float):
        """
        Initialize absolute control.
        
        Args:
            max_flow: Maximum flow in absolute units
            
        Raises:
            ValueError: If max_flow is negative
        """
        if max_flow < 0.0:
            raise ValueError(f"Max flow must be non-negative, got {max_flow}")
        self.max_flow = max_flow
    
    def calculate_limit(self, base_capacity: float, source: 'Node', 
                       target: 'Node') -> float:
        """
        Calculate controlled flow limit by applying absolute cap.
        
        Args:
            base_capacity: Base capacity before control is applied
            source: Source node (unused)
            target: Target node (unused)
            
        Returns:
            Minimum of base capacity and max_flow
        """
        return min(base_capacity, self.max_flow)


class SwitchControl(Control):
    """Binary on/off control."""
    
    def __init__(self, is_on: bool):
        """
        Initialize switch control.
        
        Args:
            is_on: Whether the switch is on (True) or off (False)
        """
        self.is_on = is_on
    
    def calculate_limit(self, base_capacity: float, source: 'Node', 
                       target: 'Node') -> float:
        """
        Calculate controlled flow limit based on switch state.
        
        Args:
            base_capacity: Base capacity before control is applied
            source: Source node (unused)
            target: Target node (unused)
            
        Returns:
            Base capacity if switch is on, 0.0 if off
        """
        return base_capacity if self.is_on else 0.0
