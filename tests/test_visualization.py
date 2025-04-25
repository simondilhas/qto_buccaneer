import pytest
import json
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go

from qto_buccaneer.plots_utils import (
    load_plot_config,
    create_single_plot,
    create_all_plots
)

def test_load_plot_config():
    """Test loading plot configuration from YAML file."""
    config_path = Path("src/qto_buccaneer/configs/plot_config.yaml")
    config = load_plot_config(config_path)
    
    assert config is not None
    assert 'plot_settings' in config
    assert 'plots' in config
    assert 'covering_visualization' in config['plots']
    
    # Check covering visualization settings
    covering_config = config['plots']['covering_visualization']
    assert covering_config['type'] == '3d'
    assert covering_config['title'] == 'External Coverings'
    assert 'include' in covering_config
    assert len(covering_config['include']) == 1
    
    # Check element configuration
    element_config = covering_config['include'][0]
    assert element_config['type'] == 'elements'
    assert element_config['filter']['types'] == ['IfcCovering']
    assert element_config['filter']['predefined_types'] == ['EXTERNAL']
    assert element_config['show_text'] is True

def test_create_single_plot():
    """Test creating a single plot for coverings."""
    # Load test data
    data_dir = Path("examples/ifc_json_data")
    geometry_path = data_dir / "geometry/IfcCovering_geometry.json"
    properties_path = data_dir / "metadata/test_metadata.json"
    config_path = Path("src/qto_buccaneer/configs/plot_config.yaml")
    
    with open(geometry_path, 'r') as f:
        geometry_data = json.load(f)
    with open(properties_path, 'r') as f:
        properties_data = json.load(f)
    
    config = load_plot_config(config_path)
    file_info = {
        "file_name": "test_file",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Create plot
    fig = create_single_plot(
        geometry_json=geometry_data,
        properties_json=properties_data,
        config=config,
        plot_name="covering_visualization",
        file_info=file_info
    )
    
    # Check plot properties
    assert fig is not None
    assert fig.layout.title.text.startswith("External Coverings")
    assert len(fig.data) > 0  # Should have at least one trace
    
    # Check that we have mesh traces for the coverings
    mesh_traces = [trace for trace in fig.data if isinstance(trace, go.Mesh3d)]
    assert len(mesh_traces) > 0
    
    # Check that the traces have the correct properties
    for trace in mesh_traces:
        assert trace.opacity == config['plot_settings']['covering']['opacity']
        assert trace.showlegend is True
        assert trace.color in [
            config['plot_settings']['covering']['color_map']['default'],
            config['plot_settings']['covering']['color_map']['predefined_types']['EXTERNAL']
        ]

def test_create_all_plots():
    """Test creating all plots defined in the configuration."""
    # Load test data
    data_dir = Path("examples/ifc_json_data")
    geometry_path = data_dir / "geometry/IfcCovering_geometry.json"
    properties_path = data_dir / "metadata/test_metadata.json"
    config_path = Path("src/qto_buccaneer/configs/plot_config.yaml")
    
    with open(geometry_path, 'r') as f:
        geometry_data = json.load(f)
    with open(properties_path, 'r') as f:
        properties_data = json.load(f)
    
    config = load_plot_config(config_path)
    file_info = {
        "file_name": "test_file",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Create all plots
    plots = create_all_plots(
        geometry_json=geometry_data,
        properties_json=properties_data,
        config=config,
        file_info=file_info
    )
    
    # Check that we got the expected plots
    assert 'covering_visualization' in plots
    assert len(plots) == 1  # Currently only one plot type
    
    # Check the covering visualization plot
    fig = plots['covering_visualization']
    assert fig is not None
    assert fig.layout.title.text.startswith("External Coverings")
    assert len(fig.data) > 0
    
    # Check that we have mesh traces for the coverings
    mesh_traces = [trace for trace in fig.data if isinstance(trace, go.Mesh3d)]
    assert len(mesh_traces) > 0
    
    # Check that the traces have the correct properties
    for trace in mesh_traces:
        assert trace.opacity == config['plot_settings']['covering']['opacity']
        assert trace.showlegend is True
        assert trace.color in [
            config['plot_settings']['covering']['color_map']['default'],
            config['plot_settings']['covering']['color_map']['predefined_types']['EXTERNAL']
        ]
 