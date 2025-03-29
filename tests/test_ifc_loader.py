import sys
import os
import pytest
import ifcopenshell

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ifc_loader import IfcProject

@pytest.fixture
def ifc_project():
    """Fixture to create an IfcProject instance"""
    test_file = os.path.join(os.path.dirname(__file__), "Mustermodell V2_abstractBIM.ifc")
    return IfcProject(test_file)

def test_ifc_project_initialization(ifc_project):
    """Test if IfcProject is initialized correctly"""
    assert isinstance(ifc_project, IfcProject)
    assert isinstance(ifc_project.model, ifcopenshell.file)
    assert os.path.exists(ifc_project.file_path)

def test_get_gfa_elements_default_params(ifc_project):
    """Test get_gfa_elements with default parameters"""
    gfa_elements = ifc_project.get_gfa_elements()
    get_gfa_elements
    # Basic checks
    assert isinstance(gfa_elements, list), "Should return a list"
    
    # Check each element if list is not empty
    if gfa_elements:
        for element in gfa_elements:
            assert element.is_a("IfcSpace"), "Each element should be an IfcSpace"
            assert element.Name == "GFA", "Each element should have Name 'GFA'"
            assert hasattr(element, "NetFloorArea"), "Each element should have NetFloorArea property"

def test_get_gfa_elements_custom_params(ifc_project):
    """Test get_gfa_elements with custom parameters"""
    custom_elements = ifc_project.get_gfa_elements(
        ifc_entity="IfcSpace",
        attribute="Name",
        name="CustomName",
        quantity="CustomQuantity"
    )
    assert isinstance(custom_elements, list), "Should return a list with custom parameters"

def test_get_gfa_elements_invalid_entity(ifc_project):
    """Test get_gfa_elements with invalid entity type"""
    with pytest.raises(RuntimeError):
        ifc_project.get_gfa_elements(ifc_entity="NonExistentEntity")

def test_get_gfa_elements_empty_result(ifc_project):
    """Test get_gfa_elements with parameters that should return empty list"""
    elements = ifc_project.get_gfa_elements(name="NonExistentName")
    assert isinstance(elements, list)
    assert len(elements) == 0, "Should return empty list for non-existent name"

if __name__ == "__main__":
    pytest.main(["-v", "-s"])