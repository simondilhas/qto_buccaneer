import pytest
import yaml
import numpy as np
from pathlib import Path
import pandas as pd
import os
from qto_buccaneer.metrics import (
    calculate_single_metric,
    calculate_single_metric_by_space,
    calculate_single_grouped_metric,
    calculate_all_metrics,
    calculate_single_derived_metric,
)
import ifcopenshell  # Add this import for verification

# Constants - Use absolute paths
TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")
TEST_DATA_PATH = str(TEST_DIR / "test_data.yaml")

# Print debug info at module level
print(f"\nDEBUG: Test directory is {TEST_DIR}")
print(f"DEBUG: Looking for IFC file at {TEST_IFC_PATH}")
print(f"DEBUG: Current working directory is {os.getcwd()}")

@pytest.fixture
def test_config():
    """Basic test configuration for metrics"""
    return {
        "metrics": {
            "gross_floor_area": {
                "description": "Total floor area",
                "quantity_type": "area",
                "ifc_entity": "IfcSpace",
                "pset_name": "Qto_SpaceBaseQuantities",
                "prop_name": "NetFloorArea"
            },
            "window_count": {
                "description": "Total number of windows",
                "quantity_type": "count",
                "ifc_entity": "IfcWindow"
            },
            "doors_exterior_area": {
                "description": "The total area of exterior doors",
                "quantity_type": "area",
                "ifc_entity": "IfcDoor",
                "pset_name": "Qto_DoorBaseQuantities",
                "prop_name": "Area",
                "include_filter": {
                    "Pset_DoorCommon.IsExternal": True
                },
                "include_filter_logic": "AND"
            },
            "walls_interior_non_loadbearing_net_side_area": {
                "description": "The total area of internal non-load bearing walls",
                "quantity_type": "area",
                "ifc_entity": "IfcWallStandardCase",
                "pset_name": "Qto_WallBaseQuantities",
                "prop_name": "NetSideArea",
                "include_filter": {
                    "Pset_WallCommon.IsExternal": False,
                    "Qto_WallBaseQuantities.Width": ["<=", 0.15]
                },
                "include_filter_logic": "AND"
            }
        },
        "room_based_metrics": {
            "net_area_by_room": {
                "description": "Net area per room",
                "quantity_type": "area",
                "ifc_entity": "IfcSpace",
                "grouping_attribute": "LongName",
                "pset_name": "Qto_SpaceBaseQuantities",
                "prop_name": "NetFloorArea"
            },
            "window_area_per_space": {
                "description": "Window area per space",
                "quantity_type": "area",
                "ifc_entity": "IfcWindow",
                "grouping_attribute": "GlobalId",
                "room_reference_attribute_guid": "ePset_abstractBIM.Spaces",
                "pset_name": "Qto_WindowBaseQuantities",
                "prop_name": "Area"
            }
        },
        "grouped_by_attribute_metrics": {
            "window_area_by_direction": {
                "description": "Window area by orientation",
                "quantity_type": "area",
                "ifc_entity": "IfcWindow",
                "grouping_attribute": "Pset_abstractBIM.Normal",
                "pset_name": "Qto_WindowBaseQuantities",
                "prop_name": "Area"
            }   
        },
        "derived_metrics": {
            "window_area_per_gross_floor_area": {
                "description": "Window area per gross floor area",
                "formula": "window_area_by_direction_180 / gross_floor_area"
            }
        }
    }

@pytest.fixture
def test_data():
    """Load test data from YAML file"""
    with open(TEST_DATA_PATH, 'r') as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="module")
def ifc_file():
    """Fixture to verify and provide IFC file access"""
    print(f"\nVerifying IFC file before tests:")
    print(f"File exists: {os.path.exists(TEST_IFC_PATH)}")
    try:
        ifc = ifcopenshell.open(TEST_IFC_PATH)
        print(f"Successfully opened IFC file with {len(ifc.by_type('IfcSpace'))} spaces")
        return ifc
    except Exception as e:
        print(f"Error opening file: {e}")
        raise

# tests for single value calculations

def test_calculate_gross_floor_area(test_config, test_data, ifc_file):
    """Test calculation of gross floor area metric"""
    result = calculate_single_metric(
        ifc_path=TEST_IFC_PATH,
        config=test_config,
        metric_name="gross_floor_area",
        file_info={"test": "test_single_metric"}
    )

    print("\nDEBUG INFO - Gross Floor Area:")
    print(f"Result DataFrame:\n{result}")
    print(f"Expected value: {test_data['metrics']['gross_floor_area']}")
    print(f"Actual value: {result['value'].iloc[0]}")
    print(f"Status: {result['status'].iloc[0]}")
    print(f"Unit: {result['unit'].iloc[0]}")
    
    assert result['status'].iloc[0] == "success", f"Error in calculation: {result['status'].iloc[0]}"
    assert np.isclose(result['value'].iloc[0], test_data['metrics']['gross_floor_area'], rtol=1e-7), \
        f"Expected {test_data['metrics']['gross_floor_area']}, got {result['value'].iloc[0]}"
    assert result['unit'].iloc[0] == "m²"

def test_calculate_window_count(test_config, test_data, ifc_file):
    """Test calculation of window count metric"""
    result = calculate_single_metric(
        ifc_path=TEST_IFC_PATH,
        config=test_config,
        metric_name="window_count",
        file_info={"test": "test_single_metric"}
    )
    
    print("\nDEBUG INFO - Window Count:")
    print(f"Result DataFrame:\n{result}")
    print(f"Expected value: {test_data['metrics']['window_count']}")
    print(f"Actual value: {result['value'].iloc[0]}")
    print(f"Status: {result['status'].iloc[0]}")
    
    assert result['status'].iloc[0] == "success", f"Error in calculation: {result['status'].iloc[0]}"
    assert result['value'].iloc[0] == test_data['metrics']['window_count']
    assert result['unit'].iloc[0] == "count"

def test_calculate_doors_exterior_area(test_config, test_data, ifc_file):
    """Test calculation of exterior door area metric"""
    result = calculate_single_metric(
        ifc_path=TEST_IFC_PATH,
        config=test_config,
        metric_name="doors_exterior_area",
        file_info={"test": "test_single_metric"}
    )
    
    print("\nDEBUG INFO - Exterior Door Area:")
    print(f"Result DataFrame:\n{result}")
    print(f"Expected value: {test_data['metrics']['doors_exterior_area']}")
    print(f"Actual value: {result['value'].iloc[0]}")
    print(f"Status: {result['status'].iloc[0]}")
    
    assert result['status'].iloc[0] == "success", f"Error in calculation: {result['status'].iloc[0]}"
    assert result['value'].iloc[0] == test_data['metrics']['doors_exterior_area']
    assert result['unit'].iloc[0] == "m²"

def test_calculate_interior_non_loadbearing_walls(test_config, test_data, ifc_file):
    """Test calculation of interior non-load bearing walls area metric"""
    result = calculate_single_metric(
        ifc_path=TEST_IFC_PATH,
        config=test_config,
        metric_name="walls_interior_non_loadbearing_net_side_area",
        file_info={"test": "test_single_metric"}
    )
    
    print("\nDEBUG INFO - Interior Non-Load Bearing Walls:")
    print(f"Result DataFrame:\n{result}")
    print(f"Expected value: {test_data['metrics']['walls_interior_non_loadbearing_net_side_area']}")
    print(f"Actual value: {result['value'].iloc[0]}")
    print(f"Status: {result['status'].iloc[0]}")
    
    # First check if calculation was successful
    assert result['status'].iloc[0] == "success", f"Error in calculation: {result['status'].iloc[0]}"
    
    # Check the value matches expected
    assert np.isclose(
        result['value'].iloc[0], 
        test_data['metrics']['walls_interior_non_loadbearing_net_side_area'],
        rtol=1e-7
    ), f"Expected {test_data['metrics']['walls_interior_non_loadbearing_net_side_area']}, got {result['value'].iloc[0]}"
    
    # Check unit is correct
    assert result['unit'].iloc[0] == "m²"


# Tests for grouped by space calculations

def test_window_area_by_direction(test_config, test_data):
    """Test calculation of metrics grouped by attribute"""
    result = calculate_single_grouped_metric(
        ifc_path=TEST_IFC_PATH,
        config=test_config,
        metric_name="window_area_by_direction",
        file_info={"test": "test_grouped_metric"}
    )
    
    print("\nDEBUG INFO - Window Area by Direction:")
    print(f"Result DataFrame:\n{result}")
    print(f"Expected values from test_data:\n{test_data['grouped_metrics']['window_area_by_direction']}")
    
    # Print each direction's result
    for direction, expected_area in test_data['grouped_metrics']['window_area_by_direction'].items():
        direction_result = result[result['metric_name'] == f"window_area_by_direction_{direction.lower()}"]
        print(f"\nDirection {direction}:")
        print(f"Expected area: {expected_area}")
        if not direction_result.empty:
            print(f"Actual area: {direction_result['value'].iloc[0]}")
            print(f"Status: {direction_result['status'].iloc[0]}")
            print(f"Unit: {direction_result['unit'].iloc[0]}")
        else:
            print("No result found for this direction")
    
    assert all(result['status'] == "success"), f"Error in calculation: {result[result['status'] != 'success']['status'].iloc[0]}"
    
    # Check window area for each direction
    for direction, expected_area in test_data['grouped_metrics']['window_area_by_direction'].items():
        direction_result = result[result['metric_name'] == f"window_area_by_direction_{direction.lower()}"]
        assert not direction_result.empty, f"No result found for direction {direction}"
        assert direction_result['value'].iloc[0] == expected_area
        assert direction_result['unit'].iloc[0] == "m²"

def test_window_area_per_gross_floor_area(test_config, test_data):
    """Test calculation of window area per gross floor area"""
    # Create DataFrame with both required metrics
    df_metrics = pd.DataFrame([
        {
            'metric_name': 'window_area_by_direction_180',
            'value': test_data['grouped_metrics']['window_area_by_direction']['180'],
            'unit': 'm²'
        },
        {
            'metric_name': 'gross_floor_area',
            'value': test_data['metrics']['gross_floor_area'],
            'unit': 'm²'
        }
    ])

    result = calculate_single_derived_metric(
        unit="ratio",
        formula="window_area_by_direction_180 / gross_floor_area",
        df_metrics=df_metrics,
        metric_name="window_area_per_gross_floor_area",
        file_info={"test": "test_derived_metric"}
    )
    
    print("\nDEBUG INFO - Window Area per Gross Floor Area:")
    print(f"Input DataFrame:\n{df_metrics}")
    print(f"Result DataFrame:\n{result}")
    print(f"Expected value: {test_data['derived_metrics']['window_area_per_gross_floor_area']}")
    print(f"Actual value: {result['value'].iloc[0]}")
    print(f"Status: {result['status'].iloc[0]}")
    print(f"Unit: {result['unit'].iloc[0]}")
    
    # Assertions
    assert result['status'].iloc[0] == "success", f"Error in calculation: {result['status'].iloc[0]}"
    assert np.isclose(
        result['value'].iloc[0], 
        test_data['derived_metrics']['window_area_per_gross_floor_area'],
        rtol=1e-7
    ), f"Expected {test_data['derived_metrics']['window_area_per_gross_floor_area']}, got {result['value'].iloc[0]}"
    assert result['unit'].iloc[0] == "ratio"

def test_window_area_per_space(test_config, test_data):
    """Test calculation of window area per space"""
    result = calculate_single_metric_by_space(
        ifc_path=TEST_IFC_PATH,
        config=test_config,
        metric_name="window_area_per_space",
        file_info={"test": "test_grouped_metric"}
    )

    print("\nDEBUG INFO - Window Area per Space:")
    print(f"Result DataFrame:\n{result}")
    
    # Check each room's window area
    for room_name, expected_area in test_data['room_metrics']['window_area_per_space'].items():
        room_result = result[result['metric_name'] == f"window_area_per_space_by_longname_{room_name.lower()}"]
        print(f"\nRoom {room_name}:")
        print(f"Expected area: {expected_area}")
        if not room_result.empty:
            print(f"Actual area: {room_result['value'].iloc[0]}")
            print(f"Status: {room_result['status'].iloc[0]}")
            print(f"Unit: {room_result['unit'].iloc[0]}")
        else:
            print("No result found for this room")
    
    assert all(result['status'] == "success"), f"Error in calculation: {result[result['status'] != 'success']['status'].iloc[0]}"
    
    # Check window area for each room
    for room_name, expected_area in test_data['room_metrics']['window_area_per_space'].items():
        room_result = result[result['metric_name'] == f"window_area_per_space_by_longname_{room_name}"]
        assert not room_result.empty, f"No result found for room {room_name}"
        assert np.isclose(room_result['value'].iloc[0], expected_area, rtol=1e-7), \
            f"Expected {expected_area}, got {room_result['value'].iloc[0]}"
        assert room_result['unit'].iloc[0] == "m²"

def test_calculate_all_metrics(test_config, test_data):
    """Test calculation of all metrics"""
    result = calculate_all_metrics(
        config=test_config,
        ifc_path=TEST_IFC_PATH,
        file_info={"test": "test_all_metrics"}
    )
    
    print("\nDEBUG INFO - Calculate All Metrics:")
    print(f"Result DataFrame:\n{result}")
    print(f"Status counts:\n{result['status'].value_counts()}")
    
    assert not result.empty, "No results returned"
    
    # Check if all expected metrics are present
    expected_metrics = (
        list(test_config['metrics'].keys()) +
        [f"window_area_by_direction_{dir.lower()}" for dir in test_data['grouped_metrics']['window_area_by_direction'].keys()] +
        list(test_config['derived_metrics'].keys())
    )
    
    # Only include room metrics if they exist in test_data
    if test_data['room_metrics']['net_area_by_room']:
        expected_metrics.extend(
            [f"net_area_by_room_by_longname_{room.lower()}" 
             for room in test_data['room_metrics']['net_area_by_room'].keys()]
        )
    
    print(f"\nExpected metrics: {expected_metrics}")
    print(f"Actual metrics: {result['metric_name'].unique()}")
    
    for metric in expected_metrics:
        assert any(result['metric_name'] == metric), f"Missing metric: {metric}"
    
    # Check that all non-room metrics are successful
    non_room_metrics = result[~result['metric_name'].str.contains('net_area_by_room')]
    assert all(non_room_metrics['status'] == "success"), \
        f"Errors in calculation: {non_room_metrics[non_room_metrics['status'] != 'success']['status'].values}"
