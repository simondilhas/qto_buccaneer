import pytest
import os
import sys
import json
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.utils.ifc_metadata_extractor import (
    extract_ifc_metadata, 
    extract_metadata,
    _extract_properties,
    _extract_property_sets,
    _extract_property_value,
    _extract_materials,
    _build_element_id_mapping,
    _create_element_record
)

# Constants
TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")

@pytest.fixture
def mock_ifc_file():
    """Create a mock IFC file."""
    mock_file = MagicMock()
    
    # Setup mock project
    mock_project = MagicMock()
    mock_project.GlobalId = "PROJECT_ID"
    mock_project.Name = "Test Project"
    mock_project.is_a.return_value = "IfcProject"
    mock_project.HasAssociations = []
    mock_project.HasAssignments = []
    
    # Setup mock building
    mock_building = MagicMock()
    mock_building.GlobalId = "BUILDING_ID"
    mock_building.Name = "Test Building"
    mock_building.is_a.return_value = "IfcBuilding"
    mock_building.HasAssociations = []
    mock_building.HasAssignments = []
    
    # Setup mock wall
    mock_wall = MagicMock()
    mock_wall.GlobalId = "WALL_ID"
    mock_wall.Name = "Test Wall"
    mock_wall.is_a.return_value = "IfcWall"
    mock_wall.HasAssociations = []
    mock_wall.HasAssignments = []
    
    # Setup mock property set
    mock_pset = MagicMock()
    mock_pset.Name = "Pset_WallCommon"
    mock_pset.is_a.return_value = "IfcPropertySet"
    
    # Setup mock property
    mock_property = MagicMock()
    mock_property.Name = "IsExternal"
    mock_property.NominalValue = MagicMock()
    mock_property.NominalValue.wrappedValue = True
    mock_pset.HasProperties = [mock_property]
    
    # Setup mock relationship
    mock_rel_def = MagicMock()
    mock_rel_def.is_a.return_value = "IfcRelDefinesByProperties"
    mock_rel_def.RelatingPropertyDefinition = mock_pset
    mock_rel_def.RelatedObjects = [mock_wall]
    
    # Connect property sets to wall
    mock_wall.IsDefinedBy = [mock_rel_def]
    
    # Setup mock quantity set
    mock_qset = MagicMock()
    mock_qset.Name = "Qto_WallBaseQuantities"
    mock_qset.is_a.return_value = "IfcElementQuantity"
    
    # Setup mock quantities
    mock_length = MagicMock()
    mock_length.Name = "Length"
    mock_length.LengthValue = 5.0
    mock_length.is_a.return_value = "IfcQuantityLength"
    
    mock_area = MagicMock()
    mock_area.Name = "GrossFootprintArea"
    mock_area.AreaValue = 10.0
    mock_area.is_a.return_value = "IfcQuantityArea"
    
    mock_qset.Quantities = [mock_length, mock_area]
    
    # Setup mock quantity relationship
    mock_rel_quant = MagicMock()
    mock_rel_quant.is_a.return_value = "IfcRelDefinesByProperties"
    mock_rel_quant.RelatingPropertyDefinition = mock_qset
    mock_rel_quant.RelatedObjects = [mock_wall]
    
    # Add quantity relationship to wall
    mock_wall.IsDefinedBy.append(mock_rel_quant)
    
    # Setup mock material
    mock_material = MagicMock()
    mock_material.Name = "Concrete"
    
    # Setup mock material association
    mock_material_assoc = MagicMock()
    mock_material_assoc.is_a.return_value = "IfcRelAssociatesMaterial"
    mock_material_assoc.RelatingMaterial = mock_material
    
    # Add material association to wall
    mock_wall.HasAssociations.append(mock_material_assoc)
    
    # Setup mock classification
    mock_classification = MagicMock()
    mock_classification.ItemReference = "23.21"
    mock_classification.Name = "Walls"
    
    # Setup mock classification association
    mock_class_assoc = MagicMock()
    mock_class_assoc.is_a.return_value = "IfcRelAssociatesClassification"
    mock_class_assoc.RelatingClassification = mock_classification
    
    # Add classification association to wall
    mock_wall.HasAssociations.append(mock_class_assoc)
    
    # Setup mock system
    mock_system = MagicMock()
    mock_system.GlobalId = "SYSTEM_ID"
    mock_system.Name = "HVAC System"
    mock_system.is_a.return_value = "IfcSystem"
    
    # Setup mock system assignment
    mock_system_assign = MagicMock()
    mock_system_assign.is_a.return_value = "IfcRelAssignsToGroup"
    mock_system_assign.RelatingGroup = mock_system
    
    # Add system assignment to wall
    mock_wall.HasAssignments.append(mock_system_assign)
    
    # Setup by_type method
    def mock_by_type(type_name):
        if type_name == "IfcProject":
            return [mock_project]
        elif type_name == "IfcBuilding":
            return [mock_building]
        elif type_name == "IfcWall":
            return [mock_wall]
        elif type_name == "IfcSystem":
            return [mock_system]
        elif type_name == "IfcClassification":
            return []
        elif type_name == "IfcRelAssociatesClassification":
            return [mock_class_assoc]
        elif type_name == "IfcRelAssignsToGroup":
            return [mock_system_assign]
        return []
    
    mock_file.by_type.side_effect = mock_by_type
    
    # Setup get_inverse method
    def mock_get_inverse(element):
        if element == mock_project:
            return []
        elif element == mock_building:
            return []
        elif element == mock_wall:
            return []
        return []
    
    mock_file.get_inverse.side_effect = mock_get_inverse
    
    return mock_file

@pytest.fixture
def mock_element():
    """Create a mock IFC element with properties."""
    mock_elem = MagicMock()
    mock_elem.GlobalId = "ELEMENT_ID"
    mock_elem.Name = "Test Element"
    mock_elem.is_a.return_value = "IfcWall"
    
    # Setup mock property set
    mock_pset = MagicMock()
    mock_pset.Name = "Pset_WallCommon"
    mock_pset.is_a.return_value = "IfcPropertySet"
    
    # Setup mock property
    mock_property = MagicMock()
    mock_property.Name = "IsExternal"
    mock_property.NominalValue = MagicMock()
    mock_property.NominalValue.wrappedValue = True
    mock_pset.HasProperties = [mock_property]
    
    # Setup mock relationship
    mock_rel_def = MagicMock()
    mock_rel_def.is_a.return_value = "IfcRelDefinesByProperties"
    mock_rel_def.RelatingPropertyDefinition = mock_pset
    mock_rel_def.RelatedObjects = [mock_elem]
    
    # Connect property sets to element
    mock_elem.IsDefinedBy = [mock_rel_def]
    
    return mock_elem

def test_extract_property_sets(mock_element):
    """Test extracting property sets from an element."""
    properties = _extract_property_sets(mock_element)
    
    assert "Pset_WallCommon.IsExternal" in properties
    assert properties["Pset_WallCommon.IsExternal"] is True

def test_extract_properties(mock_element):
    """Test extracting properties from an element."""
    with patch('qto_buccaneer.utils.ifc_metadata_extractor._extract_property_value', 
               return_value=("Pset_WallCommon.IsExternal", True)):
        properties = _extract_properties(mock_element)
    
    assert "Pset_WallCommon.IsExternal" in properties
    assert properties["Pset_WallCommon.IsExternal"] is True

def test_extract_materials(mock_element):
    """Test extracting materials from an element."""
    # Setup mock material
    mock_material = MagicMock()
    mock_material.Name = "Concrete"
    
    # Setup mock material association
    mock_material_assoc = MagicMock()
    mock_material_assoc.is_a.return_value = "IfcRelAssociatesMaterial"
    mock_material_assoc.RelatingMaterial = mock_material
    
    # Add material association to element
    mock_element.HasAssociations = [mock_material_assoc]
    
    materials = _extract_materials(mock_element)
    
    assert "material" in materials
    assert materials["material"] == "Concrete"

def test_build_element_id_mapping(mock_ifc_file):
    """Test building element ID mapping."""
    globalid_to_id, all_elements = _build_element_id_mapping(mock_ifc_file)
    
    assert "PROJECT_ID" in globalid_to_id
    assert "BUILDING_ID" in globalid_to_id
    assert "WALL_ID" in globalid_to_id
    assert len(all_elements) >= 3

def test_create_element_record(mock_ifc_file):
    """Test creating an element record."""
    globalid_to_id, all_elements = _build_element_id_mapping(mock_ifc_file)
    wall = [el for el in all_elements if el.is_a() == "IfcWall"][0]
    
    # Mock child_to_parent mapping
    child_to_parent = {"WALL_ID": "BUILDING_ID"}
    
    record = _create_element_record(wall, 3, globalid_to_id, child_to_parent)
    
    assert record["id"] == 3
    assert record["GlobalId"] == "WALL_ID"
    assert record["Name"] == "Test Wall"
    assert record["type"] == "IfcWall"
    assert "parent" in record
    assert record["parent"] == globalid_to_id["BUILDING_ID"]

def test_extract_ifc_metadata(mock_ifc_file):
    """Test extracting metadata from an IFC file."""
    with patch('ifcopenshell.open', return_value=mock_ifc_file):
        elements_data = extract_ifc_metadata(TEST_IFC_PATH)
    
    assert len(elements_data) >= 3
    
    # Find the wall element
    wall_data = next((elem for elem in elements_data if elem.get("type") == "IfcWall"), None)
    assert wall_data is not None
    assert wall_data["GlobalId"] == "WALL_ID"
    assert wall_data["Name"] == "Test Wall"
    
    # Check if classifications and systems are extracted
    assert "Classifications" in wall_data
    assert "Systems" in wall_data

def test_extract_metadata_dataframe(mock_ifc_file):
    """Test extracting metadata as DataFrame."""
    with patch('ifcopenshell.open', return_value=mock_ifc_file):
        with patch('qto_buccaneer.utils.ifc_metadata_extractor.extract_ifc_metadata', 
                  return_value=[
                      {"id": 1, "GlobalId": "PROJECT_ID", "Name": "Test Project", "type": "IfcProject"},
                      {"id": 2, "GlobalId": "BUILDING_ID", "Name": "Test Building", "type": "IfcBuilding"},
                      {"id": 3, "GlobalId": "WALL_ID", "Name": "Test Wall", "type": "IfcWall"}
                  ]):
            df = extract_metadata(TEST_IFC_PATH, output_formats=["dataframe"])
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "GlobalId" in df.columns
    assert "Name" in df.columns
    assert "type" in df.columns

def test_extract_metadata_json(mock_ifc_file):
    """Test extracting metadata as JSON."""
    with patch('ifcopenshell.open', return_value=mock_ifc_file):
        with patch('qto_buccaneer.utils.ifc_metadata_extractor.extract_ifc_metadata', 
                  return_value=[
                      {"id": 1, "GlobalId": "PROJECT_ID", "Name": "Test Project", "type": "IfcProject"},
                      {"id": 2, "GlobalId": "BUILDING_ID", "Name": "Test Building", "type": "IfcBuilding"},
                      {"id": 3, "GlobalId": "WALL_ID", "Name": "Test Wall", "type": "IfcWall"}
                  ]):
            json_data = extract_metadata(TEST_IFC_PATH, output_formats=["json"])
    
    assert isinstance(json_data, dict)
    assert "elements" in json_data
    assert "1" in json_data["elements"]
    assert "2" in json_data["elements"]
    assert "3" in json_data["elements"]
    assert json_data["elements"]["3"]["Name"] == "Test Wall"

def test_extract_metadata_json_file(mock_ifc_file, tmp_path):
    """Test extracting metadata as JSON file."""
    output_dir = tmp_path / "output"
    
    with patch('ifcopenshell.open', return_value=mock_ifc_file):
        with patch('qto_buccaneer.utils.ifc_metadata_extractor.extract_ifc_metadata', 
                  return_value=[
                      {"id": 1, "GlobalId": "PROJECT_ID", "Name": "Test Project", "type": "IfcProject"},
                      {"id": 2, "GlobalId": "BUILDING_ID", "Name": "Test Building", "type": "IfcBuilding"},
                      {"id": 3, "GlobalId": "WALL_ID", "Name": "Test Wall", "type": "IfcWall"}
                  ]):
            json_path = extract_metadata(
                TEST_IFC_PATH, 
                output_formats=["json_file"], 
                output_dir=output_dir,
                project_name="test_project"
            )
    
    assert isinstance(json_path, str)
    assert "test_project_metadata.json" in json_path
    
    # Check if the file exists
    assert os.path.exists(json_path)
    
    # Check file content
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    assert "elements" in json_data
    assert "3" in json_data["elements"]
    assert json_data["elements"]["3"]["Name"] == "Test Wall"

def test_extract_metadata_multiple_formats(mock_ifc_file, tmp_path):
    """Test extracting metadata in multiple formats."""
    output_dir = tmp_path / "output"
    
    with patch('ifcopenshell.open', return_value=mock_ifc_file):
        with patch('qto_buccaneer.utils.ifc_metadata_extractor.extract_ifc_metadata', 
                  return_value=[
                      {"id": 1, "GlobalId": "PROJECT_ID", "Name": "Test Project", "type": "IfcProject"},
                      {"id": 2, "GlobalId": "BUILDING_ID", "Name": "Test Building", "type": "IfcBuilding"},
                      {"id": 3, "GlobalId": "WALL_ID", "Name": "Test Wall", "type": "IfcWall"}
                  ]):
            df, json_data, json_path = extract_metadata(
                TEST_IFC_PATH, 
                output_formats=["dataframe", "json", "json_file"], 
                output_dir=output_dir,
                project_name="test_project"
            )
    
    assert isinstance(df, pd.DataFrame)
    assert isinstance(json_data, dict)
    assert isinstance(json_path, str)
    
    assert len(df) == 3
    assert "elements" in json_data
    assert "test_project_metadata.json" in json_path 