import pytest
import os
import sys
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
    # Setup mock properties and methods as needed
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

def test_get_entity_metadata_df(ifc_loader, mock_ifc_model):
    """Test getting entity metadata as DataFrame."""
    # Setup mock entities
    mock_entity1 = MagicMock()
    mock_entity1.Name = "Entity1"
    mock_entity1.GlobalId = "ID1"
    
    mock_entity2 = MagicMock()
    mock_entity2.Name = "Entity2"
    mock_entity2.GlobalId = "ID2"
    
    mock_ifc_model.by_type.return_value = [mock_entity1, mock_entity2]
    
    # Call the method
    df = ifc_loader.get_entity_metadata_df("IfcSpace")
    
    # Assertions
    assert len(df) == 2
    assert "Name" in df.columns
    assert "GlobalId" in df.columns
    mock_ifc_model.by_type.assert_called_once_with("IfcSpace")

def test_load_method(ifc_loader):
    """Test the load method returns the IFC model."""
    model = ifc_loader.load()
    assert model is not None

def test_get_all_entities(ifc_loader, mock_ifc_model):
    """Test getting all entities of a specific type."""
    # Setup mock entities
    mock_entities = [MagicMock(), MagicMock()]
    mock_ifc_model.by_type.return_value = mock_entities
    
    # Call the method
    entities = ifc_loader.get_all_entities("IfcWall")
    
    # Assertions
    assert entities == mock_entities
    mock_ifc_model.by_type.assert_called_once_with("IfcWall")