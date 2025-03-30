import os
import pytest
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ifc_loader import IfcLoader

# Path to your test IFC file (adjust if needed)
TEST_IFC_FILE = "tests/Mustermodell V2_abstractBIM.ifc"

@pytest.fixture(scope="module")
def ifc_loader():
    if not os.path.isfile(TEST_IFC_FILE):
        pytest.fail(f"Test IFC file not found: {TEST_IFC_FILE}")
    return IfcLoader(TEST_IFC_FILE)

def test_get_elements_by_attribute(ifc_loader):
    # Example: Test that a space named 'GFA' exists
    elements = ifc_loader.get_elements(key="Name", value="GFA", ifc_entity="IfcSpace")
    assert isinstance(elements, list)
    assert len(elements) > 0
    assert elements[0].is_a("IfcSpace")
    assert getattr(elements[0], "Name", None) == "GFA"

def test_get_elements_by_property(ifc_loader):
    # Example: Test walls with IsExternal == True (adjust according to your IFC test file)
    walls = ifc_loader.get_elements(key="IsExternal", value=True, ifc_entity="IfcWall")
    assert isinstance(walls, list)
    for wall in walls:
        assert wall.is_a("IfcWall")

def test_get_gfa_elements(ifc_loader):
    gfa_spaces = ifc_loader.get_gfa_elements()
    assert isinstance(gfa_spaces, list)
    assert len(gfa_spaces) > 0
    for space in gfa_spaces:
        assert space.is_a("IfcSpace")
        assert getattr(space, "Name", None) == "GFA"
