"""
Simulation engine for orchestrating timestep execution.

The simulation engine coordinates the execution of all components in the
correct order to ensure proper physics and optimization.
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

from hydrosim.climate_engine import ClimateEngine
from hydrosim.config import NetworkGraph
from hydrosim.nodes import Node, StorageNode, DemandNode, SourceNode
from hydrosim.links import Link
from hydrosim.solver import NetworkSolver, LinearProgrammingSolver, LookaheadSolver
from hydrosim.exceptions import (
    NegativeStorageError, 
    InfeasibleNetworkError, 
    ClimateDataError,
    EAVInterpolationError
)

# Configure logger
logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Orchestrates timestep execution for water network simulation.
    
    The simulation engine enforces a strict execution order for each timestep:
    1. Environment step: Update climate drivers and calculate ET0
    2. Node step: Execute node-specific logic (generation, demand, evaporation)
    3. Link step: Update constraints based on current system state
    4. Solver step: Perform network optimization
    5. State update: Move mass and update storage based on allocated flows
    
    Attributes:
        network: Network graph containing nodes and links
        climate_engine: Climate engine for environmental drivers
        solver: Network flow solver
        current_timestep: Current timestep number (0-indexed)
    """
    
    def __init__(self,
                 network: NetworkGraph,
                 climate_engine: ClimateEngine,
                 solver: NetworkSolver = None):
        """
        Initialize simulation engine.
        
        Args:
            network: Network graph with nodes and links
            climate_engine: Climate engine for environmental drivers
            solver: Network flow solver for optimization (optional, auto-selected based on config)
        """
        self.network = network
        self.climate_engine = climate_engine
        
        # Auto-select solver based on optimization configuration
        if solver is None:
            solver = self._create_solver_from_config()
        
        self.solver = solver
        self.current_timestep = 0
        
        # Initialize future data cache for look-ahead optimization
        self._future_data_prepared = False
    
    def step(self) -> Dict[str, any]:
        """
        Execute one timestep of the simulation.
        
        This method enforces the strict execution order:
        1. Environment: Update climate and calculate ET0
        2. Nodes: Run generators, demands, and evaporation
        3. Links: Update constraints based on current state
        4. Solver: Optimize network flows
        5. State update: Move mass and update storage
        
        Returns:
            Dictionary containing timestep results including:
                - timestep: Current timestep number
                - date: Current date
                - climate: Climate state
                - node_states: State of all nodes
                - flows: Flow allocations for all links
                
        Raises:
            ClimateDataError: If climate data is not available for the current timestep
            InfeasibleNetworkError: If the network flow problem is infeasible
            NegativeStorageError: If storage would become negative (if allow_negative=False)
            EAVInterpolationError: If storage is out of EAV table bounds (if extrapolate=False)
        """
        try:
            # Step 1: Environment step - update climate drivers
            logger.debug(f"Timestep {self.current_timestep}: Updating climate drivers")
            climate_state = self.climate_engine.step()
            
            # Step 2: Node step - execute node-specific logic
            logger.debug(f"Timestep {self.current_timestep}: Executing node step")
            nodes = list(self.network.nodes.values())
            for node in nodes:
                node.step(climate_state)
            
            # Step 3: Link step - update constraints based on current state
            logger.debug(f"Timestep {self.current_timestep}: Updating link constraints")
            links = list(self.network.links.values())
            constraints = {}
            for link in links:
                constraints[link.link_id] = link.calculate_constraints()
            
            # Step 4: Solver step - perform network optimization
            logger.debug(f"Timestep {self.current_timestep}: Solving network flow")
            flow_allocations = self.solver.solve(nodes, links, constraints)
            
            # Step 5: State update - move mass and update storage
            logger.debug(f"Timestep {self.current_timestep}: Updating state")
            self._update_state(flow_allocations)
            
            # Collect results
            results = {
                'timestep': self.current_timestep,
                'date': climate_state.date,
                'climate': climate_state,
                'node_states': {node.node_id: node.get_state() for node in nodes},
                'flows': flow_allocations
            }
            
            # Increment timestep counter
            self.current_timestep += 1
            
            logger.info(
                f"Completed timestep {self.current_timestep - 1} "
                f"(date: {climate_state.date})"
            )
            
            return results
            
        except ClimateDataError as e:
            logger.error(f"Climate data error at timestep {self.current_timestep}: {e}")
            raise
        except InfeasibleNetworkError as e:
            logger.error(f"Infeasible network at timestep {self.current_timestep}: {e}")
            raise
        except NegativeStorageError as e:
            logger.error(f"Negative storage at timestep {self.current_timestep}: {e}")
            raise
        except EAVInterpolationError as e:
            logger.error(f"EAV interpolation error at timestep {self.current_timestep}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error at timestep {self.current_timestep}: {type(e).__name__}: {e}"
            )
            raise
    
    def _update_state(self, flow_allocations: Dict[str, float]) -> None:
        """
        Update node states based on allocated flows.
        
        This method:
        - Updates flow values on all links
        - Calculates total inflow and outflow for each node
        - Updates storage for StorageNodes
        - Updates delivery and deficit for DemandNodes
        
        Args:
            flow_allocations: Dictionary mapping link_id to allocated flow
        """
        # Update flow values on links
        for link in self.network.links.values():
            link.flow = flow_allocations.get(link.link_id, 0.0)
        
        # Update node states based on flows
        for node in self.network.nodes.values():
            # Calculate total inflow and outflow
            total_inflow = sum(link.flow for link in node.inflows)
            total_outflow = sum(link.flow for link in node.outflows)
            
            # Update storage nodes
            if isinstance(node, StorageNode):
                # Check if storage was already updated by virtual network architecture
                # If so, skip the update_storage() call to avoid double-updating
                if not getattr(node, '_updated_by_carryover', False):
                    node.update_storage(total_inflow, total_outflow)
            
            # Update demand nodes with delivery information
            elif isinstance(node, DemandNode):
                node.update_delivery(total_inflow)
    
    def run(self, num_timesteps: int) -> List[Dict[str, any]]:
        """
        Run simulation for multiple timesteps.
        
        Args:
            num_timesteps: Number of timesteps to simulate
        
        Returns:
            List of results dictionaries, one per timestep
            
        Raises:
            ClimateDataError: If climate data is not available
            InfeasibleNetworkError: If the network flow problem is infeasible
            NegativeStorageError: If storage would become negative
            EAVInterpolationError: If storage is out of EAV table bounds
        """
        logger.info(f"Starting simulation for {num_timesteps} timesteps")
        
        # Prepare future data for look-ahead optimization
        self._prepare_future_data(num_timesteps)
        
        results = []
        try:
            for i in range(num_timesteps):
                timestep_results = self.step()
                results.append(timestep_results)
        except Exception as e:
            logger.error(
                f"Simulation halted at timestep {self.current_timestep} "
                f"after completing {len(results)} timesteps"
            )
            raise
        
        logger.info(f"Simulation completed successfully: {num_timesteps} timesteps")
        return results
    
    def _create_solver_from_config(self) -> NetworkSolver:
        """
        Create appropriate solver based on network optimization configuration.
        
        Returns:
            NetworkSolver instance (LinearProgrammingSolver or LookaheadSolver)
        """
        # Get optimization config from network (set during YAML parsing)
        opt_config = getattr(self.network, 'opt_config', {})
        lookahead_days = opt_config.get('lookahead_days', 1)
        carryover_cost = opt_config.get('carryover_cost', -1.0)
        
        if lookahead_days == 1:
            # Use standard myopic solver
            logger.info("Using LinearProgrammingSolver (myopic optimization)")
            return LinearProgrammingSolver()
        else:
            # Use look-ahead solver
            logger.info(f"Using LookaheadSolver with {lookahead_days}-day horizon")
            return LookaheadSolver(
                lookahead_days=lookahead_days,
                carryover_cost=carryover_cost
            )
    
    def _prepare_future_data(self, num_timesteps: int) -> None:
        """
        Prepare future data for look-ahead optimization.
        
        This method extracts future inflows and demands from the network's
        source and demand nodes for perfect foresight optimization.
        
        Args:
            num_timesteps: Total number of timesteps to simulate
        """
        if self._future_data_prepared or not isinstance(self.solver, LookaheadSolver):
            return
        
        logger.info("Preparing future data for look-ahead optimization...")
        
        future_inflows = {}
        future_demands = {}
        future_climate = []
        
        # Extract future inflows from source nodes
        for node in self.network.nodes.values():
            if node.node_type == "source":
                # Get future inflows from the node's strategy
                if hasattr(node.strategy, 'get_future_values'):
                    # For time series strategies, get future values
                    future_values = node.strategy.get_future_values(num_timesteps)
                    future_inflows[node.node_id] = future_values
                else:
                    # For other strategies, assume constant current inflow
                    future_inflows[node.node_id] = [node.inflow] * num_timesteps
        
        # Extract future demands from demand nodes
        for node in self.network.nodes.values():
            if node.node_type == "demand":
                # Get future demands from the node's demand model
                if hasattr(node.demand_model, 'get_future_demands'):
                    # For time-varying demand models, get future values
                    future_values = node.demand_model.get_future_demands(num_timesteps)
                    future_demands[node.node_id] = future_values
                else:
                    # For static demand models, assume constant current request
                    future_demands[node.node_id] = [node.request] * num_timesteps
        
        # Extract future climate data
        if hasattr(self.climate_engine, 'get_future_climate'):
            future_climate = self.climate_engine.get_future_climate(num_timesteps)
        
        # Set future data on the look-ahead solver
        self.solver.set_future_data(future_inflows, future_demands, future_climate)
        self._future_data_prepared = True
        
        logger.info(f"Future data prepared: {len(future_inflows)} sources, {len(future_demands)} demands")
    
    def get_current_timestep(self) -> int:
        """
        Get current timestep number.
        
        Returns:
            Current timestep (0-indexed)
        """
        return self.current_timestep
    
    def get_network_state(self) -> Dict[str, Dict[str, float]]:
        """
        Get current state of all nodes in the network.
        
        Returns:
            Dictionary mapping node_id to node state dictionary
        """
        return {node.node_id: node.get_state() 
                for node in self.network.nodes.values()}
