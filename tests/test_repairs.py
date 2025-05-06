import pytest
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.repairs import _parse_filter, _apply_filter, _apply_change_value, _apply_repair, apply_repairs
from qto_buccaneer.utils.ifc_loader import IfcLoader

# Sample config for testing
SAMPLE_CONFIG = {
    "buildings": [
        {
            "name": "Building A",
            "repairs": [
                {
                    "name": "Fix Space Names",
                    "filter": "type=IfcSpace AND Name=TempName",
                    "actions": [
                        {
                            "change_value": {
                                "field": "Name",
                                "value": "FixedName"
                            }
                        }
                    ]
                },
                {
                    "name": "Update Property",
                    "filter": "type=IfcWall",
                    "actions": [
                        {
                            "change_value": {
                                "field": "Pset_WallCommon.IsExternal",
                                "value": True
                            }
                        }
                    ]
                }
            ]
        },
        {
            "name": "Building B",
            "repairs": []
        }
    ]
}

@pytest.fixture
def mock_ifc_model():
    """Create a mock IFC model."""
    mock_model = MagicMock()
    
    # Mock element with direct attribute
    mock_space = MagicMock()
    mock_space.is_a.return_value = "IfcSpace"
    mock_space.Name = "TempName"
    mock_space.GlobalId = "SPACE_ID_1"
    
    # Mock element with property set
    mock_wall = MagicMock()
    mock_wall.is_a.return_value = "IfcWall"
    mock_wall.GlobalId = "WALL_ID_1"
    
    # Mock property set
    mock_pset = MagicMock()
    mock_pset.Name = "Pset_WallCommon"
    mock_pset.is_a.return_value = "IfcPropertySet"
    
    # Mock property
    mock_property = MagicMock()
    mock_property.Name = "IsExternal"
    mock_property.NominalValue = MagicMock()
    mock_property.NominalValue.is_a.return_value = "IfcBoolean"
    mock_property.NominalValue.__bool__ = lambda self: False
    
    # Setup property set relationships
    mock_pset.HasProperties = [mock_property]
    
    mock_rel_def = MagicMock()
    mock_rel_def.RelatingPropertyDefinition = mock_pset
    
    mock_wall.IsDefinedBy = [mock_rel_def]
    
    # Setup model.by_type to return our mock elements
    def mock_by_type(type_name):
        if type_name == "IfcSpace":
            return [mock_space]
        elif type_name == "IfcWall":
            return [mock_wall]
        elif type_name == "IfcProduct":
            return [mock_space, mock_wall]
        return []
    
    mock_model.by_type.side_effect = mock_by_type
    
    # Setup model.create_entity for property values
    mock_model.create_entity.return_value = MagicMock()
    
    return mock_model, mock_space, mock_wall, mock_property

@pytest.fixture
def mock_ifc_loader(mock_ifc_model):
    """Create a mock IfcLoader instance."""
    mock_model, _, _, _ = mock_ifc_model
    mock_loader = MagicMock(spec=IfcLoader)
    mock_loader.model = mock_model
    mock_loader.file_path = "test_model.ifc"
    return mock_loader

def test_parse_filter_simple():
    """Test parsing a simple filter string."""
    filter_str = "type=IfcSpace AND Name=TempName"
    parsed = _parse_filter(filter_str)
    
    assert len(parsed) == 3
    assert parsed[0]['field'] == 'type'
    assert parsed[0]['op'] == '='
    assert parsed[0]['value'] == 'IfcSpace'
    assert parsed[1] == 'AND'
    assert parsed[2]['field'] == 'Name'
    assert parsed[2]['op'] == '='
    assert parsed[2]['value'] == 'TempName'

def test_parse_filter_complex():
    """Test parsing a complex filter string with different operators."""
    filter_str = "type=IfcWall AND Height>2.5 AND Width!=0.2"
    parsed = _parse_filter(filter_str)
    
    assert len(parsed) == 5
    assert parsed[0]['field'] == 'type'
    assert parsed[0]['op'] == '='
    assert parsed[0]['value'] == 'IfcWall'
    assert parsed[1] == 'AND'
    assert parsed[2]['field'] == 'Height'
    assert parsed[2]['op'] == '>'
    assert parsed[2]['value'] == '2.5'
    assert parsed[3] == 'AND'
    assert parsed[4]['field'] == 'Width'
    assert parsed[4]['op'] == '!='
    assert parsed[4]['value'] == '0.2'

def test_apply_filter(mock_ifc_loader, mock_ifc_model):
    """Test applying a filter to get matching elements."""
    mock_model, mock_space, _, _ = mock_ifc_model
    
    # Test filter for IfcSpace with specific name
    filter_str = "type=IfcSpace AND Name=TempName"
    elements = _apply_filter(mock_ifc_loader, filter_str)
    
    assert len(elements) == 1
    assert elements[0] == mock_space
    
    # Test filter with no matches
    filter_str = "type=IfcSpace AND Name=NonExistentName"
    elements = _apply_filter(mock_ifc_loader, filter_str)
    
    assert len(elements) == 0

def test_apply_change_value_direct_attribute(mock_ifc_model):
    """Test changing a direct attribute value."""
    _, mock_space, _, _ = mock_ifc_model
    
    # Change Name attribute
    _apply_change_value(mock_space, "Name", "NewName")
    
    assert mock_space.Name == "NewName"

def test_apply_change_value_property_set(mock_ifc_model):
    """Test changing a property set value."""
    mock_model, _, mock_wall, mock_property = mock_ifc_model
    
    # Change property set value
    _apply_change_value(mock_wall, "Pset_WallCommon.IsExternal", True, mock_model)
    
    # Verify model.create_entity was called to create a new IfcBoolean
    mock_model.create_entity.assert_called_with("IfcBoolean", True)
    
    # Verify the property's NominalValue was updated
    assert mock_property.NominalValue == mock_model.create_entity.return_value

def test_apply_repair(mock_ifc_loader):
    """Test applying a repair rule to an IFC model."""
    repair = {
        "name": "Fix Space Names",
        "filter": "type=IfcSpace AND Name=TempName",
        "actions": [
            {
                "change_value": {
                    "field": "Name",
                    "value": "FixedName"
                }
            }
        ]
    }
    
    with patch('qto_buccaneer.repairs.IfcLoader', return_value=mock_ifc_loader):
        _apply_repair("test_model.ifc", repair)
    
    # Verify the model was saved
    mock_ifc_loader.model.write.assert_called_once_with("test_model.ifc")

def test_apply_repairs_with_output_dir(mock_ifc_loader):
    """Test applying repairs with an output directory."""
    with patch('qto_buccaneer.repairs.IfcLoader', return_value=mock_ifc_loader):
        with patch('pathlib.Path.mkdir'):
            result = apply_repairs(
                "test_model.ifc",
                SAMPLE_CONFIG,
                "Building A",
                output_dir="output_dir"
            )
    
    # Verify the result is the output path
    assert result == "output_dir/test_model.ifc"
    
    # Verify the model was saved to the output path
    mock_ifc_loader.model.write.assert_called_once_with("output_dir/test_model.ifc")

def test_apply_repairs_building_not_found(mock_ifc_loader):
    """Test applying repairs for a building that doesn't exist in the config."""
    with patch('qto_buccaneer.repairs.IfcLoader', return_value=mock_ifc_loader):
        result = apply_repairs(
            "test_model.ifc",
            SAMPLE_CONFIG,
            "Building C"
        )
    
    # Verify the result is the input path
    assert result == "test_model.ifc"
    
    # Verify the model was not saved
    mock_ifc_loader.model.write.assert_not_called()

def test_apply_repairs_no_repairs(mock_ifc_loader):
    """Test applying repairs for a building with no repairs defined."""
    with patch('qto_buccaneer.repairs.IfcLoader', return_value=mock_ifc_loader):
        result = apply_repairs(
            "test_model.ifc",
            SAMPLE_CONFIG,
            "Building B"
        )
    
    # Verify the result is the input path
    assert result == "test_model.ifc"
    
    # Verify the model was not saved
    mock_ifc_loader.model.write.assert_not_called()

def test_apply_repairs_with_model_object(mock_ifc_loader):
    """Test applying repairs with an ifcopenshell.file object instead of a file path."""
    with patch('qto_buccaneer.repairs.IfcLoader', return_value=mock_ifc_loader):
        with patch('pathlib.Path.mkdir'):
            result = apply_repairs(
                mock_ifc_loader.model,
                SAMPLE_CONFIG,
                "Building A",
                output_dir="output_dir"
            )
    
    # Verify the result is the output path
    assert result == "output_dir/Building A_repaired.ifc"
    
    # Verify the model was saved to the output path
    mock_ifc_loader.model.write.assert_called_once_with("output_dir/Building A_repaired.ifc") 