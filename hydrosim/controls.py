"""
Control system abstractions for link flow management.

Controls allow modeling of operational rules and automated control logic.
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
