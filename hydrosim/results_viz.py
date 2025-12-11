"""
Results visualization for HydroSim simulations.

This module provides automated time series plotting based on YAML configuration.
"""

from typing import List, Dict, Any, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from hydrosim.results import ResultsWriter
from hydrosim.config import NetworkGraph


class ResultsVisualizer:
    """
    Automated results visualization based on configuration.
    
    Generates time series plots for climate, sources, reservoirs, and demands
    based on YAML visualization configuration.
    """
    
    def __init__(self, results_writer: ResultsWriter, network: NetworkGraph, 
                 viz_config: Optional[Dict[str, Any]] = None):
        """
        Initialize results visualizer.
        
        Args:
            results_writer: ResultsWriter with accumulated simulation results
            network: NetworkGraph with model structure
            viz_config: Visualization configuration from YAML (optional)
        """
        self.results_writer = results_writer
        self.network = network
        self.viz_config = viz_config or {}
        
        # Convert results to dataframes for easier plotting
        self._prepare_dataframes()
    
    def _prepare_dataframes(self) -> None:
        """Convert results to pandas DataFrames."""
        results = self.results_writer.get_results()
        
        if not results:
            self.df_flows = pd.DataFrame()
            self.df_storage = pd.DataFrame()
            self.df_demands = pd.DataFrame()
            self.df_sources = pd.DataFrame()
            self.df_climate = pd.DataFrame()
            return
        
        # Flows dataframe
        flows_data = []
        for r in results:
            for link_id, flow in r['flows'].items():
                flows_data.append({
                    'date': r['date'],
                    'link_id': link_id,
                    'flow': flow
                })
        self.df_flows = pd.DataFrame(flows_data)
        
        # Storage dataframe
        storage_data = []
        for r in results:
            for node_id, state in r['node_states'].items():
                if 'storage' in state:
                    storage_data.append({
                        'date': r['date'],
                        'node_id': node_id,
                        'storage': state['storage'],
                        'elevation': state['elevation'],
                        'surface_area': state['surface_area'],
                        'evap_loss': state['evap_loss']
                    })
        self.df_storage = pd.DataFrame(storage_data)
        
        # Demands dataframe
        demands_data = []
        for r in results:
            for node_id, state in r['node_states'].items():
                if 'deficit' in state:
                    demands_data.append({
                        'date': r['date'],
                        'node_id': node_id,
                        'request': state['request'],
                        'delivered': state['delivered'],
                        'deficit': state['deficit']
                    })
        self.df_demands = pd.DataFrame(demands_data)
        
        # Sources dataframe
        sources_data = []
        for r in results:
            for node_id, state in r['node_states'].items():
                if 'inflow' in state and 'deficit' not in state:
                    sources_data.append({
                        'date': r['date'],
                        'node_id': node_id,
                        'inflow': state['inflow']
                    })
        self.df_sources = pd.DataFrame(sources_data)
        
        # Climate dataframe
        climate_data = []
        for r in results:
            if 'climate' in r:
                climate = r['climate']
                climate_data.append({
                    'date': r['date'],
                    'precip': climate.precip,
                    'tmax': climate.t_max,
                    'tmin': climate.t_min,
                    'solar': climate.solar,
                    'et0': climate.et0
                })
        self.df_climate = pd.DataFrame(climate_data)
    
    def generate_all_plots(self) -> go.Figure:
        """
        Generate all plots based on configuration.
        
        Returns:
            Plotly Figure with all subplots
        """
        plots_config = self.viz_config.get('plots', [])
        layout_config = self.viz_config.get('layout', {})
        
        if not plots_config:
            # Default plots if no config provided
            plots_config = self._get_default_plots()
        
        # Expand auto-generated plots
        expanded_plots = self._expand_auto_plots(plots_config)
        
        # Create subplots
        n_plots = len(expanded_plots)
        fig = make_subplots(
            rows=n_plots,
            cols=1,
            subplot_titles=[p.get('title', '') for p in expanded_plots],
            specs=[[{"secondary_y": True}] for _ in range(n_plots)],
            vertical_spacing=0.08
        )
        
        # Generate each plot
        for i, plot_config in enumerate(expanded_plots, start=1):
            self._add_plot(fig, plot_config, row=i)
        
        # Update layout
        width = layout_config.get('width', 1200)
        height = layout_config.get('height', 400) * n_plots
        
        fig.update_layout(
            height=height,
            width=width + 250,  # Add extra width for custom legends
            showlegend=False,  # Disable global legend - we'll use custom annotations
            hovermode='x unified'
        )
        
        # Add custom legends for each subplot
        self._add_custom_legends(fig, expanded_plots)
        
        return fig
    
    def _add_custom_legends(self, fig: go.Figure, plots_config: List[Dict]) -> None:
        """Add custom legend annotations for each subplot."""
        n_plots = len(plots_config)
        
        # Group traces by their legendgroup (subplot)
        traces_by_subplot = {}
        for trace in fig.data:
            if hasattr(trace, 'legendgroup') and trace.legendgroup:
                subplot_key = trace.legendgroup
                if subplot_key not in traces_by_subplot:
                    traces_by_subplot[subplot_key] = []
                traces_by_subplot[subplot_key].append(trace)
        
        # Create custom legend for each subplot
        for i, plot_config in enumerate(plots_config, start=1):
            subplot_key = f"plot_{i}"
            
            if subplot_key in traces_by_subplot:
                # Calculate vertical position for this subplot's legend
                # Position legend in the middle of each subplot's vertical space
                subplot_y_center = 1 - (i - 0.5) / n_plots
                
                # Create legend entries for this subplot
                legend_items = []
                plot_title = plot_config.get('title', f'Plot {i}')
                legend_items.append(f"<b>{plot_title}</b>")
                
                for trace in traces_by_subplot[subplot_key]:
                    # Get trace color and line style
                    color = self._get_trace_color(trace)
                    line_style = self._get_trace_line_style(trace)
                    
                    # Create legend entry with color indicator
                    legend_entry = f"<span style='color:{color}'>{line_style} {trace.name}</span>"
                    legend_items.append(legend_entry)
                
                # Add legend annotation
                legend_text = "<br>".join(legend_items)
                fig.add_annotation(
                    x=1.02,  # Position to the right of plots
                    y=subplot_y_center,
                    xref="paper",
                    yref="paper",
                    text=legend_text,
                    showarrow=False,
                    xanchor="left",
                    yanchor="middle",
                    bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="rgba(0,0,0,0.2)",
                    borderwidth=1,
                    font=dict(size=10),
                    align="left"
                )
    
    def _get_trace_color(self, trace) -> str:
        """Extract color from trace for legend display."""
        # Check line color first
        if hasattr(trace, 'line') and trace.line and hasattr(trace.line, 'color') and trace.line.color:
            return trace.line.color
        # Check marker color
        elif hasattr(trace, 'marker') and trace.marker and hasattr(trace.marker, 'color') and trace.marker.color:
            return trace.marker.color
        else:
            # Default colors from Plotly's default color sequence
            default_colors = [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
            ]
            # Use a hash of the trace name to consistently assign colors
            color_index = hash(trace.name) % len(default_colors)
            return default_colors[color_index]
    
    def _get_trace_line_style(self, trace) -> str:
        """Get line style indicator for legend display."""
        if hasattr(trace, 'line') and trace.line and 'dash' in trace.line:
            dash_style = trace.line.dash
            if dash_style == 'dash':
                return '- - -'
            elif dash_style == 'dot':
                return '· · ·'
            elif dash_style == 'dashdot':
                return '- · -'
        
        if hasattr(trace, 'fill') and trace.fill:
            return '▬▬▬'  # Filled area indicator
        
        return '───'  # Solid line indicator
    
    def _expand_auto_plots(self, plots_config: List[Dict]) -> List[Dict]:
        """Expand auto-generated plots for multiple nodes."""
        expanded = []
        
        for plot_config in plots_config:
            if plot_config.get('auto', False):
                plot_type = plot_config['type']
                
                if plot_type == 'source':
                    # Generate plot for each source node
                    for node_id, node in self.network.nodes.items():
                        if node.node_type == 'source':
                            expanded.append(self._create_node_plot_config(
                                plot_config, node_id
                            ))
                
                elif plot_type == 'reservoir':
                    # Generate plot for each storage node
                    for node_id, node in self.network.nodes.items():
                        if node.node_type == 'storage':
                            expanded.append(self._create_node_plot_config(
                                plot_config, node_id
                            ))
                
                elif plot_type == 'demand':
                    # Generate plot for each demand node
                    for node_id, node in self.network.nodes.items():
                        if node.node_type == 'demand':
                            expanded.append(self._create_node_plot_config(
                                plot_config, node_id
                            ))
            else:
                expanded.append(plot_config)
        
        return expanded
    
    def _create_node_plot_config(self, template: Dict, node_id: str) -> Dict:
        """Create plot config for specific node from template."""
        config = template.copy()
        config['node_id'] = node_id
        
        # Replace template variables in title
        if 'title_template' in config:
            config['title'] = config['title_template'].format(node_id=node_id)
        
        return config
    
    def _add_plot(self, fig: go.Figure, plot_config: Dict, row: int) -> None:
        """Add a single plot to the figure."""
        plot_type = plot_config['type']
        
        if plot_type == 'climate':
            self._add_climate_plot(fig, plot_config, row)
        elif plot_type == 'source':
            self._add_source_plot(fig, plot_config, row)
        elif plot_type == 'reservoir':
            self._add_reservoir_plot(fig, plot_config, row)
        elif plot_type == 'demand':
            self._add_demand_plot(fig, plot_config, row)
    
    def _add_climate_plot(self, fig: go.Figure, config: Dict, row: int) -> None:
        """Add climate plot."""
        if self.df_climate.empty:
            return
        
        y1_config = config.get('y1_axis', {})
        y2_config = config.get('y2_axis', {})
        
        legend_group = f"plot_{row}"
        
        # Y1 variables (precipitation)
        for var in y1_config.get('variables', []):
            if var in self.df_climate.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.df_climate['date'],
                        y=self.df_climate[var],
                        name=var.capitalize(),
                        mode='lines',
                        legendgroup=legend_group,
                        showlegend=False
                    ),
                    row=row, col=1, secondary_y=False
                )
        
        # Y2 variables (temperature)
        for var in y2_config.get('variables', []):
            if var in self.df_climate.columns:
                fig.add_trace(
                    go.Scatter(
                        x=self.df_climate['date'],
                        y=self.df_climate[var],
                        name=var.upper(),
                        legendgroup=legend_group,
                        showlegend=False,
                        mode='lines',
                        line=dict(dash='dash')
                    ),
                    row=row, col=1, secondary_y=True
                )
        
        # Update axes labels
        fig.update_yaxes(title_text=y1_config.get('label', ''), row=row, col=1, secondary_y=False)
        fig.update_yaxes(title_text=y2_config.get('label', ''), row=row, col=1, secondary_y=True)
    
    def _add_source_plot(self, fig: go.Figure, config: Dict, row: int) -> None:
        """Add source/catchment plot."""
        node_id = config.get('node_id')
        if self.df_sources.empty or not node_id:
            return
        
        df_node = self.df_sources[self.df_sources['node_id'] == node_id]
        y1_config = config.get('y1_axis', {})
        legend_group = f"plot_{row}"
        
        for var in y1_config.get('variables', []):
            if var in df_node.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_node['date'],
                        y=df_node[var],
                        name=f"{node_id} {var}",
                        mode='lines',
                        legendgroup=legend_group,
                        showlegend=False
                    ),
                    row=row, col=1, secondary_y=False
                )
        
        fig.update_yaxes(title_text=y1_config.get('label', ''), row=row, col=1, secondary_y=False)
    
    def _add_reservoir_plot(self, fig: go.Figure, config: Dict, row: int) -> None:
        """Add reservoir plot."""
        node_id = config.get('node_id')
        if self.df_storage.empty or not node_id:
            return
        
        df_node = self.df_storage[self.df_storage['node_id'] == node_id]
        y1_config = config.get('y1_axis', {})
        y2_config = config.get('y2_axis', {})
        legend_group = f"plot_{row}"
        
        # Y1: Storage
        for var in y1_config.get('variables', []):
            if var in df_node.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_node['date'],
                        y=df_node[var],
                        name=f"{node_id} {var}",
                        mode='lines',
                        fill='tozeroy',
                        legendgroup=legend_group,
                        showlegend=False
                    ),
                    row=row, col=1, secondary_y=False
                )
        
        # Y2: Flows (inflow, outflow, evap, spill)
        # Calculate inflow and outflow from links
        inflows = self._calculate_node_inflows(node_id)
        outflows = self._calculate_node_outflows(node_id)
        spills = self._calculate_node_spills(node_id)
        
        if not inflows.empty:
            fig.add_trace(
                go.Scatter(
                    x=inflows['date'],
                    y=inflows['flow'],
                    name=f"{node_id} inflow",
                    mode='lines',
                    legendgroup=legend_group,
                    showlegend=False
                ),
                row=row, col=1, secondary_y=True
            )
        
        if not outflows.empty:
            fig.add_trace(
                go.Scatter(
                    x=outflows['date'],
                    y=outflows['flow'],
                    name=f"{node_id} outflow",
                    mode='lines',
                    legendgroup=legend_group,
                    showlegend=False
                ),
                row=row, col=1, secondary_y=True
            )
        
        # Evaporation loss
        if 'evap_loss' in df_node.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_node['date'],
                    y=df_node['evap_loss'],
                    name=f"{node_id} evap_loss",
                    mode='lines',
                    line=dict(dash='dot'),
                    legendgroup=legend_group,
                    showlegend=False
                ),
                row=row, col=1, secondary_y=True
            )
        
        # Spills
        if not spills.empty:
            fig.add_trace(
                go.Scatter(
                    x=spills['date'],
                    y=spills['flow'],
                    name=f"{node_id} spill",
                    mode='lines',
                    line=dict(dash='dash'),
                    legendgroup=legend_group,
                    showlegend=False
                ),
                row=row, col=1, secondary_y=True
            )
        
        fig.update_yaxes(title_text=y1_config.get('label', ''), row=row, col=1, secondary_y=False)
        fig.update_yaxes(title_text=y2_config.get('label', ''), row=row, col=1, secondary_y=True)
    
    def _add_demand_plot(self, fig: go.Figure, config: Dict, row: int) -> None:
        """Add demand plot."""
        node_id = config.get('node_id')
        if self.df_demands.empty or not node_id:
            return
        
        df_node = self.df_demands[self.df_demands['node_id'] == node_id]
        y1_config = config.get('y1_axis', {})
        legend_group = f"plot_{row}"
        
        for var in y1_config.get('variables', []):
            if var in df_node.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_node['date'],
                        y=df_node[var],
                        name=f"{node_id} {var}",
                        mode='lines',
                        legendgroup=legend_group,
                        showlegend=False
                    ),
                    row=row, col=1, secondary_y=False
                )
        
        fig.update_yaxes(title_text=y1_config.get('label', ''), row=row, col=1, secondary_y=False)
    
    def _calculate_node_inflows(self, node_id: str) -> pd.DataFrame:
        """Calculate total inflows to a node."""
        node = self.network.nodes.get(node_id)
        if not node or not node.inflows:
            return pd.DataFrame()
        
        inflow_links = [link.link_id for link in node.inflows if not link.link_id.endswith('_carryover')]
        
        if not inflow_links or self.df_flows.empty:
            return pd.DataFrame()
        
        df_inflows = self.df_flows[self.df_flows['link_id'].isin(inflow_links)]
        return df_inflows.groupby('date')['flow'].sum().reset_index()
    
    def _calculate_node_outflows(self, node_id: str) -> pd.DataFrame:
        """Calculate total outflows from a node (excluding spills and carryover)."""
        node = self.network.nodes.get(node_id)
        if not node or not node.outflows:
            return pd.DataFrame()
        
        outflow_links = [
            link.link_id for link in node.outflows 
            if not link.link_id.endswith('_spill') and not link.link_id.endswith('_carryover')
        ]
        
        if not outflow_links or self.df_flows.empty:
            return pd.DataFrame()
        
        df_outflows = self.df_flows[self.df_flows['link_id'].isin(outflow_links)]
        return df_outflows.groupby('date')['flow'].sum().reset_index()
    
    def _calculate_node_spills(self, node_id: str) -> pd.DataFrame:
        """Calculate spills from a node."""
        node = self.network.nodes.get(node_id)
        if not node or not node.outflows:
            return pd.DataFrame()
        
        spill_links = [link.link_id for link in node.outflows if link.link_id.endswith('_spill')]
        
        if not spill_links or self.df_flows.empty:
            return pd.DataFrame()
        
        df_spills = self.df_flows[self.df_flows['link_id'].isin(spill_links)]
        return df_spills.groupby('date')['flow'].sum().reset_index()
    
    def _get_default_plots(self) -> List[Dict]:
        """Get default plot configuration if none provided."""
        return [
            {
                'type': 'climate',
                'title': 'Climate Conditions',
                'y1_axis': {'label': 'Precipitation (mm/day)', 'variables': ['precip']},
                'y2_axis': {'label': 'Temperature (°C)', 'variables': ['tmax', 'tmin']}
            },
            {
                'type': 'source',
                'auto': True,
                'title_template': '{node_id} Runoff',
                'y1_axis': {'label': 'Runoff (m³/day)', 'variables': ['inflow']}
            },
            {
                'type': 'reservoir',
                'auto': True,
                'title_template': '{node_id} Operations',
                'y1_axis': {'label': 'Storage (m³)', 'variables': ['storage']},
                'y2_axis': {'label': 'Flow (m³/day)', 'variables': ['inflow', 'outflow', 'evap_loss', 'spill']}
            },
            {
                'type': 'demand',
                'auto': True,
                'title_template': '{node_id} Supply vs Demand',
                'y1_axis': {'label': 'Flow (m³/day)', 'variables': ['request', 'delivered', 'deficit']}
            }
        ]
    
    def save_html(self, filepath: str) -> None:
        """
        Generate and save all plots to HTML file.
        
        Args:
            filepath: Output HTML file path
        """
        fig = self.generate_all_plots()
        fig.write_html(filepath)


def visualize_results(results_writer: ResultsWriter, network: NetworkGraph,
                     viz_config: Optional[Dict[str, Any]] = None,
                     output_file: str = "simulation_results.html") -> go.Figure:
    """
    Convenience function to visualize simulation results.
    
    Args:
        results_writer: ResultsWriter with simulation results
        network: NetworkGraph with model structure
        viz_config: Visualization configuration from YAML
        output_file: Output HTML file path
    
    Returns:
        Plotly Figure object
    """
    visualizer = ResultsVisualizer(results_writer, network, viz_config)
    fig = visualizer.generate_all_plots()
    visualizer.save_html(output_file)
    return fig
