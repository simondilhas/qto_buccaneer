import pytest
import os
import sys
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.utils.ifc_loader import IfcLoader

# Constants
TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")

@pytest.fixture
def mock_ifc_model():
    """Create a mock IFC model."""
    mock_model = MagicMock()
    
    # Setup mock spaces
    mock_space1 = MagicMock()
    mock_space1.Name = "Space1"
    mock_space1.LongName = "Long Space Name 1"
    mock_space1.GlobalId = "SPACE_ID_1"
    mock_space1.Description = "Description 1"
    mock_space1.ObjectType = "Room"
    mock_space1.is_a.return_value = "IfcSpace"
    
    mock_space2 = MagicMock()
    mock_space2.Name = "Space2"
    mock_space2.LongName = "Long Space Name 2"
    mock_space2.GlobalId = "SPACE_ID_2"
    mock_space2.Description = "Description 2"
    mock_space2.ObjectType = "Room"
    mock_space2.is_a.return_value = "IfcSpace"
    
    # Setup mock property sets
    mock_pset1 = MagicMock()
    mock_pset1.Name = "Pset_SpaceCommon"
    mock_prop1 = MagicMock()
    mock_prop1.Name = "IsExternal"
    mock_prop1.NominalValue = MagicMock()
    mock_prop1.NominalValue.wrappedValue = True
    mock_pset1.HasProperties = [mock_prop1]
    
    # Setup mock property definition relationship
    mock_rel_def = MagicMock()
    mock_rel_def.RelatingPropertyDefinition = mock_pset1
    
    # Connect property sets to spaces
    mock_space1.IsDefinedBy = [mock_rel_def]
    mock_space2.IsDefinedBy = []
    
    # Setup mock project
    mock_project = MagicMock()
    mock_project.Name = "Test Project"
    mock_project.GlobalId = "PROJECT_ID"
    mock_project.Phase = "Design"
    mock_project.Status = "Active"
    
    # Setup mock stories
    mock_story1 = MagicMock()
    mock_story1.Name = "Ground Floor"
    mock_story1.Elevation = 0.0
    
    mock_story2 = MagicMock()
    mock_story2.Name = "First Floor"
    mock_story2.Elevation = 3.0
    
    # Setup mock relationships
    mock_rel_contained = MagicMock()
    mock_rel_contained.is_a.return_value = True
    mock_rel_contained.RelatedElements = [mock_space1]
    
    mock_rel_aggregates = MagicMock()
    mock_rel_aggregates.is_a.return_value = True
    mock_rel_aggregates.RelatedObjects = [mock_space2]
    
    # Setup by_type method
    def mock_by_type(type_name):
        if type_name == "IfcSpace":
            return [mock_space1, mock_space2]
        elif type_name == "IfcProject":
            return [mock_project]
        elif type_name == "IfcBuildingStorey":
            return [mock_story1, mock_story2]
        return []
    
    mock_model.by_type.side_effect = mock_by_type
    
    # Setup get_inverse method
    def mock_get_inverse(element):
        if element == mock_story1:
            return [mock_rel_contained]
        elif element == mock_story2:
            return [mock_rel_aggregates]
        return []
    
    mock_model.get_inverse.side_effect = mock_get_inverse
    
    return mock_model

@pytest.fixture
def ifc_loader(mock_ifc_model):
    """Create an IfcLoader instance with a mock model."""
    with patch('ifcopenshell.open', return_value=mock_ifc_model):
        loader = IfcLoader(TEST_IFC_PATH)
        return loader

def test_ifc_loader_initialization():
    """Test that IfcLoader initializes correctly with a file path."""
    with patch('ifcopenshell.open') as mock_open:
        loader = IfcLoader(TEST_IFC_PATH)
        mock_open.assert_called_once_with(TEST_IFC_PATH)
        assert loader.file_path == TEST_IFC_PATH
        assert loader.model is not None

def test_ifc_loader_initialization_with_model():
    """Test that IfcLoader initializes correctly with an existing model."""
    mock_model = MagicMock()
    loader = IfcLoader(mock_model)
    assert loader.model == mock_model
    assert loader.file_path is None

def test_get_property_value(ifc_loader, mock_ifc_model):
    """Test getting a property value from an element."""
    spaces = mock_ifc_model.by_type("IfcSpace")
    
    # Test getting a property that exists
    is_external = ifc_loader.get_property_value(spaces[0], "Pset_SpaceCommon", "IsExternal")
    assert is_external is True
    
    # Test getting a property that doesn't exist
    non_existent = ifc_loader.get_property_value(spaces[1], "Pset_SpaceCommon", "IsExternal")
    assert non_existent is None

def test_get_property_sets(ifc_loader, mock_ifc_model):
    """Test getting all property sets for an element."""
    spaces = mock_ifc_model.by_type("IfcSpace")
    
    # Test getting property sets for an element with properties
    psets = ifc_loader.get_property_sets(spaces[0])
    assert "Pset_SpaceCommon" in psets
    assert "IsExternal" in psets["Pset_SpaceCommon"]
    
    # Test getting property sets for an element without properties
    empty_psets = ifc_loader.get_property_sets(spaces[1])
    assert empty_psets == {}

def test_get_elements(ifc_loader, mock_ifc_model):
    """Test getting elements with filters."""
    # Test getting all spaces
    spaces = ifc_loader.get_elements("IfcSpace")
    assert len(spaces) == 2
    
    # Test getting filtered spaces
    filtered_spaces = ifc_loader.get_elements("IfcSpace", {"Name": "Space1"})
    assert len(filtered_spaces) == 1
    assert filtered_spaces[0].Name == "Space1"

def test_get_project_info(ifc_loader):
    """Test getting project information."""
    project_info = ifc_loader.get_project_info()
    
    assert project_info["project_name"] == "Test Project"
    assert project_info["project_number"] == "PROJECT_ID"
    assert project_info["project_phase"] == "Design"
    assert project_info["project_status"] == "Active"

def test_get_space_information(ifc_loader):
    """Test getting space information as DataFrame."""
    df = ifc_loader.get_space_information()
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "Name" in df.columns
    assert "LongName" in df.columns
    assert "GlobalId" in df.columns
    assert "Description" in df.columns
    assert "ObjectType" in df.columns
    assert "IFC_ENTITY_TYPE" in df.columns
    
    # Check values
    assert "Space1" in df["Name"].values
    assert "Long Space Name 1" in df["LongName"].values
    assert "SPACE_ID_1" in df["GlobalId"].values
    
    # Check property set values
    assert "Pset_SpaceCommon.IsExternal" in df.columns

def test_get_element_spatial_relationship(ifc_loader):
    """Test getting spatial relationships for elements."""
    df = ifc_loader.get_element_spatial_relationship()
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "GlobalId" in df.columns
    assert "BuildingStory" in df.columns
    assert "ElevationOfStory" in df.columns
    
    # Check values
    assert "SPACE_ID_1" in df["GlobalId"].values
    assert "SPACE_ID_2" in df["GlobalId"].values
    assert "Ground Floor" in df["BuildingStory"].values
    assert "First Floor" in df["BuildingStory"].values

def test_get_entity_metadata_df(ifc_loader):
    """Test getting entity metadata as DataFrame."""
    # Mock the get_entity_metadata method
    with patch.object(ifc_loader, 'get_entity_metadata', return_value={"GlobalId": "ID1", "Name": "Entity1"}):
        df = ifc_loader.get_entity_metadata_df("IfcSpace")
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "GlobalId" in df.columns
        assert "Name" in df.columns

def test_get_entity_geometry_df(ifc_loader):
    """Test getting entity geometry as DataFrame."""
    # Mock the get_entity_geometry method
    with patch.object(ifc_loader, 'get_entity_geometry', return_value={"GlobalId": "ID1", "Area": 100.0}):
        df = ifc_loader.get_entity_geometry_df("IfcSpace")
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "GlobalId" in df.columns
        assert "Area" in df.columns

def test_get_filtered_elements(ifc_loader):
    """Test getting filtered elements."""
    # Mock the filter_elements method
    with patch('qto_buccaneer.utils.ifc_loader.IfcFilter.filter_elements', return_value=pd.DataFrame([{"GlobalId": "ID1"}])):
        with patch.object(ifc_loader, 'get_entity_metadata_df', return_value=pd.DataFrame([{"GlobalId": "ID1"}, {"GlobalId": "ID2"}])):
            df = ifc_loader.get_filtered_elements("IfcSpace", {"Name": "Space1"})
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 1
            assert "GlobalId" in df.columns