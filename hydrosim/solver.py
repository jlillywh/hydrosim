"""
Network solver abstractions for optimization.

The solver performs minimum cost network flow optimization to allocate
water across the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from hydrosim.nodes import Node
    from hydrosim.links import Link

from hydrosim.exceptions import InfeasibleNetworkError

# Configure logger
logger = logging.getLogger(__name__)


# ============================================================================
# Cost Constants for Network Flow Optimization
# ============================================================================
# These constants define the cost hierarchy used by the solver to prioritize
# water allocation decisions. The solver minimizes total cost, so more negative
# values represent higher priority allocations.
#
# Cost Hierarchy (highest to lowest priority):
#   1. COST_DEMAND (-1000): Meeting water demands has highest priority
#   2. COST_STORAGE (-1): Storing water for future use has medium priority
#   3. COST_SPILL (0): Spilling excess water has lowest priority (no reward)
#
# This hierarchy ensures that:
#   - Demands are met before water is stored or spilled
#   - Water is stored before being spilled when demands are satisfied
#   - The system operates efficiently by prioritizing beneficial uses
#
# Usage:
#   - Demand links: Use COST_DEMAND to ensure demands are met first
#   - Carryover links: Use COST_STORAGE for reservoir storage decisions
#   - Spillway links: Use COST_SPILL for excess water disposal
#
# Modification:
#   - To adjust priorities, modify these constants in a single location
#   - Maintain the hierarchy: COST_DEMAND < COST_STORAGE < COST_SPILL
# ============================================================================

COST_DEMAND = -1000.0   # High reward: meet demands first
COST_STORAGE = -1.0     # Low reward: store water if demand is met
COST_SPILL = 0.0        # No reward: spill only if necessary


def validate_cost_hierarchy() -> None:
    """
    Validate that cost constants maintain the correct hierarchy.
    
    The cost hierarchy must satisfy: COST_DEMAND < COST_STORAGE < COST_SPILL
    This ensures proper prioritization of water allocation decisions.
    
    Raises:
        ConfigurationError: If cost hierarchy is violated
    """
    from hydrosim.exceptions import ConfigurationError
    
    if not (COST_DEMAND < COST_STORAGE < COST_SPILL):
        raise ConfigurationError(
            f"Cost hierarchy violation: COST_DEMAND ({COST_DEMAND}) must be less than "
            f"COST_STORAGE ({COST_STORAGE}) which must be less than COST_SPILL ({COST_SPILL}). "
            f"Current hierarchy is invalid. Please ensure COST_DEMAND < COST_STORAGE < COST_SPILL."
        )


class NetworkSolver(ABC):
    """Abstract interface for network flow optimization."""
    
    @abstractmethod
    def solve(self, nodes: List['Node'], links: List['Link'], 
              constraints: Dict[str, Tuple[float, float, float]]) -> Dict[str, float]:
        """
        Solve minimum cost network flow problem.
        
        Args:
            nodes: List of all nodes in the network
            links: List of all links in the network
            constraints: Dict mapping link_id to (q_min, q_max, cost)
        
        Returns:
            Dict mapping link_id to allocated flow
        """
        pass


class LookaheadSolver(NetworkSolver):
    """
    Look-ahead network flow solver using time-expanded graphs.
    
    This solver implements multi-timestep optimization by creating a time-expanded
    graph that represents multiple timesteps simultaneously. It uses a rolling
    horizon approach where decisions for the current timestep are applied, then
    the horizon advances by one timestep.
    
    Key features:
    - Configurable look-ahead horizon (1 to N days)
    - Time-expanded graph with carryover links between timesteps
    - Perfect foresight assumption for future inflows/demands
    - Rolling horizon optimization
    - Hedging capability (saving water for future high-priority needs)
    """
    
    def __init__(self, lookahead_days: int = 1, carryover_cost: float = -1.0):
        """
        Initialize look-ahead solver.
        
        Args:
            lookahead_days: Number of days to look ahead (1 = myopic behavior)
            carryover_cost: Cost for storing water between timesteps (hedging penalty)
        """
        validate_cost_hierarchy()
        self.lookahead_days = lookahead_days
        self.carryover_cost = carryover_cost
        self.base_solver = LinearProgrammingSolver()  # Use LP solver for expanded graph
        
        # Cache for future data (perfect foresight)
        self.future_inflows = {}  # {node_id: [inflow_t0, inflow_t1, ...]}
        self.future_demands = {}  # {node_id: [demand_t0, demand_t1, ...]}
        self.future_climate = []  # [climate_t0, climate_t1, ...]
    
    def set_future_data(self, future_inflows: Dict[str, List[float]], 
                       future_demands: Dict[str, List[float]],
                       future_climate: List[any] = None):
        """
        Set future data for perfect foresight optimization.
        
        Args:
            future_inflows: Dict mapping source node_id to list of future inflows
            future_demands: Dict mapping demand node_id to list of future demands  
            future_climate: List of future climate states (optional)
        """
        self.future_inflows = future_inflows
        self.future_demands = future_demands
        self.future_climate = future_climate or []
    
    def solve(self, nodes: List['Node'], links: List['Link'], 
              constraints: Dict[str, Tuple[float, float, float]]) -> Dict[str, float]:
        """
        Solve using time-expanded graph for look-ahead optimization.
        
        Args:
            nodes: List of all nodes in the current network
            links: List of all links in the current network
            constraints: Dict mapping link_id to (q_min, q_max, cost)
        
        Returns:
            Dict mapping link_id to allocated flow (only for current timestep)
        """
        if self.lookahead_days == 1:
            # Fallback to myopic behavior for single timestep
            return self.base_solver.solve(nodes, links, constraints)
        
        # Build time-expanded graph
        expanded_nodes, expanded_links, expanded_constraints = self._build_time_expanded_graph(
            nodes, links, constraints
        )
        
        # Solve the expanded problem
        expanded_flows = self.base_solver.solve(expanded_nodes, expanded_links, expanded_constraints)
        
        # Extract flows for current timestep (t=0)
        current_flows = {}
        for link_id, flow in expanded_flows.items():
            if link_id.endswith('_t0'):  # Current timestep links
                original_link_id = link_id[:-3]  # Remove '_t0' suffix
                current_flows[original_link_id] = flow
        
        return current_flows
    
    def _build_time_expanded_graph(self, nodes: List['Node'], links: List['Link'],
                                  constraints: Dict[str, Tuple[float, float, float]]) \
                                  -> Tuple[List['Node'], List['Link'], Dict[str, Tuple[float, float, float]]]:
        """
        Build time-expanded graph for multi-timestep optimization.
        
        Creates a "super-graph" with nodes for each timestep and carryover links
        connecting storage nodes across timesteps.
        
        Args:
            nodes: Original network nodes
            links: Original network links
            constraints: Original link constraints
            
        Returns:
            Tuple of (expanded_nodes, expanded_links, expanded_constraints)
        """
        from hydrosim.nodes import StorageNode, SourceNode, DemandNode, JunctionNode
        from hydrosim.links import Link
        
        expanded_nodes = []
        expanded_links = []
        expanded_constraints = {}
        
        # Create nodes for each timestep
        timestep_nodes = {}  # {timestep: {node_id: node}}
        
        for t in range(self.lookahead_days):
            timestep_nodes[t] = {}
            
            for node in nodes:
                # Create time-indexed node
                time_node_id = f"{node.node_id}_t{t}"
                
                if isinstance(node, StorageNode):
                    # Storage nodes: adjust initial storage for future timesteps
                    if t == 0:
                        initial_storage = node.storage  # Current storage
                    else:
                        # For future timesteps, use current storage as initial
                        # (will be updated by carryover links)
                        initial_storage = node.storage
                    
                    time_node = StorageNode(
                        time_node_id,
                        initial_storage,
                        node.eav_table,
                        max_storage=node.max_storage,
                        min_storage=node.min_storage
                    )
                
                elif isinstance(node, SourceNode):
                    # Source nodes: use future inflow data if available
                    if node.node_id in self.future_inflows and t < len(self.future_inflows[node.node_id]):
                        future_inflow = self.future_inflows[node.node_id][t]
                    else:
                        future_inflow = node.inflow  # Fallback to current inflow
                    
                    # Create a simple source with fixed inflow
                    time_node = SourceNode(time_node_id, None)
                    time_node.inflow = future_inflow
                
                elif isinstance(node, DemandNode):
                    # Demand nodes: use future demand data if available
                    if node.node_id in self.future_demands and t < len(self.future_demands[node.node_id]):
                        future_demand = self.future_demands[node.node_id][t]
                    else:
                        future_demand = node.request  # Fallback to current demand
                    
                    time_node = DemandNode(time_node_id, node.demand_model)
                    time_node.request = future_demand
                
                else:  # JunctionNode
                    time_node = JunctionNode(time_node_id)
                
                # Initialize connection lists
                time_node.inflows = []
                time_node.outflows = []
                
                timestep_nodes[t][node.node_id] = time_node
                expanded_nodes.append(time_node)
        
        # Create links for each timestep
        for t in range(self.lookahead_days):
            for link in links:
                # Create time-indexed link
                time_link_id = f"{link.link_id}_t{t}"
                source_node = timestep_nodes[t][link.source.node_id]
                target_node = timestep_nodes[t][link.target.node_id]
                
                time_link = Link(
                    time_link_id,
                    source_node,
                    target_node,
                    link.physical_capacity,
                    link.cost
                )
                
                # Copy control and hydraulic models
                time_link.control = link.control
                time_link.hydraulic_model = link.hydraulic_model
                
                expanded_links.append(time_link)
                
                # Add to constraints
                if link.link_id in constraints:
                    expanded_constraints[time_link_id] = constraints[link.link_id]
                else:
                    # Default constraints
                    expanded_constraints[time_link_id] = (0.0, link.physical_capacity, link.cost)
        
        # Create carryover links between timesteps for storage nodes
        for t in range(self.lookahead_days - 1):
            for node in nodes:
                if isinstance(node, StorageNode):
                    # Create carryover link from t to t+1
                    carryover_link_id = f"{node.node_id}_carryover_t{t}_to_t{t+1}"
                    source_node = timestep_nodes[t][node.node_id]
                    target_node = timestep_nodes[t+1][node.node_id]
                    
                    carryover_link = Link(
                        carryover_link_id,
                        source_node,
                        target_node,
                        node.max_storage,  # Maximum carryover is storage capacity
                        self.carryover_cost  # Hedging penalty
                    )
                    
                    expanded_links.append(carryover_link)
                    
                    # Add to constraints
                    expanded_constraints[carryover_link_id] = (
                        node.min_storage,  # Minimum carryover
                        node.max_storage,  # Maximum carryover
                        self.carryover_cost
                    )
        
        return expanded_nodes, expanded_links, expanded_constraints


class LinearProgrammingSolver(NetworkSolver):
    """
    Network flow solver using linear programming.
    
    This solver formulates the minimum cost network flow problem as a linear
    program and solves it using SciPy's linprog optimizer.
    """
    
    def __init__(self):
        """
        Initialize the linear programming solver.
        
        Validates that cost constants maintain the correct hierarchy.
        
        Raises:
            ConfigurationError: If cost hierarchy is violated
        """
        validate_cost_hierarchy()
    
    def _create_virtual_network(self, nodes: List['Node'], links: List['Link'],
                                constraints: Dict[str, Tuple[float, float, float]]) \
                                -> Tuple[List['Node'], List['Link'], Dict[str, Tuple[float, float, float]]]:
        """
        Create virtual network using Universal Sink pattern for storage drawdown.
        
        This method implements the Universal Sink architecture:
        1. Calculate total system supply (all source inflows + all storage available mass)
        2. Create a single Universal Sink that demands this total supply
        3. Create carryover links from each storage node to the Universal Sink
        4. Redirect all demand node inflows to go through the Universal Sink
        
        This ensures strict mass conservation: sum(b_eq) = 0 always.
        
        IMPORTANT: This method creates temporary virtual components for the solver.
        The original nodes' inflows/outflows lists are NOT modified to avoid
        breaking the simulation's state update logic.
        
        Args:
            nodes: List of all nodes in the network
            links: List of all links in the network
            constraints: Dict mapping link_id to (q_min, q_max, cost)
        
        Returns:
            Tuple of (augmented_nodes, augmented_links, augmented_constraints)
        """
        from hydrosim.nodes import VirtualSink, CarryoverLink
        
        # Start with copies of the original network components
        augmented_nodes = list(nodes)
        augmented_links = list(links)
        augmented_constraints = dict(constraints)
        
        # Calculate total system supply
        total_supply = 0.0
        
        # Add all source inflows
        for node in nodes:
            if node.node_type == "source":
                total_supply += node.inflow
        
        # Add all storage available mass
        storage_nodes = []
        for node in nodes:
            if node.node_type == "storage":
                total_supply += node.get_available_mass()
                storage_nodes.append(node)
        
        # Only create virtual network if there are storage nodes
        if not storage_nodes:
            return augmented_nodes, augmented_links, augmented_constraints
        
        # Create the Universal Sink
        universal_sink = VirtualSink(
            node_id="_universal_sink",
            demand=total_supply
        )
        augmented_nodes.append(universal_sink)
        universal_sink.inflows = []
        universal_sink.outflows = []
        
        # Create carryover links from each storage node to Universal Sink
        for node in storage_nodes:
            carryover_link = CarryoverLink(
                link_id=f"{node.node_id}_carryover",
                source=node,
                target=universal_sink,
                min_flow=node.min_storage,
                max_flow=node.max_storage,
                cost=COST_STORAGE
            )
            augmented_links.append(carryover_link)
            
            # Add carryover link to augmented_constraints dict
            augmented_constraints[carryover_link.link_id] = (
                carryover_link.min_flow,
                carryover_link.max_flow,
                carryover_link.cost
            )
            
            # Track connection for LP formulation
            universal_sink.inflows.append(carryover_link)
            
            # Create spillway link from storage node to Universal Sink
            # This handles excess water that cannot be stored (when storage is at capacity)
            # Spillway has unlimited capacity and COST_SPILL (0) - lowest priority
            spillway_link = CarryoverLink(
                link_id=f"{node.node_id}_spillway",
                source=node,
                target=universal_sink,
                min_flow=0.0,
                max_flow=float('inf'),  # Unlimited capacity for spillage
                cost=COST_SPILL
            )
            augmented_links.append(spillway_link)
            
            # Add spillway link to augmented_constraints dict
            augmented_constraints[spillway_link.link_id] = (
                spillway_link.min_flow,
                spillway_link.max_flow,
                spillway_link.cost
            )
            
            # Track connection for LP formulation
            universal_sink.inflows.append(spillway_link)
        
        # Redirect all demand node connections to go through Universal Sink
        # For each demand node, create a virtual link from demand to Universal Sink
        # The demand node will act as a pass-through (b_eq = 0 in virtual mode)
        # and the actual demand satisfaction is represented by flow to the Universal Sink
        for node in nodes:
            if node.node_type == "demand":
                demand_to_sink_link = CarryoverLink(
                    link_id=f"{node.node_id}_to_sink",
                    source=node,
                    target=universal_sink,
                    min_flow=0.0,  # Allow unmet demand (deficit)
                    max_flow=node.request,  # Deliver at most the request
                    cost=0.0  # No cost for this virtual link
                )
                augmented_links.append(demand_to_sink_link)
                
                # Add to constraints
                augmented_constraints[demand_to_sink_link.link_id] = (
                    demand_to_sink_link.min_flow,
                    demand_to_sink_link.max_flow,
                    demand_to_sink_link.cost
                )
                
                # Track connection
                universal_sink.inflows.append(demand_to_sink_link)
        
        return augmented_nodes, augmented_links, augmented_constraints
    
    def _solve_lp(self, nodes: List['Node'], links: List['Link'], 
                  constraints: Dict[str, Tuple[float, float, float]]) -> Dict[str, float]:
        """
        Solve minimum cost network flow problem using linear programming.
        
        This method handles both physical and virtual network components.
        Virtual components (VirtualSink nodes and CarryoverLink links) are
        treated identically to physical components in the LP formulation.
        
        The problem is formulated as:
            minimize: sum(cost_i * flow_i) for all links i
            subject to:
                - Mass balance at each node: inflow - outflow = supply/demand
                - Flow bounds: q_min_i <= flow_i <= q_max_i for all links i
        
        Args:
            nodes: List of all nodes (including virtual sinks)
            links: List of all links (including carryover links)
            constraints: Dict mapping link_id to (q_min, q_max, cost)
        
        Returns:
            Dict mapping link_id to allocated flow (includes carryover links)
        
        Raises:
            RuntimeError: If the optimization problem is infeasible or unbounded
        """
        # Lazy imports to avoid compatibility issues
        import numpy as np
        from scipy.optimize import linprog
        
        if not links:
            return {}
        
        # Create index mappings - includes virtual sinks and carryover links
        link_indices = {link.link_id: i for i, link in enumerate(links)}
        node_indices = {node.node_id: i for i, node in enumerate(nodes)}
        n_links = len(links)
        n_nodes = len(nodes)
        
        # Set up objective function (minimize cost)
        # c = [cost_1, cost_2, ..., cost_n]
        c = np.zeros(n_links)
        for link in links:
            q_min, q_max, cost = constraints[link.link_id]
            c[link_indices[link.link_id]] = cost
        
        # Set up flow bounds
        # bounds = [(q_min_1, q_max_1), (q_min_2, q_max_2), ...]
        bounds = []
        for link in links:
            q_min, q_max, cost = constraints[link.link_id]
            bounds.append((q_min, q_max))
        
        # Set up mass balance constraints for all nodes
        # Standard min-cost flow: inflow - outflow = b
        A_eq = np.zeros((n_nodes, n_links))
        b_eq = np.zeros(n_nodes)
        
        # Build constraint matrix by iterating through links
        # This approach works for both physical links (which are in node.inflows/outflows)
        # and virtual links (which may not be in those lists)
        for link in links:
            link_idx = link_indices[link.link_id]
            
            # Get source and target node indices
            # For physical links, use link.source and link.target
            # For virtual links (CarryoverLink), these attributes exist
            source_node_id = link.source.node_id
            target_node_id = link.target.node_id
            
            source_idx = node_indices[source_node_id]
            target_idx = node_indices[target_node_id]
            
            # Flow leaves source node (negative contribution)
            A_eq[source_idx, link_idx] = -1.0
            
            # Flow enters target node (positive contribution)
            # With the Universal Sink pattern, all links (including carryover and
            # demand-to-sink links) properly connect to nodes, ensuring strict
            # mass conservation: sum(b_eq) = 0
            A_eq[target_idx, link_idx] = 1.0
        
        # Set boundary conditions (supply/demand) for each node
        for node in nodes:
            node_idx = node_indices[node.node_id]
            
            # Set supply/demand value based on node type
            if node.node_type == "source":
                # Source: inflow - outflow = b
                # For source with no inflows: -outflow = b
                # We want outflow = generation, so b = -generation
                b_eq[node_idx] = -node.inflow
            elif node.node_type == "demand":
                # Check if we're in virtual network mode (Universal Sink exists)
                has_universal_sink = any(
                    n.node_type == "virtual_sink" and n.node_id == "_universal_sink"
                    for n in nodes
                )
                
                if has_universal_sink:
                    # Virtual network mode: demand node acts as pass-through junction
                    # The actual demand is enforced by the demand-to-sink link bounds
                    b_eq[node_idx] = 0.0
                else:
                    # Standard mode: demand node demands water
                    # Demand: inflow - outflow = b
                    # For demand with no outflows: inflow = b
                    # We want inflow = request, so b = request
                    b_eq[node_idx] = node.request
            elif node.node_type == "storage":
                # CRITICAL: When using virtual network architecture, storage provides
                # available mass as source: b_eq = -available_mass (negative for source)
                # This allows the solver to allocate water from storage.
                # 
                # We detect virtual network usage by checking if there are any
                # carryover links in the augmented link list
                has_carryover = any(
                    hasattr(link, 'link_id') and link.link_id == f"{node.node_id}_carryover"
                    for link in links
                )
                
                if has_carryover:
                    # Virtual network mode: storage provides available mass as source
                    b_eq[node_idx] = -node.get_available_mass()
                else:
                    # Legacy mode: storage acts as pass-through buffer
                    b_eq[node_idx] = -node.evap_loss
            elif node.node_type == "virtual_sink":
                # CRITICAL: Universal Sink demands total system supply
                # This ensures strict mass conservation: sum(b_eq) = 0
                # All water entering the system (sources + storage) must exit through
                # the Universal Sink (via carryover links and demand-to-sink links)
                b_eq[node_idx] = node.demand
            elif node.node_type == "junction":
                # Junction: inflow - outflow = 0
                b_eq[node_idx] = 0.0
        
        # Verify mass balance: sum(b_eq) should equal 0
        total_imbalance = np.sum(b_eq)
        if abs(total_imbalance) > 1e-6:
            logger.warning(
                f"Mass balance imbalance detected: sum(b_eq) = {total_imbalance:.6f}. "
                f"Expected 0.0 for balanced network. This may indicate a problem "
                f"with virtual link construction or node boundary conditions."
            )
        
        # Add slack variable if unbalanced
        if abs(total_imbalance) > 1e-6:
            slack_col = np.zeros((n_nodes, 1))
            
            if total_imbalance < 0:
                # More supply than demand - add slack sink
                # Find a source and add slack as outflow
                for node in nodes:
                    if node.node_type == "source":
                        node_idx = node_indices[node.node_id]
                        slack_col[node_idx, 0] = -1.0
                        break
            else:
                # More demand than supply - add slack source
                # Find a demand node and add slack as inflow
                for node in nodes:
                    if node.node_type == "demand":
                        node_idx = node_indices[node.node_id]
                        slack_col[node_idx, 0] = 1.0
                        break
            
            A_eq = np.hstack([A_eq, slack_col])
            bounds.append((0, None))
            # High cost for unmet demand, zero cost for unused supply
            slack_cost = 1e6 if total_imbalance > 0 else 0.0
            c = np.append(c, slack_cost)
        
        A_ub = None
        b_ub = None
        
        # Solve the linear program
        result = linprog(
            c=c,
            A_eq=A_eq,
            b_eq=b_eq,
            A_ub=A_ub,
            b_ub=b_ub,
            bounds=bounds,
            method='highs'
        )
        
        # Check if solution was found
        if not result.success:
            # Diagnose potential issues
            conflicting_constraints = self._diagnose_infeasibility(
                nodes, links, constraints, A_eq, b_eq, bounds
            )
            
            raise InfeasibleNetworkError(
                result.message,
                conflicting_constraints
            )
        
        # Extract flow allocations (includes carryover links)
        flow_allocations = {}
        for link in links:
            link_idx = link_indices[link.link_id]
            flow_allocations[link.link_id] = result.x[link_idx]
        
        return flow_allocations
    
    def _update_storage_from_carryover(self, nodes: List['Node'],
                                       flow_allocations: Dict[str, float]) -> None:
        """
        Update storage nodes based on carryover link flows.
        
        This method iterates through all nodes to find StorageNodes and updates
        their storage based on the optimized carryover flow. The carryover flow
        represents the final storage level for the current timestep.
        
        Args:
            nodes: Original node list (before virtual network augmentation)
            flow_allocations: All flow allocations including carryover links
        """
        # Iterate through all nodes to find StorageNodes
        for node in nodes:
            if node.node_type == "storage":
                # Get carryover link ID: f"{node.node_id}_carryover"
                carryover_link_id = f"{node.node_id}_carryover"
                
                # Extract carryover flow from flow_allocations dict
                if carryover_link_id in flow_allocations:
                    carryover_flow = flow_allocations[carryover_link_id]
                    
                    # Call node.update_storage_from_carryover(carryover_flow)
                    node.update_storage_from_carryover(carryover_flow)
    
    def solve(self, nodes: List['Node'], links: List['Link'], 
              constraints: Dict[str, Tuple[float, float, float]]) -> Dict[str, float]:
        """
        Solve minimum cost network flow problem using virtual network architecture.
        
        This method implements the virtual link pattern for storage drawdown:
        1. Creates virtual sinks and carryover links for each StorageNode
        2. Solves the augmented network using linear programming
        3. Extracts physical flows (excludes virtual carryover links)
        4. Updates storage nodes based on carryover flow allocations
        
        The virtual network architecture treats final storage as a decision
        variable, enabling active drawdown and refill operations.
        
        Args:
            nodes: List of all nodes in the network
            links: List of all links in the network
            constraints: Dict mapping link_id to (q_min, q_max, cost)
        
        Returns:
            Dict mapping link_id to allocated flow (physical links only)
        
        Raises:
            RuntimeError: If the optimization problem is infeasible or unbounded
        """
        # Call _create_virtual_network() to get augmented components
        augmented_nodes, augmented_links, augmented_constraints = \
            self._create_virtual_network(nodes, links, constraints)
        
        # Call _solve_lp() with augmented components
        flow_allocations = self._solve_lp(
            augmented_nodes, augmented_links, augmented_constraints
        )
        
        # Extract physical flows (exclude virtual links)
        # Virtual links include:
        # - Carryover links (ending with "_carryover")
        # - Demand-to-sink links (ending with "_to_sink")
        # - Spillway links (ending with "_spillway")
        physical_flows = {
            link_id: flow 
            for link_id, flow in flow_allocations.items()
            if not (link_id.endswith("_carryover") or link_id.endswith("_to_sink") or link_id.endswith("_spillway"))
        }
        
        # Call _update_storage_from_carryover() to update storage nodes
        self._update_storage_from_carryover(nodes, flow_allocations)
        
        # Return physical flows only
        return physical_flows
    
    def _diagnose_infeasibility(self, nodes: List['Node'], links: List['Link'],
                                constraints: Dict[str, Tuple[float, float, float]],
                                A_eq, b_eq, bounds) -> List[str]:
        """
        Diagnose potential causes of infeasibility.
        
        Args:
            nodes: List of all nodes
            links: List of all links
            constraints: Constraint dictionary
            A_eq: Equality constraint matrix
            b_eq: Equality constraint vector
            bounds: Variable bounds
            
        Returns:
            List of diagnostic messages about potential conflicts
        """
        import numpy as np
        
        diagnostics = []
        
        # Check for supply/demand imbalance
        total_supply = 0.0
        total_demand = 0.0
        
        for node in nodes:
            if node.node_type == "source":
                total_supply += node.inflow
            elif node.node_type == "demand":
                total_demand += node.request
        
        imbalance = total_demand - total_supply
        if imbalance > 1e-6:
            diagnostics.append(
                f"Demand exceeds supply: Total demand = {total_demand:.2f}, "
                f"Total supply = {total_supply:.2f}, Deficit = {imbalance:.2f}"
            )
        
        # Check for zero-capacity links
        zero_capacity_links = []
        for link in links:
            q_min, q_max, cost = constraints[link.link_id]
            if q_max < 1e-9:
                zero_capacity_links.append(
                    f"Link '{link.link_id}' ({link.source.node_id} -> {link.target.node_id}) "
                    f"has zero or near-zero capacity: {q_max:.6f}"
                )
        
        if zero_capacity_links:
            diagnostics.append("Links with zero capacity:")
            diagnostics.extend(zero_capacity_links)
        
        # Check for isolated demand nodes
        for node in nodes:
            if node.node_type == "demand" and node.request > 0:
                if len(node.inflows) == 0:
                    diagnostics.append(
                        f"Demand node '{node.node_id}' has no inflow links but requests "
                        f"{node.request:.2f} units"
                    )
                else:
                    # Check if inflow capacity is sufficient
                    max_inflow = sum(
                        constraints[link.link_id][1] for link in node.inflows
                    )
                    if max_inflow < node.request - 1e-6:
                        diagnostics.append(
                            f"Demand node '{node.node_id}' requests {node.request:.2f} "
                            f"but maximum possible inflow is {max_inflow:.2f}"
                        )
        
        # Check for isolated source nodes
        for node in nodes:
            if node.node_type == "source" and node.inflow > 0:
                if len(node.outflows) == 0:
                    diagnostics.append(
                        f"Source node '{node.node_id}' generates {node.inflow:.2f} "
                        f"but has no outflow links"
                    )
        
        # Check for conflicting bounds
        for link in links:
            q_min, q_max, cost = constraints[link.link_id]
            if q_min > q_max + 1e-6:
                diagnostics.append(
                    f"Link '{link.link_id}' has conflicting bounds: "
                    f"min = {q_min:.2f} > max = {q_max:.2f}"
                )
        
        return diagnostics
