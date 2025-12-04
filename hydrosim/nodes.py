"""
Node abstractions and implementations for the HydroSim framework.

Nodes represent locations in the water network that handle vertical physics
(interactions with environment).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING, Optional
import logging

if TYPE_CHECKING:
    from hydrosim.links import Link
    from hydrosim.climate import ClimateState
    from hydrosim.config import ElevationAreaVolume
    from hydrosim.strategies import GeneratorStrategy, DemandModel

from hydrosim.exceptions import NegativeStorageError, ConfigurationError

# Configure logger
logger = logging.getLogger(__name__)


class Node(ABC):
    """Base class for all network nodes."""
    
    def __init__(self, node_id: str, node_type: str):
        """
        Initialize a node.
        
        Args:
            node_id: Unique identifier for the node
            node_type: Type of node (storage, junction, source, demand)
        """
        self.node_id = node_id
        self.node_type = node_type
        self.inflows: List['Link'] = []
        self.outflows: List['Link'] = []
    
    @abstractmethod
    def step(self, climate: 'ClimateState') -> None:
        """
        Execute node-specific logic for the current timestep.
        
        Args:
            climate: Current climate state
        """
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, float]:
        """
        Return current node state for reporting.
        
        Returns:
            Dictionary mapping state variable names to values
        """
        pass


class StorageNode(Node):
    """Reservoir or tank with mass storage."""
    
    def __init__(self, node_id: str, initial_storage: float, 
                 eav_table: 'ElevationAreaVolume',
                 max_storage: float,
                 min_storage: float = 0.0,
                 allow_negative: bool = False,
                 low_storage_threshold: float = 0.1):
        """
        Initialize a storage node.
        
        Args:
            node_id: Unique identifier for the node
            initial_storage: Initial storage volume
            eav_table: Elevation-area-volume table for interpolation
            max_storage: Maximum storage capacity
            min_storage: Minimum storage level (dead pool), defaults to 0.0
            allow_negative: If False, raise error on negative storage; if True, constrain to zero
            low_storage_threshold: Fraction of minimum EAV volume to trigger low storage warning
            
        Raises:
            ConfigurationError: If storage capacity constraints are violated
        """
        super().__init__(node_id, "storage")
        
        # Validate capacity constraints
        if min_storage > max_storage:
            raise ConfigurationError(
                f"Storage node '{node_id}': min_storage ({min_storage:.2f}) "
                f"cannot exceed max_storage ({max_storage:.2f})"
            )
        
        if initial_storage < min_storage:
            raise ConfigurationError(
                f"Storage node '{node_id}': initial_storage ({initial_storage:.2f}) "
                f"cannot be less than min_storage ({min_storage:.2f})"
            )
        
        if initial_storage > max_storage:
            raise ConfigurationError(
                f"Storage node '{node_id}': initial_storage ({initial_storage:.2f}) "
                f"cannot exceed max_storage ({max_storage:.2f})"
            )
        
        self.initial_storage = initial_storage
        self.storage = initial_storage
        self.eav_table = eav_table
        self.max_storage = max_storage
        self.min_storage = min_storage
        self.evap_loss = 0.0
        self.allow_negative = allow_negative
        self.low_storage_threshold = low_storage_threshold
        
        # Calculate low storage warning level
        self.low_storage_level = eav_table.min_volume * low_storage_threshold
        
        # Flag to track if storage was updated by virtual network architecture
        self._updated_by_carryover = False
    
    def get_available_mass(self) -> float:
        """
        Calculate available mass for solver allocation.
        
        This represents water already in the reservoir that can be
        allocated either to downstream flows or to carryover storage.
        
        Returns:
            Available mass (storage - evaporation), clamped to non-negative
        """
        # Check for high evaporation relative to storage (> 50%)
        if self.storage > 0 and self.evap_loss > 0.5 * self.storage:
            logger.warning(
                f"Storage node '{self.node_id}': High evaporation relative to storage. "
                f"Evaporation: {self.evap_loss:.2f}, Storage: {self.storage:.2f} "
                f"({(self.evap_loss / self.storage * 100):.1f}% of storage)"
            )
        
        available = self.storage - self.evap_loss
        
        # Critical edge case: evaporation exceeds storage
        if available < 0:
            # Clamp to zero and reduce evaporation to match storage
            logger.warning(
                f"Storage node '{self.node_id}': Evaporation ({self.evap_loss:.2f}) "
                f"exceeds storage ({self.storage:.2f}). Clamping to zero."
            )
            self.evap_loss = self.storage
            available = 0.0
        
        return available
    
    def get_elevation(self) -> float:
        """
        Interpolate elevation from current storage.
        
        Returns:
            Current elevation
        """
        return self.eav_table.storage_to_elevation(self.storage)
    
    def get_surface_area(self) -> float:
        """
        Interpolate surface area from current storage.
        
        Returns:
            Current surface area
        """
        return self.eav_table.storage_to_area(self.storage)
    
    def step(self, climate: 'ClimateState') -> None:
        """
        Calculate evaporation loss.
        
        Args:
            climate: Current climate state
        """
        # Reset carryover flag at the beginning of each timestep
        self._updated_by_carryover = False
        
        area = self.get_surface_area()
        # Convert ET0 from mm/day to m/day, then multiply by area in m² to get m³/day
        self.evap_loss = area * climate.et0 / 1000.0
    
    def update_storage(self, inflow: float, outflow: float) -> None:
        """
        Update storage based on mass balance.
        
        Args:
            inflow: Total inflow to the node
            outflow: Total outflow from the node
            
        Raises:
            NegativeStorageError: If storage would become negative and allow_negative=False
        """
        new_storage = self.storage + inflow - outflow - self.evap_loss
        
        # Check for negative storage
        if new_storage < 0:
            if not self.allow_negative:
                raise NegativeStorageError(
                    self.node_id, 
                    self.storage, 
                    outflow, 
                    self.evap_loss
                )
            else:
                # Constrain to zero and log warning
                logger.warning(
                    f"Storage node '{self.node_id}' would have negative storage "
                    f"({new_storage:.2f}). Constraining to zero. "
                    f"Current: {self.storage:.2f}, Inflow: {inflow:.2f}, "
                    f"Outflow: {outflow:.2f}, Evaporation: {self.evap_loss:.2f}"
                )
                new_storage = 0.0
        
        # Check for low storage
        elif new_storage < self.low_storage_level:
            logger.warning(
                f"Storage node '{self.node_id}' has low storage: {new_storage:.2f} "
                f"(threshold: {self.low_storage_level:.2f}). "
                f"Current: {self.storage:.2f}, Inflow: {inflow:.2f}, "
                f"Outflow: {outflow:.2f}, Evaporation: {self.evap_loss:.2f}"
            )
        
        self.storage = new_storage
    
    def update_storage_from_carryover(self, carryover_flow: float) -> None:
        """
        Update storage based on carryover link flow.
        
        This method is used by the LinearProgrammingSolver when using the
        virtual link architecture for storage drawdown. The carryover flow
        represents the optimized final storage level for the current timestep.
        
        This method sets a flag (_updated_by_carryover) to indicate that
        storage has been updated by the virtual network architecture, so
        the simulation should not call update_storage() again.
        
        Args:
            carryover_flow: Flow on the carryover link (equals final storage)
        """
        # Check if storage is approaching dead pool (within 10%)
        if self.min_storage > 0:
            dead_pool_threshold = self.min_storage * 1.1  # 10% above dead pool
            if carryover_flow <= dead_pool_threshold:
                logger.warning(
                    f"Storage node '{self.node_id}': Storage approaching dead pool. "
                    f"Current storage: {carryover_flow:.2f}, Dead pool: {self.min_storage:.2f} "
                    f"(within {((dead_pool_threshold - self.min_storage) / self.min_storage * 100):.0f}% threshold)"
                )
        
        self.storage = carryover_flow
        self._updated_by_carryover = True
    
    def get_state(self) -> Dict[str, float]:
        """
        Return current node state for reporting.
        
        Returns:
            Dictionary with storage, elevation, surface_area, and evap_loss
        """
        return {
            "storage": self.storage,
            "elevation": self.get_elevation(),
            "surface_area": self.get_surface_area(),
            "evap_loss": self.evap_loss
        }


class JunctionNode(Node):
    """Stateless connection point with no storage."""
    
    def __init__(self, node_id: str):
        """
        Initialize a junction node.
        
        Args:
            node_id: Unique identifier for the node
        """
        super().__init__(node_id, "junction")
    
    def step(self, climate: 'ClimateState') -> None:
        """
        No state update needed for junctions.
        
        Args:
            climate: Current climate state (unused)
        """
        pass
    
    def get_state(self) -> Dict[str, float]:
        """
        Junctions have no internal state.
        
        Returns:
            Empty dictionary
        """
        return {}


class SourceNode(Node):
    """Water source with pluggable generation strategy."""
    
    def __init__(self, node_id: str, generator: 'GeneratorStrategy'):
        """
        Initialize a source node.
        
        Args:
            node_id: Unique identifier for the node
            generator: Strategy for generating inflow
        """
        super().__init__(node_id, "source")
        self.generator = generator
        self.inflow = 0.0
    
    def step(self, climate: 'ClimateState') -> None:
        """
        Generate inflow using strategy.
        
        Args:
            climate: Current climate state
        """
        self.inflow = self.generator.generate(climate)
    
    def get_state(self) -> Dict[str, float]:
        """
        Return current node state for reporting.
        
        Returns:
            Dictionary with inflow
        """
        return {"inflow": self.inflow}


class DemandNode(Node):
    """Water demand with pluggable demand model."""
    
    def __init__(self, node_id: str, demand_model: 'DemandModel'):
        """
        Initialize a demand node.
        
        Args:
            node_id: Unique identifier for the node
            demand_model: Strategy for calculating demand
        """
        super().__init__(node_id, "demand")
        self.demand_model = demand_model
        self.request = 0.0
        self.delivered = 0.0
        self.deficit = 0.0
    
    def step(self, climate: 'ClimateState') -> None:
        """
        Calculate demand request.
        
        Args:
            climate: Current climate state
        """
        self.request = self.demand_model.calculate(climate)
    
    def update_delivery(self, delivered: float) -> None:
        """
        Update delivered amount and calculate deficit.
        
        Args:
            delivered: Amount of water delivered
        """
        self.delivered = delivered
        self.deficit = max(0.0, self.request - delivered)
    
    def get_state(self) -> Dict[str, float]:
        """
        Return current node state for reporting.
        
        Returns:
            Dictionary with request, delivered, and deficit
        """
        return {
            "request": self.request,
            "delivered": self.delivered,
            "deficit": self.deficit
        }


# Virtual Network Components for Storage Drawdown

@dataclass
class VirtualSink:
    """
    Represents the future state of a storage node.
    
    This is a temporary node used only during solver construction for the
    virtual link architecture. It receives flow from the carryover link,
    representing water that stays in the reservoir from timestep t to t+1.
    
    Attributes:
        node_id: Unique identifier (format: "{storage_node_id}_future")
        demand: Water demand equal to available mass from storage node
        node_type: Always "virtual_sink"
        inflows: List of incoming links (includes carryover link)
        outflows: List of outgoing links (typically empty)
    """
    node_id: str
    demand: float
    node_type: str = field(default="virtual_sink", init=False)
    inflows: List = field(default_factory=list)
    outflows: List = field(default_factory=list)


@dataclass
class CarryoverLink:
    """
    Represents water staying in storage from timestep t to t+1.
    
    This is a virtual link used only during solver construction for the
    virtual link architecture. The flow on this link equals the final
    storage level after optimization.
    
    Attributes:
        link_id: Unique identifier (format: "{storage_node_id}_carryover")
        source: Source storage node
        target: Target virtual sink node
        min_flow: Minimum flow (dead pool level)
        max_flow: Maximum flow (maximum storage capacity)
        cost: Cost per unit flow (typically COST_STORAGE = -1)
    """
    link_id: str
    source: 'StorageNode'
    target: VirtualSink
    min_flow: float
    max_flow: float
    cost: float
