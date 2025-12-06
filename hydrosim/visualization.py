"""
Network visualization using Plotly.

This module provides interactive visualization of water network topology.
"""

from typing import Optional, Dict, Tuple
import plotly.graph_objects as go
import math
from hydrosim.config import NetworkGraph


# Node type color mapping
NODE_COLORS = {
    'storage': '#3498db',      # Blue
    'demand': '#e74c3c',       # Red
    'junction': '#9b59b6',     # Purple
    'source': '#2ecc71'        # Green
}


def _calculate_layout(network: NetworkGraph, layout: str) -> Dict[str, Tuple[float, float]]:
    """
    Calculate node positions for visualization.
    
    Args:
        network: NetworkGraph to layout
        layout: Layout algorithm ('circular', 'hierarchical')
    
    Returns:
        Dictionary mapping node_id to (x, y) coordinates
    """
    nodes = list(network.nodes.keys())
    n = len(nodes)
    pos = {}
    
    if layout == 'circular':
        # Arrange nodes in a circle
        for i, node_id in enumerate(nodes):
            angle = 2 * math.pi * i / n
            pos[node_id] = (math.cos(angle), math.sin(angle))
    
    elif layout == 'hierarchical':
        # Simple hierarchical layout based on node type
        # Sources at top, junctions/storage in middle, demands at bottom
        type_levels = {'source': 0, 'storage': 1, 'junction': 1, 'demand': 2}
        
        # Group nodes by level
        levels = {}
        for node_id, node in network.nodes.items():
            level = type_levels.get(node.node_type, 1)
            if level not in levels:
                levels[level] = []
            levels[level].append(node_id)
        
        # Position nodes
        for level, level_nodes in levels.items():
            y = 1.0 - (level * 0.5)  # Top to bottom
            n_level = len(level_nodes)
            for i, node_id in enumerate(level_nodes):
                x = (i - (n_level - 1) / 2) * 0.5  # Center horizontally
                pos[node_id] = (x, y)
    
    else:
        # Default to circular
        for i, node_id in enumerate(nodes):
            angle = 2 * math.pi * i / n
            pos[node_id] = (math.cos(angle), math.sin(angle))
    
    return pos


def visualize_network(
    network: NetworkGraph,
    width: Optional[int] = None,
    height: Optional[int] = None,
    layout: Optional[str] = None
) -> go.Figure:
    """
    Create an interactive visualization of the water network.
    
    Args:
        network: NetworkGraph to visualize
        width: Figure width in pixels (default: from YAML or 600)
        height: Figure height in pixels (default: from YAML or 1200)
        layout: Layout algorithm ('circular', 'hierarchical') (default: from YAML or 'hierarchical')
    
    Returns:
        Plotly Figure object
    """
    # Get config from YAML if available
    viz_config = getattr(network, 'viz_config', {}) or {}
    network_config = viz_config.get('network_map', {})
    
    # Use provided values or fall back to YAML config or defaults
    width = width or network_config.get('width', 600)
    height = height or network_config.get('height', 1200)
    layout = layout or network_config.get('layout', 'hierarchical')
    
    # Calculate node positions
    pos = _calculate_layout(network, layout)
    
    # Create Plotly figure
    fig = go.Figure()
    
    # Add edges (links)
    edge_traces, annotations = _create_edge_traces(network, pos)
    for trace in edge_traces:
        fig.add_trace(trace)
    
    # Add nodes
    node_traces = _create_node_traces(network, pos)
    for trace in node_traces:
        fig.add_trace(trace)
    
    # Update layout
    title = network.model_name or "Water Network"
    if network.author:
        title += f"<br><sub>Author: {network.author}</sub>"
    
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        showlegend=True,
        hovermode='closest',
        width=width,
        height=height,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=80, b=20),
        annotations=annotations
    )
    
    return fig


def _create_edge_traces(network: NetworkGraph, pos: Dict[str, Tuple[float, float]]) -> tuple:
    """Create edge traces with arrows. Returns (traces, annotations)."""
    traces = []
    annotations = []
    
    for link_id, link in network.links.items():
        source_id = link.source.node_id
        target_id = link.target.node_id
        
        x0, y0 = pos[source_id]
        x1, y1 = pos[target_id]
        
        # Create line trace
        trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=3, color='#7f8c8d'),
            hoverinfo='text',
            hovertext=f"Link: {link_id}<br>From: {source_id}<br>To: {target_id}",
            showlegend=False
        )
        traces.append(trace)
        
        # Create arrow annotation pointing to center of target node
        annotation = dict(
            x=x1,
            y=y1,
            ax=x0,
            ay=y0,
            xref='x',
            yref='y',
            axref='x',
            ayref='y',
            showarrow=True,
            arrowhead=2,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor='#7f8c8d'
        )
        annotations.append(annotation)
        
    return traces, annotations


def _create_node_traces(network: NetworkGraph, pos: Dict[str, Tuple[float, float]]) -> list:
    """Create node traces grouped by type."""
    traces = []
    
    # Group nodes by type
    nodes_by_type = {}
    for node_id, node in network.nodes.items():
        node_type = node.node_type
        if node_type not in nodes_by_type:
            nodes_by_type[node_type] = []
        nodes_by_type[node_type].append((node_id, node))
    
    # Create trace for each node type
    for node_type, nodes in nodes_by_type.items():
        x_coords = []
        y_coords = []
        labels = []
        hover_texts = []
        
        for node_id, node in nodes:
            x, y = pos[node_id]
            x_coords.append(x)
            y_coords.append(y)
            labels.append(node_id)
            
            # Build hover text
            hover_parts = [f"<b>{node_id}</b>", f"Type: {node_type}"]
            if hasattr(node, 'initial_storage'):
                hover_parts.append(f"Initial Storage: {node.initial_storage:.0f} m³")
            if hasattr(node, 'max_storage'):
                hover_parts.append(f"Max Storage: {node.max_storage:.0f} m³")
            hover_texts.append("<br>".join(hover_parts))
        
        trace = go.Scatter(
            x=x_coords,
            y=y_coords,
            mode='markers+text',
            marker=dict(
                size=30,
                color=NODE_COLORS.get(node_type, '#95a5a6'),
                line=dict(width=3, color='white')
            ),
            text=labels,
            textposition='top center',
            textfont=dict(size=11, family='Arial Black'),
            hoverinfo='text',
            hovertext=hover_texts,
            name=node_type.capitalize(),
            showlegend=True
        )
        traces.append(trace)
    
    return traces


def save_network_visualization(
    network: NetworkGraph,
    filepath: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    layout: Optional[str] = None
) -> None:
    """
    Save network visualization to HTML file.
    
    Args:
        network: NetworkGraph to visualize
        filepath: Output HTML file path (default: from YAML or 'network_topology.html')
        width: Figure width in pixels (default: from YAML or 600)
        height: Figure height in pixels (default: from YAML or 1200)
        layout: Layout algorithm (default: from YAML or 'hierarchical')
    """
    # Get config from YAML if available
    viz_config = getattr(network, 'viz_config', {}) or {}
    network_config = viz_config.get('network_map', {})
    
    # Use provided values or fall back to YAML config or defaults
    filepath = filepath or network_config.get('output_file', 'network_topology.html')
    
    fig = visualize_network(network, width, height, layout)
    fig.write_html(filepath)
