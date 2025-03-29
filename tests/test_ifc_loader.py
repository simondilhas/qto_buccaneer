import pytest
import ifcopenshell
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ifc_loader import IfcProject

def test_get_gfa_elements():
    # Setup
    project = IfcProject("tests/Mustermodell V2_abstractBIM.ifc")
    
    # Execute
    gfa_elements = project.get_gfa_elements()
    
    # Assert
    assert isinstance(gfa_elements, list), "Should return a list"
    
    # Test each returned element
    for element in gfa_elements:
        assert element.is_a("IfcSpace"), "Each element should be an IfcSpace"
        assert element.Name == "GFA", "Each element should have Name 'GFA'"
        assert element.NetFloorArea == "NetFloorArea", "Each element should have NetFloorArea property"

    # Test with custom parameters
    custom_elements = project.get_gfa_elements(
        ifc_entity="IfcSpace",
        attribute="Name",
        name="CustomName",
        quantity="CustomQuantity"
    )
    assert isinstance(custom_elements, list), "Should return a list with custom parameters"