"""
Link implementations for the HydroSim framework.

Links represent connections between nodes that handle horizontal physics
(transport constraints). Links define flow capacity, cost, and optional
control rules or hydraulic models.

Example:
    >>> import hydrosim as hs
    >>> 
    >>> # Create nodes
    >>> reservoir = hs.StorageNode('reservoir', capacity=1000)
    >>> city = hs.DemandNode('city', demand_strategy=hs.MunicipalDemand(50))
    >>> 
    >>> # Create link with capacity and cost
    >>> pipeline = hs.Link(
    ...     link_id='pipeline',
    ...     source=reservoir,
    ...     target=city,
    ...     physical_capacity=100.0,
    ...     cost=0.01
    ... )
    >>> 
    >>> # Add control rule (optional)
    >>> pipeline.control = hs.FractionalControl(
    ...     target_fraction=0.8,
    ...     reference_node=reservoir
    ... )

Links participate in the network optimization process where flows are
allocated to minimize cost while satisfying all constraints.
"""

from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hydrosim.nodes import Node
    from hydrosim.controls import Control
    from hydrosim.hydraulics import HydraulicModel


class Link:
    """Represents a connection between two nodes with constraints."""
    
    def __init__(self, link_id: str, source: 'Node', target: 'Node', 
                 physical_capacity: float, cost: float):
        """
        Initialize a link.
        
        Args:
            link_id: Unique identifier for the link
            source: Source node
            target: Target node
            physical_capacity: Maximum physical capacity
            cost: Cost per unit flow
        """
        self.link_id = link_id
        self.source = source
        self.target = target
        self.physical_capacity = physical_capacity
        self.cost = cost
        self.control: Optional['Control'] = None
        self.hydraulic_model: Optional['HydraulicModel'] = None
        self.flow: float = 0.0
    
    def calculate_constraints(self) -> Tuple[float, float, float]:
        """
        Apply constraint funnel to determine feasible flow bounds.
        
        Returns:
            Tuple of (q_min, q_max, cost)
        """
        q_max = self.physical_capacity
        
        # Apply hydraulic constraints
        if self.hydraulic_model:
            q_max = min(q_max, self.hydraulic_model.calculate_capacity(self.source))
        
        # Apply control constraints
        if self.control:
            q_max = min(q_max, self.control.calculate_limit(q_max, self.source, self.target))
        
        return (0.0, q_max, self.cost)
