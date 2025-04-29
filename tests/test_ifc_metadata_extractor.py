import pytest
import ifcopenshell
from pathlib import Path
from qto_buccaneer.utils.ifc_metadata_extractor import safe_instances_by_type

@pytest.fixture
def ifc_file():
    """Fixture to provide a test IFC file."""
    test_ifc_path = Path(__file__).parent / "test_model_1.ifc"
    return ifcopenshell.open(str(test_ifc_path))

def test_safe_instances_by_type_with_string(ifc_file):
    """Test safe_instances_by_type with string input."""
    # Test with a valid IFC type
    walls = safe_instances_by_type(ifc_file, "IfcWall")
    assert isinstance(walls, list)
    assert all(isinstance(wall, ifcopenshell.entity_instance) for wall in walls)
    assert all(wall.is_a("IfcWall") for wall in walls)

    # Test with an invalid IFC type
    invalid = safe_instances_by_type(ifc_file, "InvalidType")
    assert isinstance(invalid, list)
    assert len(invalid) == 0

def test_safe_instances_by_type_with_entity_instance(ifc_file):
    """Test safe_instances_by_type with entity instance input."""
    # Get a wall instance first
    walls = ifc_file.by_type("IfcWall")
    if walls:
        wall = walls[0]
        result = safe_instances_by_type(ifc_file, wall)
        assert isinstance(result, list)
        assert all(isinstance(w, ifcopenshell.entity_instance) for w in result)
        assert all(w.is_a("IfcWall") for w in result)

def test_safe_instances_by_type_with_class(ifc_file):
    """Test safe_instances_by_type with class input."""
    # Test with a valid IFC class
    result = safe_instances_by_type(ifc_file, ifcopenshell.entity_instance)
    assert isinstance(result, list)
    assert all(isinstance(w, ifcopenshell.entity_instance) for w in result)

def test_safe_instances_by_type_with_invalid_input(ifc_file):
    """Test safe_instances_by_type with invalid input types."""
    # Test with None
    result = safe_instances_by_type(ifc_file, None)
    assert isinstance(result, list)
    assert len(result) == 0

    # Test with an integer
    result = safe_instances_by_type(ifc_file, 123)
    assert isinstance(result, list)
    assert len(result) == 0

    # Test with a list
    result = safe_instances_by_type(ifc_file, [])
    assert isinstance(result, list)
    assert len(result) == 0 