# HydroSim: Project Steering Document

**Version:** 1.1  
**Date:** December 3, 2025  
**Scope:** Daily Timestep Water Resources Planning Framework

## 1. The Mission

To provide a Python-based framework for water resources consulting that unifies process-based simulation (hydrology/demands) and network allocation (systems analysis).

FlowSim allows engineers to model complex, interconnected systems where flow decisions are driven simultaneously by:

- Physical Constraints (Pipe capacity, Weir hydraulics)
- Local Control Rules (PID, Deadbands, Rule Curves)
- Global Network Optimization (Minimizing cost / Maximizing priority)

## 2. Core Philosophy

**Topology is Explicit:** The network structure is defined by Links, not by hidden references inside components. If you can't draw the graph from the YAML, the model is malformed.

**Separation of Concerns:**

- **Nodes** handle "Vertical Physics" (Interactions with the environment: Rain, Evap, Demand).
- **Links** handle "Horizontal Physics" (Transport constraints between nodes).
- **Solver** handles "Decisions" (Allocating flow to satisfy constraints).

**The "Constraint Stacking" Principle:** We do not hard-code logic into the solver. Instead, Links calculate their own feasible limits ($Q_{min}, Q_{max}$) based on physics and logic before the solver runs. The solver simply finds the best path within those limits.

## 3. The Environment (Global Context)

The model operates within a fixed temporal and climatic context.

**Time Step:** Strictly 1-day. No sub-daily routing (Saint-Venant equations are out of scope). We assume steady-state flow within the timestep.

**Climate Engine:**

- **Drivers:** Precipitation, $T_{max}$, $T_{min}$, Solar Radiation.
- **Sources:** Time Series (CSV) OR Stochastic Generation (WGEN).
- **Derived Physics:** Reference Evapotranspiration ($ET_0$) is calculated globally (Hargreaves method) and broadcast to all components.

**Site Definition:** Models are anchored by a specific Latitude/Elevation.

## 4. The Architecture: Nodes, Links, Solver

### I. The Node (State & Boundary Conditions)

Nodes are the "Places" in the model. They handle mass balance and boundary generation.

**StorageNode (Reservoir/Tank):**

- **Role:** Holds mass. Tracks $dS/dt$.
- **Physics:** Calculates evaporation losses based on surface area (EAV table).

**JunctionNode (Stream/Hub):**

- **Role:** Stateless connection point. $\sum Inflow = \sum Outflow$.

**SourceNode (Generator):**

- **Role:** Injects water into the system.
- **Strategy Pattern:** Uses a pluggable Generator to determine volume.
  - **TimeSeriesStrategy:** Reads from CSV.
  - **HydrologyStrategy:** Runs Snow17/AWBM physics to simulate runoff.

**DemandNode (Sink):**

- **Role:** Consumes water.
- **Strategy Pattern:** Uses a DemandModel to calculate the Request ($D$).
  - **Municipal:** Population-based.
  - **Agriculture:** Crop Coefficient ($K_c$) based.
- **Solver View:** The Request is treated as a high-priority target. Unmet demand is tracked as Deficit.

### II. The Link (Transport & Constraints)

Links are the "Paths". They are the only mechanism for mass transfer. Every Link defines a Constraint Funnel that narrows down the feasible flow for the solver.

$$Q_{limit} = \min(PhysicalLimit, HydraulicLimit, ControlLimit)$$

- **Physical Layer:** Static limits (Pipe diameter, Pump rating).
- **Hydraulic Layer:** Dynamic limits based on state (Weir equation using upstream Head).
- **Control Layer:** Logic-based limits. Supports Continuous Control:
  - **Fractional:** Throttles capacity (0.0 to 1.0). Used for PID/Proportional logic.
  - **Absolute:** Sets a hard cap (e.g., "Max 50 cfs"). Used for Rule Curves.
  - **Switch:** On/Off (Deadbands).
- **Cost/Priority:** Every Link has a cost. The solver minimizes $\sum (Q_{link} \times Cost_{link})$.

### III. The Allocator (Solver)

- **Role:** Solves the Minimum Cost Network Flow problem for the current timestep.
- **Scope:** Stepwise Optimization (Greedy). It optimizes the current day based on the constraints provided by the Links.

## 5. The Simulation Loop (Order of Operations)

To ensure Global Optimization respects Local Controls, the timestep execution order is strict:

1. **Environment Step:**
   - Update Climate Drivers ($P, T, Solar$).
   - Calculate Global $ET_0$.

2. **Node Step (Vertical Physics):**
   - SourceNodes run generators (Hydrology) → Produce Inflow $I$.
   - DemandNodes run demand models → Produce Target $D$.
   - StorageNodes calculate Evap Loss.

3. **Link Step (Constraint Update):**
   - Every Link queries its Source/Target nodes.
   - Applies Physics → Hydraulics → Control Logic.
   - Output: Hard bounds ($Q_{min}, Q_{max}$) and Cost ($C$) for the solver.

4. **Solver Step (Network Allocation):**
   - Construct the matrix/graph.
   - Solve for $Q$ such that Mass Balance is conserved and Cost is minimized.

5. **State Update:**
   - Move mass according to $Q$.
   - Update Storage ($S_{t+1}$).

## 6. Anti-Patterns (What NOT to do)

- **No Hidden Flows:** Water cannot teleport. If Node A sends water to Node B, a Link object must exist between them.
- **No "Super-Nodes":** A Reservoir Node should not calculate its own spillway release. That logic belongs in the Link connecting the Reservoir to the River.
- **No Sub-Daily Loops:** If a process requires 15-minute routing, it belongs in a different tool. FlowSim is for strategic planning, not hydraulic transient analysis.
