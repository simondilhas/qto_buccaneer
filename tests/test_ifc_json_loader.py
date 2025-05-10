import pytest
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader

# Test data
SAMPLE_IFC_JSON = """
{
  "elements": [
    {
      "GlobalId": "1ABC23DEF456GHI7890J1K",
      "type": "IfcWall",
      "name": "Wall-01",
      "properties": {
        "Pset_WallCommon": {
          "IsExternal": true,
          "LoadBearing": true
        },
        "Qto_WallBaseQuantities": {
          "Length": 5.0,
          "Width": 0.2,
          "Height": 3.0
        }
      },
      "geometry": {
        "type": "mesh",
        "vertices": [[0,0,0], [5,0,0], [5,0,3], [0,0,3]],
        "faces": [[0,1,2,3]]
      }
    }
  ]
}
"""

@pytest.fixture
def ifc_json_loader():
    """Create an IfcJsonLoader instance with sample data."""
    # Parsăm JSON-ul înainte de a-l folosi
    parsed_json = json.loads(SAMPLE_IFC_JSON)
    
    # Folosim un mock care returnează direct obiectul Python, nu string-ul JSON
    with patch.object(IfcJsonLoader, '_load_data', return_value=parsed_json):
        loader = IfcJsonLoader("dummy_path.json")
        return loader

def test_ifc_json_loader_initialization():
    """Test that IfcJsonLoader initializes correctly with a file path."""
    with patch("builtins.open", mock_open(read_data=SAMPLE_IFC_JSON)):
        loader = IfcJsonLoader("dummy_path.json")
        assert loader.data is not None
        assert "elements" in loader.data

def test_get_elements_by_type(ifc_json_loader):
    """Test getting elements by type."""
    walls = ifc_json_loader.get_elements_by_type("IfcWall")
    assert len(walls) == 1
    assert walls[0]["name"] == "Wall-01"
    
    # Test with non-existent type
    windows = ifc_json_loader.get_elements_by_type("IfcWindow")
    assert len(windows) == 0

def test_get_element_by_id(ifc_json_loader):
    """Test getting an element by its GlobalId."""
    element = ifc_json_loader.get_element_by_id("1ABC23DEF456GHI7890J1K")
    assert element is not None
    assert element["type"] == "IfcWall"
    
    # Test with non-existent ID
    non_existent = ifc_json_loader.get_element_by_id("NON_EXISTENT_ID")
    assert non_existent is None

def test_get_property_value(ifc_json_loader):
    """Test getting a property value from an element."""
    wall = ifc_json_loader.get_elements_by_type("IfcWall")[0]
    
    # Test getting a property
    is_external = ifc_json_loader.get_property_value(wall, "Pset_WallCommon", "IsExternal")
    assert is_external is True
    
    # Test getting a quantity
    length = ifc_json_loader.get_property_value(wall, "Qto_WallBaseQuantities", "Length")
    assert length == 5.0
    
    # Test with non-existent property
    non_existent = ifc_json_loader.get_property_value(wall, "NonExistentPset", "NonExistentProp")
    assert non_existent is None

def test_to_dataframe(ifc_json_loader):
    """Test converting elements to a DataFrame."""
    df = ifc_json_loader.to_dataframe("IfcWall")
    
    # Assertions
    assert len(df) == 1
    assert "GlobalId" in df.columns
    assert "name" in df.columns
    assert "Pset_WallCommon.IsExternal" in df.columns
    assert "Qto_WallBaseQuantities.Length" in df.columns