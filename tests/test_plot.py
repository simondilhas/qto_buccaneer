import os
import tempfile
import shutil
from pathlib import Path
import pytest
import yaml
import json

from qto_buccaneer.plots import create_all_plots

@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    return Path(__file__).parent / "test_data"

@pytest.fixture
def geometry_dir(test_data_dir):
    """Return the path to the geometry test data directory."""
    return test_data_dir / "geometry"

@pytest.fixture
def properties_path(test_data_dir):
    """Create a temporary properties file with test data."""
    properties = {
        "elements": {
            "182": {
                "type": "IfcSpace",
                "properties": {
                    "Name": "Test Space",
                    "Description": "Test Description",
                    "LongName": "Test Space Long Name"
                },
                "storey_id": "5"
            },
            "2": {
                "type": "IfcDoor",
                "properties": {
                    "Name": "Test Door",
                    "Description": "Test Description"
                },
                "storey_id": "5"
            },
            "3": {
                "type": "IfcWindow",
                "properties": {
                    "Name": "Test Window",
                    "Description": "Test Description"
                },
                "storey_id": "5"
            },
            "5": {
                "type": "IfcBuildingStorey",
                "name": "Ground Floor",
                "properties": {
                    "Description": "Test Description"
                }
            }
        },
        "indexes": {
            "by_type": {
                "IfcSpace": ["182"],
                "IfcDoor": ["2"],
                "IfcWindow": ["3"],
                "IfcBuildingStorey": ["5"]
            }
        },
        "global_id_to_id": {
            "1QkKxMqDv7nuSnClC0HTpb": "182",
            "2": "2",
            "3": "3",
            "5": "5"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(properties, f)
        return f.name

@pytest.fixture
def config_path(test_data_dir):
    """Create a temporary config file with test plot configurations."""
    config = {
        "plot_settings": {
            "defaults": {
                "title": "Default Plot Title",
                "font_family": "Arial",
                "title_size": 24,
                "text_size": 12,
                "legend_size": 14,
                "show_legend": False,
                "background_color": "white",
                "margin": {
                    "left": 50,
                    "right": 50,
                    "top": 50,
                    "bottom": 50
                }
            },
            "modes": {
                "3d_view": {
                    "type": "3d",
                    "opacity": 1.0,
                    "line_color": "black",
                    "line_width": 0.8,
                    "view_angle": {
                        "x": 1.5,
                        "y": 1.5,
                        "z": 1.5
                    },
                    "scene": {
                        "xaxis": {
                            "visible": False,
                            "showgrid": False,
                            "zeroline": False,
                            "showticklabels": False,
                            "showline": False,
                            "showbackground": False,
                            "showspikes": False,
                            "gridcolor": "rgba(0,0,0,0)",
                            "zerolinecolor": "rgba(0,0,0,0)",
                            "linecolor": "rgba(0,0,0,0)"
                        },
                        "yaxis": {
                            "visible": False,
                            "showgrid": False,
                            "zeroline": False,
                            "showticklabels": False,
                            "showline": False,
                            "showbackground": False,
                            "showspikes": False,
                            "gridcolor": "rgba(0,0,0,0)",
                            "zerolinecolor": "rgba(0,0,0,0)",
                            "linecolor": "rgba(0,0,0,0)"
                        },
                        "zaxis": {
                            "visible": False,
                            "showgrid": False,
                            "zeroline": False,
                            "showticklabels": False,
                            "showline": False,
                            "showbackground": False,
                            "showspikes": False,
                            "gridcolor": "rgba(0,0,0,0)",
                            "zerolinecolor": "rgba(0,0,0,0)",
                            "linecolor": "rgba(0,0,0,0)"
                        },
                        "camera": {
                            "up": {"x": 0, "y": 0, "z": 1},
                            "center": {"x": 0, "y": 0, "z": 0},
                            "eye": {"x": 1.5, "y": 1.5, "z": 1.5}
                        },
                        "aspectmode": "data",
                        "bgcolor": "rgba(0,0,0,0)"
                    }
                },
                "floor_plan": {
                    "type": "2d",
                    "opacity": 0.8,
                    "line_color": "gray",
                    "line_width": 0.5,
                    "view": "top"
                }
            }
        },
        "plots": {
            "test_floorplan": {
                "mode": "floor_plan",
                "title": "Test Floor Plan",
                "description": "A test floor plan visualization",
                "elements": [
                    {
                        "name": "Spaces",
                        "filter": "type=IfcSpace",
                        "color": "lightblue",
                        "label": "LongName"
                    },
                    {
                        "name": "Doors",
                        "filter": "type=IfcDoor",
                        "color": "black",
                        "label": "none"
                    },
                    {
                        "name": "Windows",
                        "filter": "type=IfcWindow",
                        "color": "lightgray",
                        "label": "none"
                    }
                ]
            },
            "test_3d": {
                "mode": "3d_view",
                "title": "Test 3D Visualization",
                "description": "A test 3D visualization",
                "elements": [
                    {
                        "name": "Windows",
                        "filter": "type=IfcWindow",
                        "color": "lightgray",
                        "label": "none"
                    },
                    {
                        "name": "Doors",
                        "filter": "type=IfcDoor",
                        "color": "black",
                        "label": "none"
                    },
                    {
                        "name": "Slabs",
                        "filter": "type=IfcSlab",
                        "color": "lightblue",
                        "label": "none"
                    },
                    {
                        "name": "Coverings",
                        "filter": "type=IfcCovering",
                        "color": "lightgreen",
                        "label": "none"
                    }
                ]
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        return f.name

@pytest.fixture
def output_dir():
    """Create a temporary output directory for test results."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)

class TestPlots:
    """Test class for plots functionality."""
    
    def test_create_all_plots(self, geometry_dir, properties_path, config_path, output_dir):
        """Test creating all plots from configuration."""
        # Create all plots
        output_paths = create_all_plots(
            geometry_dir=str(geometry_dir),
            properties_path=properties_path,
            config_path=config_path,
            output_dir=output_dir
        )
        
        # Verify output directory exists
        assert os.path.exists(output_dir)
        
        # Verify output files were created
        expected_files = [
            "test_floorplan_Ground Floor.html",  # Floor plan output with storey name
            "test_3d.html"                       # 3D visualization output
        ]
        
        for file in expected_files:
            file_path = os.path.join(output_dir, file)
            assert os.path.exists(file_path), f"Expected output file {file} not found"

    def test_create_specific_plots(self, geometry_dir, properties_path, config_path, output_dir):
        """Test creating specific plots by name."""
        # Create only the floor plan plot
        output_paths = create_all_plots(
            geometry_dir=str(geometry_dir),
            properties_path=properties_path,
            config_path=config_path,
            output_dir=output_dir,
            plot_names=["test_floorplan"]
        )
        
        # Verify only floor plan was created
        assert os.path.exists(os.path.join(output_dir, "test_floorplan_Ground Floor.html"))

    def test_invalid_plot_name(self, geometry_dir, properties_path, config_path, output_dir):
        """Test behavior with invalid plot name."""
        # Try to create non-existent plot
        output_paths = create_all_plots(
            geometry_dir=str(geometry_dir),
            config_path=config_path,
            properties_path=properties_path,
            output_dir=output_dir,
            plot_names=["non_existent_plot"]
        )
        
        # Verify no output files were created
        assert len(os.listdir(output_dir)) == 0
