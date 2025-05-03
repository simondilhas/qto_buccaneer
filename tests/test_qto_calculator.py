import pytest
import os
import sys
from pathlib import Path
from ifcopenshell import open as ifc_open

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.ifc_qto_calculator import QtoCalculator

# Constants - Use absolute paths
TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")

@pytest.fixture
def ifc_model():
    """Load the test IFC model."""
    return ifc_open(TEST_IFC_PATH)

@pytest.fixture
def calculator(ifc_model):
    """Create a QtoCalculator instance with the test IFC model."""
    loader = IfcLoader(ifc_model)
    return QtoCalculator(loader)

def test_get_property_value(calculator):
    """Test getting property values from elements using the test model."""
    # Get a wall from the test model
    walls = calculator.loader.get_elements(ifc_entity="IfcWall")
    assert len(walls) > 0, "No walls found in test model"
    wall = walls[0]
    
    # Test getting a boolean property
    raw_value, float_value = calculator._get_property_value(wall, "Pset_WallCommon", "IsExternal")
    assert raw_value is not None, "IsExternal property not found"
    assert isinstance(raw_value, bool), "IsExternal should be a boolean"
    # Note: In Python, bool is a subclass of int, so True converts to 1.0
    assert float_value == 1.0 if raw_value else 0.0, "Boolean properties should convert to 1.0 or 0.0"
    
    # Test getting a string property
    raw_value, float_value = calculator._get_property_value(wall, "Pset_WallCommon", "Reference")
    assert raw_value is not None, "Reference property not found"
    assert isinstance(raw_value, str), "Reference should be a string"
    assert float_value is None, "String properties should not have float values"
    
    # Test getting a non-existent property
    raw_value, float_value = calculator._get_property_value(wall, "Pset_WallCommon", "NonExistent")
    assert raw_value is None, "Non-existent property should return None"
    assert float_value is None, "Non-existent property should return None for float value"

def test_find_property_or_quantity(calculator):
    """Test finding properties and quantities in elements using the test model."""
    # Get a wall from the test model
    walls = calculator.loader.get_elements(ifc_entity="IfcWall")
    assert len(walls) > 0, "No walls found in test model"
    wall = walls[0]
    
    # Test finding a property
    result = calculator._find_property_or_quantity(wall, "Pset_WallCommon", "IsExternal")
    assert result is not None, "IsExternal property not found"
    
    # Test finding a non-existent property
    result = calculator._find_property_or_quantity(wall, "Pset_WallCommon", "NonExistent")
    assert result is None, "Non-existent property should return None"

def test_get_property_from_set(calculator):
    """Test getting properties from property sets using the test model."""
    # Get a wall from the test model
    walls = calculator.loader.get_elements(ifc_entity="IfcWall")
    assert len(walls) > 0, "No walls found in test model"
    wall = walls[0]
    
    # Get the property set
    pset = None
    for rel in getattr(wall, "IsDefinedBy", []):
        definition = getattr(rel, "RelatingPropertyDefinition", None)
        if definition and definition.is_a("IfcPropertySet") and definition.Name == "Pset_WallCommon":
            pset = definition
            break
    assert pset is not None, "Pset_WallCommon not found"
    
    # Test getting existing property
    result = calculator._get_property_from_set(pset, "IsExternal")
    assert result is not None, "IsExternal property not found"
    
    # Test getting non-existent property
    result = calculator._get_property_from_set(pset, "NonExistent")
    assert result is None, "Non-existent property should return None"

def test_get_quantity_from_set(calculator):
    """Test getting quantities from quantity sets using the test model."""
    # Get a wall from the test model
    walls = calculator.loader.get_elements(ifc_entity="IfcWall")
    assert len(walls) > 0, "No walls found in test model"
    wall = walls[0]
    
    # Get the quantity set
    qto = None
    for rel in getattr(wall, "IsDefinedBy", []):
        definition = getattr(rel, "RelatingPropertyDefinition", None)
        if definition and definition.is_a("IfcElementQuantity"):
            qto = definition
            break
    assert qto is not None, "Quantity set not found"
    
    # Test getting existing quantity
    result = calculator._get_quantity_from_set(qto, "NetSideArea")
    assert result is not None, "NetSideArea quantity not found"
    
    # Test getting non-existent quantity
    result = calculator._get_quantity_from_set(qto, "NonExistent")
    assert result is None, "Non-existent quantity should return None"

def test_try_convert_to_float(calculator):
    """Test converting values to float."""
    # Test valid numeric values
    assert calculator._try_convert_to_float(10) == 10.0
    assert calculator._try_convert_to_float("10.5") == 10.5
    assert calculator._try_convert_to_float(10.5) == 10.5
    
    # Test boolean values (should convert to 1.0 or 0.0)
    assert calculator._try_convert_to_float(True) == 1.0
    assert calculator._try_convert_to_float(False) == 0.0
    
    # Test invalid values
    assert calculator._try_convert_to_float(None) is None
    assert calculator._try_convert_to_float("not a number") is None

def test_compare_numeric(calculator):
    """Test numeric comparisons."""
    # Test greater than
    assert calculator._compare_numeric(10.0, ">", 5.0) is True
    assert calculator._compare_numeric(5.0, ">", 10.0) is False
    
    # Test less than
    assert calculator._compare_numeric(5.0, "<", 10.0) is True
    assert calculator._compare_numeric(10.0, "<", 5.0) is False
    
    # Test equal to
    assert calculator._compare_numeric(10.0, "=", 10.0) is True
    assert calculator._compare_numeric(10.0, "=", 5.0) is False
    
    # Test greater than or equal
    assert calculator._compare_numeric(10.0, ">=", 10.0) is True
    assert calculator._compare_numeric(10.0, ">=", 5.0) is True
    assert calculator._compare_numeric(5.0, ">=", 10.0) is False
    
    # Test less than or equal
    assert calculator._compare_numeric(10.0, "<=", 10.0) is True
    assert calculator._compare_numeric(5.0, "<=", 10.0) is True
    assert calculator._compare_numeric(10.0, "<=", 5.0) is False

def test_check_value_match(calculator):
    """Test value matching logic."""
    # Test direct comparison
    assert calculator._check_value_match(10, 10) is True
    assert calculator._check_value_match(10, 5) is False
    
    # Test numeric comparison
    assert calculator._check_value_match(10, [">", 5]) is True
    assert calculator._check_value_match(5, [">", 10]) is False
    
    # Test list comparison
    assert calculator._check_value_match(10, [5, 10, 15]) is True
    assert calculator._check_value_match(20, [5, 10, 15]) is False
    
    # Test string comparison
    assert calculator._check_value_match("test", "test") is True
    assert calculator._check_value_match("test", "other") is False

def test_apply_filter(calculator):
    """Test filter application using the test model."""
    # Get a wall from the test model
    walls = calculator.loader.get_elements(ifc_entity="IfcWall")
    assert len(walls) > 0, "No walls found in test model"
    wall = walls[0]
    
    # Test AND logic
    assert calculator._apply_filter(
        wall,
        {
            "Pset_WallCommon.IsExternal": True,
            "Pset_WallCommon.Reference": "Wall Exterior"
        },
        "AND"
    ) is True
    
    # Test OR logic
    assert calculator._apply_filter(
        wall,
        {
            "Pset_WallCommon.IsExternal": True,
            "Pset_WallCommon.Reference": "Wall Interior"
        },
        "OR"
    ) is True

def test_get_elements_by_space(calculator):
    """Test getting elements grouped by space with their quantities."""
    # Test window area calculation using the exact config from metrics_config_abstractBIM.yaml
    result = calculator._get_elements_by_space(
        ifc_entity="IfcWindow",
        grouping_pset=None,
        grouping_attribute_or_property="LongName",
        room_reference_attribute_guid="ePset_abstractBIM.Spaces",
        include_filter={"Pset_WindowCommon.IsExternal": True},
        include_filter_logic="AND",
        metric_pset_name="Qto_WindowBaseQuantities",
        metric_prop_name="Area"
    )
    
    print("\nDEBUG INFO - Window Area by Space:")
    print(f"Result: {result}")
    
    # Verify that we got some results
    assert len(result) > 0, "No window areas calculated"
    
    # Verify that all values are positive numbers
    for space_name, area in result.items():
        assert isinstance(area, float), f"Area for space {space_name} is not a float"
        assert area > 0, f"Area for space {space_name} is not positive"

