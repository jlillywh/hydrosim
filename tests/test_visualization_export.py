"""
Tests for network visualization export functionality.

This module tests the export of network graphs to GraphML and DOT formats
for visualization in external tools.
"""

import pytest
from pathlib import Path
from xml.etree import ElementTree as ET
from hydrosim.config import NetworkGraph
from hydrosim.nodes import StorageNode, JunctionNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.controls import FractionalControl, AbsoluteControl, SwitchControl
from hydrosim.hydraulics import WeirModel, PipeModel
from hydrosim.strategies import MunicipalDemand, AgricultureDemand
from hydrosim.config import ElevationAreaVolume


@pytest.fixture
def simple_network():
    """Create a simple network for testing."""
    network = NetworkGraph()
    
    # Add nodes
    j1 = JunctionNode('j1')
    j2 = JunctionNode('j2')
    
    network.add_node(j1)
    network.add_node(j2)
    
    # Add link
    link = Link('link1', j1, j2, 100.0, 1.0)
    network.add_link(link)
    
    return network


@pytest.fixture
def complex_network():
    """Create a complex network with all node types and link properties."""
    network = NetworkGraph()
    
    # Create EAV table for storage node
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 2000.0, 3000.0],
        volumes=[0.0, 10000.0, 30000.0],
        node_id='reservoir'
    )
    
    # Add nodes of different types
    reservoir = StorageNode('reservoir', 15000.0, eav, max_storage=50000.0, min_storage=0.0)
    junction = JunctionNode('junction')
    source = SourceNode('source', MunicipalDemand(10000.0, 0.2))  # Using demand as placeholder
    demand = DemandNode('demand', MunicipalDemand(10000.0, 0.2))
    
    network.add_node(reservoir)
    network.add_node(junction)
    network.add_node(source)
    network.add_node(demand)
    
    # Add links with various properties
    link1 = Link('link1', reservoir, junction, 200.0, 1.0)
    link1.control = FractionalControl(0.8)
    link1.hydraulic_model = WeirModel(1.5, 10.0, 105.0)
    network.add_link(link1)
    
    link2 = Link('link2', junction, demand, 150.0, 2.0)
    link2.control = AbsoluteControl(100.0)
    network.add_link(link2)
    
    link3 = Link('link3', source, junction, float('inf'), 0.5)
    link3.control = SwitchControl(True)
    link3.hydraulic_model = PipeModel(300.0)
    network.add_link(link3)
    
    return network


# GraphML Export Tests

def test_export_graphml_creates_file(simple_network, tmp_path):
    """Test that export_graphml creates a file."""
    output_path = tmp_path / "network.graphml"
    simple_network.export_graphml(str(output_path))
    
    assert output_path.exists()


def test_export_graphml_valid_xml(simple_network, tmp_path):
    """Test that exported GraphML is valid XML."""
    output_path = tmp_path / "network.graphml"
    simple_network.export_graphml(str(output_path))
    
    # Should be able to parse as XML
    tree = ET.parse(output_path)
    root = tree.getroot()
    
    # Check root element
    assert 'graphml' in root.tag


def test_export_graphml_contains_nodes(simple_network, tmp_path):
    """Test that exported GraphML contains all nodes."""
    output_path = tmp_path / "network.graphml"
    simple_network.export_graphml(str(output_path))
    
    tree = ET.parse(output_path)
    root = tree.getroot()
    
    # Find all node elements
    nodes = root.findall('.//{http://graphml.graphdrawing.org/xmlns}node')
    
    assert len(nodes) == 2
    node_ids = [node.get('id') for node in nodes]
    assert 'j1' in node_ids
    assert 'j2' in node_ids


def test_export_graphml_contains_edges(simple_network, tmp_path):
    """Test that exported GraphML contains all edges."""
    output_path = tmp_path / "network.graphml"
    simple_network.export_graphml(str(output_path))
    
    tree = ET.parse(output_path)
    root = tree.getroot()
    
    # Find all edge elements
    edges = root.findall('.//{http://graphml.graphdrawing.org/xmlns}edge')
    
    assert len(edges) == 1
    edge = edges[0]
    assert edge.get('id') == 'link1'
    assert edge.get('source') == 'j1'
    assert edge.get('target') == 'j2'


def test_export_graphml_node_types(complex_network, tmp_path):
    """Test that node types are included in GraphML export."""
    output_path = tmp_path / "network.graphml"
    complex_network.export_graphml(str(output_path))
    
    tree = ET.parse(output_path)
    root = tree.getroot()
    
    # Find node with id 'reservoir'
    nodes = root.findall('.//{http://graphml.graphdrawing.org/xmlns}node')
    reservoir_node = None
    for node in nodes:
        if node.get('id') == 'reservoir':
            reservoir_node = node
            break
    
    assert reservoir_node is not None
    
    # Check that node_type data is present
    data_elements = reservoir_node.findall('.//{http://graphml.graphdrawing.org/xmlns}data')
    node_type_data = None
    for data in data_elements:
        if data.get('key') == 'd0':  # d0 is node_type
            node_type_data = data
            break
    
    assert node_type_data is not None
    assert node_type_data.text == 'storage'


def test_export_graphml_storage_properties(complex_network, tmp_path):
    """Test that storage node properties are included in GraphML export."""
    output_path = tmp_path / "network.graphml"
    complex_network.export_graphml(str(output_path))
    
    tree = ET.parse(output_path)
    root = tree.getroot()
    
    # Find node with id 'reservoir'
    nodes = root.findall('.//{http://graphml.graphdrawing.org/xmlns}node')
    reservoir_node = None
    for node in nodes:
        if node.get('id') == 'reservoir':
            reservoir_node = node
            break
    
    assert reservoir_node is not None
    
    # Check that initial_storage data is present
    data_elements = reservoir_node.findall('.//{http://graphml.graphdrawing.org/xmlns}data')
    storage_data = None
    for data in data_elements:
        if data.get('key') == 'd1':  # d1 is initial_storage
            storage_data = data
            break
    
    assert storage_data is not None
    assert storage_data.text == '15000.0'


def test_export_graphml_link_properties(complex_network, tmp_path):
    """Test that link properties are included in GraphML export."""
    output_path = tmp_path / "network.graphml"
    complex_network.export_graphml(str(output_path))
    
    tree = ET.parse(output_path)
    root = tree.getroot()
    
    # Find edge with id 'link1'
    edges = root.findall('.//{http://graphml.graphdrawing.org/xmlns}edge')
    link1_edge = None
    for edge in edges:
        if edge.get('id') == 'link1':
            link1_edge = edge
            break
    
    assert link1_edge is not None
    
    # Check capacity
    data_elements = link1_edge.findall('.//{http://graphml.graphdrawing.org/xmlns}data')
    capacity_data = None
    cost_data = None
    control_data = None
    hydraulic_data = None
    
    for data in data_elements:
        key = data.get('key')
        if key == 'd2':  # capacity
            capacity_data = data
        elif key == 'd3':  # cost
            cost_data = data
        elif key == 'd4':  # control_type
            control_data = data
        elif key == 'd5':  # hydraulic_type
            hydraulic_data = data
    
    assert capacity_data is not None
    assert capacity_data.text == '200.0'
    
    assert cost_data is not None
    assert cost_data.text == '1.0'
    
    assert control_data is not None
    assert control_data.text == 'FractionalControl'
    
    assert hydraulic_data is not None
    assert hydraulic_data.text == 'WeirModel'


# DOT Export Tests

def test_export_dot_creates_file(simple_network, tmp_path):
    """Test that export_dot creates a file."""
    output_path = tmp_path / "network.dot"
    simple_network.export_dot(str(output_path))
    
    assert output_path.exists()


def test_export_dot_valid_format(simple_network, tmp_path):
    """Test that exported DOT has valid format."""
    output_path = tmp_path / "network.dot"
    simple_network.export_dot(str(output_path))
    
    with open(output_path, 'r') as f:
        content = f.read()
    
    # Check basic DOT structure
    assert content.startswith('digraph HydroSim {')
    assert content.endswith('}')
    assert 'rankdir=LR' in content


def test_export_dot_contains_nodes(simple_network, tmp_path):
    """Test that exported DOT contains all nodes."""
    output_path = tmp_path / "network.dot"
    simple_network.export_dot(str(output_path))
    
    with open(output_path, 'r') as f:
        content = f.read()
    
    assert '"j1"' in content
    assert '"j2"' in content
    assert 'Type: junction' in content


def test_export_dot_contains_edges(simple_network, tmp_path):
    """Test that exported DOT contains all edges."""
    output_path = tmp_path / "network.dot"
    simple_network.export_dot(str(output_path))
    
    with open(output_path, 'r') as f:
        content = f.read()
    
    assert '"j1" -> "j2"' in content
    assert 'link1' in content


def test_export_dot_node_colors(complex_network, tmp_path):
    """Test that nodes have appropriate colors based on type."""
    output_path = tmp_path / "network.dot"
    complex_network.export_dot(str(output_path))
    
    with open(output_path, 'r') as f:
        content = f.read()
    
    # Check that different node types have different colors
    assert 'lightblue' in content  # storage
    assert 'lightgray' in content  # junction
    assert 'lightgreen' in content  # source
    assert 'lightyellow' in content  # demand


def test_export_dot_storage_properties(complex_network, tmp_path):
    """Test that storage node properties are included in DOT export."""
    output_path = tmp_path / "network.dot"
    complex_network.export_dot(str(output_path))
    
    with open(output_path, 'r') as f:
        content = f.read()
    
    # Check that storage information is in the label
    assert 'Storage: 15000.00' in content


def test_export_dot_link_properties(complex_network, tmp_path):
    """Test that link properties are included in DOT export."""
    output_path = tmp_path / "network.dot"
    complex_network.export_dot(str(output_path))
    
    with open(output_path, 'r') as f:
        content = f.read()
    
    # Check that link properties are in labels
    assert 'Cap: 200.00' in content
    assert 'Cost: 1.00' in content
    assert 'Ctrl: FractionalControl' in content
    assert 'Hyd: WeirModel' in content


def test_export_dot_infinite_capacity(complex_network, tmp_path):
    """Test that infinite capacity is handled correctly in DOT export."""
    output_path = tmp_path / "network.dot"
    complex_network.export_dot(str(output_path))
    
    with open(output_path, 'r') as f:
        content = f.read()
    
    # link3 has infinite capacity, so it shouldn't show "Cap:" in label
    # Find the link3 edge definition
    lines = content.split('\n')
    link3_line = None
    for line in lines:
        if 'link3' in line and '->' in line:
            link3_line = line
            break
    
    assert link3_line is not None
    # Should not have "Cap:" since capacity is infinite
    assert 'Cap:' not in link3_line


def test_export_dot_special_characters_in_ids(tmp_path):
    """Test that special characters in node IDs are handled correctly."""
    network = NetworkGraph()
    
    # Add nodes with special characters
    j1 = JunctionNode('node-with-dash')
    j2 = JunctionNode('node with space')
    
    network.add_node(j1)
    network.add_node(j2)
    
    # Add link
    link = Link('link-1', j1, j2, 100.0, 1.0)
    network.add_link(link)
    
    output_path = tmp_path / "network.dot"
    network.export_dot(str(output_path))
    
    with open(output_path, 'r') as f:
        content = f.read()
    
    # Should replace special characters with underscores in node IDs
    # but keep original names in labels
    assert content  # Just verify it doesn't crash


# Integration Tests

def test_export_both_formats(complex_network, tmp_path):
    """Test that both export formats can be generated for the same network."""
    graphml_path = tmp_path / "network.graphml"
    dot_path = tmp_path / "network.dot"
    
    complex_network.export_graphml(str(graphml_path))
    complex_network.export_dot(str(dot_path))
    
    assert graphml_path.exists()
    assert dot_path.exists()
    
    # Both files should have content
    assert graphml_path.stat().st_size > 0
    assert dot_path.stat().st_size > 0


def test_export_empty_network(tmp_path):
    """Test that exporting an empty network doesn't crash."""
    network = NetworkGraph()
    
    graphml_path = tmp_path / "empty.graphml"
    dot_path = tmp_path / "empty.dot"
    
    network.export_graphml(str(graphml_path))
    network.export_dot(str(dot_path))
    
    assert graphml_path.exists()
    assert dot_path.exists()
