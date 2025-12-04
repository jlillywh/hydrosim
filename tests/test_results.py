"""
Tests for the results output system.

These tests verify that the ResultsWriter correctly outputs simulation
results in structured formats (CSV and JSON) at daily resolution.
"""

import pytest
import csv
import json
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from hydrosim.results import ResultsWriter
from hydrosim.simulation import SimulationEngine
from hydrosim.climate_engine import ClimateEngine
from hydrosim.climate import ClimateState, SiteConfig
from hydrosim.climate_sources import TimeSeriesClimateSource
from hydrosim.config import NetworkGraph, ElevationAreaVolume
from hydrosim.nodes import StorageNode, SourceNode, DemandNode
from hydrosim.links import Link
from hydrosim.solver import LinearProgrammingSolver
from hydrosim.strategies import TimeSeriesStrategy, MunicipalDemand
import pandas as pd


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for output files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_timestep_result():
    """Create a sample timestep result for testing."""
    return {
        'timestep': 0,
        'date': datetime(2024, 1, 1),
        'climate': ClimateState(
            date=datetime(2024, 1, 1),
            precip=5.0,
            t_max=25.0,
            t_min=15.0,
            solar=20.0,
            et0=4.5
        ),
        'node_states': {
            'source1': {'inflow': 100.0},
            'storage1': {
                'storage': 15000.0,
                'elevation': 110.0,
                'surface_area': 1500.0,
                'evap_loss': 6.75
            },
            'demand1': {
                'request': 80.0,
                'delivered': 80.0,
                'deficit': 0.0
            }
        },
        'flows': {
            'link1': 100.0,
            'link2': 80.0
        }
    }


@pytest.fixture
def simple_network():
    """Create a simple network for integration testing."""
    network = NetworkGraph()
    
    eav = ElevationAreaVolume(
        elevations=[100.0, 110.0, 120.0],
        areas=[1000.0, 1500.0, 2000.0],
        volumes=[0.0, 12500.0, 30000.0]
    )
    
    inflow_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5, freq='D'),
        'inflow': [100.0] * 5
    })
    source = SourceNode('source1', TimeSeriesStrategy(inflow_data, 'inflow'))
    storage = StorageNode('storage1', initial_storage=15000.0, eav_table=eav, max_storage=50000.0, min_storage=0.0)
    demand = DemandNode('demand1', MunicipalDemand(population=400, per_capita_demand=0.2))
    
    network.add_node(source)
    network.add_node(storage)
    network.add_node(demand)
    
    link1 = Link('link1', source, storage, physical_capacity=200.0, cost=1.0)
    link2 = Link('link2', storage, demand, physical_capacity=300.0, cost=1.0)
    
    network.add_link(link1)
    network.add_link(link2)
    
    return network


@pytest.fixture
def climate_engine():
    """Create a climate engine for testing."""
    climate_data = pd.DataFrame({
        'precip': [5.0] * 5,
        't_max': [25.0] * 5,
        't_min': [15.0] * 5,
        'solar': [20.0] * 5
    }, index=pd.date_range('2024-01-01', periods=5, freq='D'))
    
    source = TimeSeriesClimateSource(climate_data)
    site_config = SiteConfig(latitude=40.0, elevation=100.0)
    
    return ClimateEngine(source, site_config, datetime(2024, 1, 1))


def test_results_writer_initialization_csv(temp_output_dir):
    """Test that ResultsWriter can be initialized with CSV format."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    
    assert writer.output_dir == Path(temp_output_dir)
    assert writer.format == 'csv'
    assert writer.results == []


def test_results_writer_initialization_json(temp_output_dir):
    """Test that ResultsWriter can be initialized with JSON format."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='json')
    
    assert writer.output_dir == Path(temp_output_dir)
    assert writer.format == 'json'
    assert writer.results == []


def test_results_writer_invalid_format(temp_output_dir):
    """Test that ResultsWriter rejects invalid formats."""
    with pytest.raises(ValueError, match="Format must be 'csv' or 'json'"):
        ResultsWriter(output_dir=temp_output_dir, format='xml')


def test_results_writer_creates_output_directory(temp_output_dir):
    """Test that ResultsWriter creates output directory if it doesn't exist."""
    new_dir = Path(temp_output_dir) / "subdir" / "output"
    writer = ResultsWriter(output_dir=str(new_dir), format='csv')
    
    assert new_dir.exists()
    assert new_dir.is_dir()


def test_add_timestep(temp_output_dir, sample_timestep_result):
    """Test that timestep results can be added."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    
    writer.add_timestep(sample_timestep_result)
    
    assert len(writer.results) == 1
    assert writer.results[0] == sample_timestep_result


def test_add_multiple_timesteps(temp_output_dir, sample_timestep_result):
    """Test that multiple timestep results can be added."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    
    # Add 3 timesteps
    for i in range(3):
        result = sample_timestep_result.copy()
        result['timestep'] = i
        writer.add_timestep(result)
    
    assert len(writer.results) == 3
    assert writer.results[0]['timestep'] == 0
    assert writer.results[1]['timestep'] == 1
    assert writer.results[2]['timestep'] == 2


def test_write_flows_csv(temp_output_dir, sample_timestep_result):
    """Test that flow data is written correctly to CSV."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    writer.add_timestep(sample_timestep_result)
    
    files = writer.write_all(prefix='test')
    
    # Verify file was created
    assert 'flows' in files
    flows_file = Path(files['flows'])
    assert flows_file.exists()
    
    # Read and verify contents
    with open(flows_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Should have 2 rows (link1 and link2)
    assert len(rows) == 2
    
    # Verify headers
    assert set(rows[0].keys()) == {'timestep', 'date', 'link_id', 'flow'}
    
    # Verify data
    link1_row = next(r for r in rows if r['link_id'] == 'link1')
    assert link1_row['timestep'] == '0'
    assert link1_row['date'] == '2024-01-01'
    assert float(link1_row['flow']) == 100.0
    
    link2_row = next(r for r in rows if r['link_id'] == 'link2')
    assert float(link2_row['flow']) == 80.0


def test_write_storage_csv(temp_output_dir, sample_timestep_result):
    """Test that storage node data is written correctly to CSV."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    writer.add_timestep(sample_timestep_result)
    
    files = writer.write_all(prefix='test')
    
    # Verify file was created
    assert 'storage' in files
    storage_file = Path(files['storage'])
    assert storage_file.exists()
    
    # Read and verify contents
    with open(storage_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Should have 1 row (storage1)
    assert len(rows) == 1
    
    # Verify headers
    expected_headers = {'timestep', 'date', 'node_id', 'storage', 
                       'elevation', 'surface_area', 'evap_loss'}
    assert set(rows[0].keys()) == expected_headers
    
    # Verify data
    row = rows[0]
    assert row['node_id'] == 'storage1'
    assert float(row['storage']) == 15000.0
    assert float(row['elevation']) == 110.0
    assert float(row['surface_area']) == 1500.0
    assert float(row['evap_loss']) == 6.75


def test_write_demands_csv(temp_output_dir, sample_timestep_result):
    """Test that demand node data is written correctly to CSV."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    writer.add_timestep(sample_timestep_result)
    
    files = writer.write_all(prefix='test')
    
    # Verify file was created
    assert 'demands' in files
    demands_file = Path(files['demands'])
    assert demands_file.exists()
    
    # Read and verify contents
    with open(demands_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Should have 1 row (demand1)
    assert len(rows) == 1
    
    # Verify headers
    expected_headers = {'timestep', 'date', 'node_id', 'request', 
                       'delivered', 'deficit'}
    assert set(rows[0].keys()) == expected_headers
    
    # Verify data
    row = rows[0]
    assert row['node_id'] == 'demand1'
    assert float(row['request']) == 80.0
    assert float(row['delivered']) == 80.0
    assert float(row['deficit']) == 0.0


def test_write_sources_csv(temp_output_dir, sample_timestep_result):
    """Test that source node data is written correctly to CSV."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    writer.add_timestep(sample_timestep_result)
    
    files = writer.write_all(prefix='test')
    
    # Verify file was created
    assert 'sources' in files
    sources_file = Path(files['sources'])
    assert sources_file.exists()
    
    # Read and verify contents
    with open(sources_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Should have 1 row (source1)
    assert len(rows) == 1
    
    # Verify headers
    expected_headers = {'timestep', 'date', 'node_id', 'inflow'}
    assert set(rows[0].keys()) == expected_headers
    
    # Verify data
    row = rows[0]
    assert row['node_id'] == 'source1'
    assert float(row['inflow']) == 100.0


def test_write_json(temp_output_dir, sample_timestep_result):
    """Test that all data is written correctly to JSON."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='json')
    writer.add_timestep(sample_timestep_result)
    
    files = writer.write_all(prefix='test')
    
    # Verify file was created
    assert 'all' in files
    json_file = Path(files['all'])
    assert json_file.exists()
    
    # Read and verify contents
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Should have 1 timestep
    assert len(data) == 1
    
    # Verify structure
    result = data[0]
    assert result['timestep'] == 0
    assert result['date'] == '2024-01-01'
    assert 'flows' in result
    assert 'node_states' in result
    
    # Verify flows
    assert result['flows']['link1'] == 100.0
    assert result['flows']['link2'] == 80.0
    
    # Verify node states
    assert result['node_states']['source1']['inflow'] == 100.0
    assert result['node_states']['storage1']['storage'] == 15000.0
    assert result['node_states']['demand1']['deficit'] == 0.0


def test_daily_resolution_output(temp_output_dir):
    """Test that output is at daily resolution."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    
    # Add results for 3 consecutive days
    for i in range(3):
        result = {
            'timestep': i,
            'date': datetime(2024, 1, 1 + i),
            'node_states': {'source1': {'inflow': 100.0}},
            'flows': {'link1': 100.0}
        }
        writer.add_timestep(result)
    
    files = writer.write_all(prefix='test')
    
    # Read flows file
    with open(files['flows'], 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Verify daily dates
    assert rows[0]['date'] == '2024-01-01'
    assert rows[1]['date'] == '2024-01-02'
    assert rows[2]['date'] == '2024-01-03'


def test_output_completeness(temp_output_dir, sample_timestep_result):
    """Test that output includes all required data types."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    writer.add_timestep(sample_timestep_result)
    
    files = writer.write_all(prefix='test')
    
    # Verify all file types were created
    assert 'flows' in files
    assert 'storage' in files
    assert 'demands' in files
    assert 'sources' in files
    
    # Verify all files exist
    assert Path(files['flows']).exists()
    assert Path(files['storage']).exists()
    assert Path(files['demands']).exists()
    assert Path(files['sources']).exists()


def test_clear_results(temp_output_dir, sample_timestep_result):
    """Test that results can be cleared."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    writer.add_timestep(sample_timestep_result)
    
    assert len(writer.results) == 1
    
    writer.clear()
    
    assert len(writer.results) == 0


def test_get_results(temp_output_dir, sample_timestep_result):
    """Test that accumulated results can be retrieved."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    writer.add_timestep(sample_timestep_result)
    
    results = writer.get_results()
    
    assert len(results) == 1
    assert results[0] == sample_timestep_result


def test_write_all_with_no_results(temp_output_dir):
    """Test that write_all handles empty results gracefully."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    
    files = writer.write_all(prefix='test')
    
    # Should return empty dict
    assert files == {}


def test_integration_with_simulation(simple_network, climate_engine, temp_output_dir):
    """Test ResultsWriter integration with SimulationEngine."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    
    # Run simulation and collect results
    for _ in range(5):
        result = engine.step()
        writer.add_timestep(result)
    
    # Write results
    files = writer.write_all(prefix='simulation')
    
    # Verify all files were created
    assert Path(files['flows']).exists()
    assert Path(files['storage']).exists()
    assert Path(files['demands']).exists()
    assert Path(files['sources']).exists()
    
    # Verify flows file has correct number of rows (5 timesteps * 2 links)
    with open(files['flows'], 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 10  # 5 timesteps * 2 links
    
    # Verify storage file has correct number of rows (5 timesteps * 1 storage)
    with open(files['storage'], 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 5


def test_multiple_storage_nodes(temp_output_dir):
    """Test that multiple storage nodes are all written to output."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    
    result = {
        'timestep': 0,
        'date': datetime(2024, 1, 1),
        'node_states': {
            'storage1': {
                'storage': 15000.0,
                'elevation': 110.0,
                'surface_area': 1500.0,
                'evap_loss': 6.75
            },
            'storage2': {
                'storage': 20000.0,
                'elevation': 115.0,
                'surface_area': 1800.0,
                'evap_loss': 8.1
            }
        },
        'flows': {}
    }
    
    writer.add_timestep(result)
    files = writer.write_all(prefix='test')
    
    # Read storage file
    with open(files['storage'], 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Should have 2 rows
    assert len(rows) == 2
    
    # Verify both storage nodes are present
    node_ids = {row['node_id'] for row in rows}
    assert node_ids == {'storage1', 'storage2'}


def test_multiple_demand_nodes(temp_output_dir):
    """Test that multiple demand nodes are all written to output."""
    writer = ResultsWriter(output_dir=temp_output_dir, format='csv')
    
    result = {
        'timestep': 0,
        'date': datetime(2024, 1, 1),
        'node_states': {
            'demand1': {
                'request': 80.0,
                'delivered': 80.0,
                'deficit': 0.0
            },
            'demand2': {
                'request': 50.0,
                'delivered': 40.0,
                'deficit': 10.0
            }
        },
        'flows': {}
    }
    
    writer.add_timestep(result)
    files = writer.write_all(prefix='test')
    
    # Read demands file
    with open(files['demands'], 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Should have 2 rows
    assert len(rows) == 2
    
    # Verify both demand nodes are present
    node_ids = {row['node_id'] for row in rows}
    assert node_ids == {'demand1', 'demand2'}


def test_json_format_integration(simple_network, climate_engine, temp_output_dir):
    """Test JSON format with full simulation."""
    solver = LinearProgrammingSolver()
    engine = SimulationEngine(simple_network, climate_engine, solver)
    writer = ResultsWriter(output_dir=temp_output_dir, format='json')
    
    # Run simulation and collect results
    for _ in range(3):
        result = engine.step()
        writer.add_timestep(result)
    
    # Write results
    files = writer.write_all(prefix='simulation')
    
    # Verify JSON file was created
    assert 'all' in files
    json_file = Path(files['all'])
    assert json_file.exists()
    
    # Read and verify JSON structure
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Should have 3 timesteps
    assert len(data) == 3
    
    # Verify each timestep has required structure
    for i, timestep_data in enumerate(data):
        assert timestep_data['timestep'] == i
        assert 'date' in timestep_data
        assert 'flows' in timestep_data
        assert 'node_states' in timestep_data
        
        # Verify flows
        assert 'link1' in timestep_data['flows']
        assert 'link2' in timestep_data['flows']
        
        # Verify node states
        assert 'source1' in timestep_data['node_states']
        assert 'storage1' in timestep_data['node_states']
        assert 'demand1' in timestep_data['node_states']
