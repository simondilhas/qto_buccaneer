import pytest
import os
import sys
import pandas as pd
import ifcopenshell
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.enrich import enrich_df, enrich_ifc_with_df
from qto_buccaneer.utils.ifc_loader import IfcLoader

# Test data
@pytest.fixture
def sample_model_df():
    """Create a sample model DataFrame for testing."""
    return pd.DataFrame({
        'LongName': ['Room 101', 'Room 102', 'Room 103'],
        'GlobalId': ['ID1', 'ID2', 'ID3'],
        'Area': [20.0, 25.0, 30.0]
    })

@pytest.fixture
def sample_enrichment_df():
    """Create a sample enrichment DataFrame for testing."""
    return pd.DataFrame({
        'LongName': ['Room 101', 'Room 102', 'Room 104'],
        'OccupancyNumber': [2, 4, 1],
        'Department': ['HR', 'Engineering', 'Storage']
    })

@pytest.fixture
def mock_ifc_model():
    """Create a mock IFC model."""
    mock_model = MagicMock()
    mock_model.by_guid.return_value = MagicMock()
    mock_model.create_entity.return_value = MagicMock()
    return mock_model

@pytest.fixture
def mock_ifc_loader(mock_ifc_model):
    """Create a mock IfcLoader instance."""
    mock_loader = MagicMock(spec=IfcLoader)
    mock_loader.model = mock_ifc_model
    mock_loader.file_path = "test_model.ifc"
    
    # Mock the get_space_information method
    mock_loader.get_space_information.return_value = pd.DataFrame({
        'LongName': ['Room 101', 'Room 102', 'Room 103'],
        'GlobalId': ['ID1', 'ID2', 'ID3']
    })
    
    return mock_loader

def test_enrich_df(sample_model_df, sample_enrichment_df):
    """Test enriching a DataFrame with data from another DataFrame."""
    # Enrich model data with enrichment data
    enriched_df = enrich_df(sample_model_df, sample_enrichment_df, 'LongName')
    
    # Assertions
    assert len(enriched_df) == 3  # Should maintain original number of rows
    assert 'OccupancyNumber' in enriched_df.columns
    assert 'Department' in enriched_df.columns
    
    # Check values were correctly merged
    assert enriched_df.loc[enriched_df['LongName'] == 'Room 101', 'OccupancyNumber'].values[0] == 2
    assert enriched_df.loc[enriched_df['LongName'] == 'Room 102', 'Department'].values[0] == 'Engineering'
    
    # Room 103 should have NaN for enrichment columns as it's not in enrichment_df
    assert pd.isna(enriched_df.loc[enriched_df['LongName'] == 'Room 103', 'OccupancyNumber'].values[0])
    
    # Room 104 from enrichment_df should not be in the result as it's not in model_df
    assert 'Room 104' not in enriched_df['LongName'].values

def test_enrich_ifc_with_df_using_loader(mock_ifc_loader, sample_enrichment_df):
    """Test enriching an IFC file using an IfcLoader instance."""
    with patch('ifcopenshell.open', return_value=MagicMock()):
        with patch('ifcopenshell.guid.new', return_value='NEW_GUID'):
            # Call the function with mock loader
            result_path = enrich_ifc_with_df(
                mock_ifc_loader,
                sample_enrichment_df,
                key='LongName',
                pset_name='Pset_TestEnrichment'
            )
    
    # Assertions
    assert result_path == "test_model_enriched.ifc"
    mock_ifc_loader.get_space_information.assert_called_once()
    
    # Check that the model was written
    mock_ifc_loader.model.write.assert_called_once()

def test_enrich_ifc_with_df_using_file_path(mock_ifc_model, sample_enrichment_df):
    """Test enriching an IFC file using a file path."""
    with patch('qto_buccaneer.enrich.IfcLoader') as mock_loader_class:
        # Setup the mock loader
        mock_loader_instance = MagicMock()
        mock_loader_instance.model = mock_ifc_model
        mock_loader_instance.file_path = "test_model.ifc"
        mock_loader_instance.get_space_information.return_value = pd.DataFrame({
            'LongName': ['Room 101', 'Room 102', 'Room 103'],
            'GlobalId': ['ID1', 'ID2', 'ID3']
        })
        mock_loader_class.return_value = mock_loader_instance
        
        with patch('ifcopenshell.open', return_value=MagicMock()):
            with patch('ifcopenshell.guid.new', return_value='NEW_GUID'):
                # Call the function with file path
                result_path = enrich_ifc_with_df(
                    "test_model.ifc",
                    sample_enrichment_df,
                    key='LongName',
                    output_dir="output_dir"
                )
    
    # Assertions
    assert result_path == os.path.join("output_dir", "test_model_enriched.ifc")
    mock_loader_instance.get_space_information.assert_called_once()

def test_enrich_ifc_with_df_with_globalid(mock_ifc_loader):
    """Test enriching an IFC file with a DataFrame that already has GlobalId."""
    # Create enrichment data with GlobalId
    enrichment_df = pd.DataFrame({
        'GlobalId': ['ID1', 'ID2'],
        'CustomProperty': ['Value1', 'Value2']
    })
    
    with patch('ifcopenshell.open', return_value=MagicMock()):
        with patch('ifcopenshell.guid.new', return_value='NEW_GUID'):
            # Call the function
            result_path = enrich_ifc_with_df(
                mock_ifc_loader,
                enrichment_df
            )
    
    # Assertions
    assert result_path == "test_model_enriched.ifc"
    # Should not call get_space_information since GlobalId is already present
    mock_ifc_loader.get_space_information.assert_not_called()

def test_enrich_ifc_with_df_exception_handling(mock_ifc_loader, sample_enrichment_df):
    """Test exception handling in enrich_ifc_with_df."""
    # Setup mock to raise an exception when opening the new file
    with patch('ifcopenshell.open', side_effect=Exception("Test exception")):
        with patch('os.remove') as mock_remove:
            # Call the function and expect an exception
            with pytest.raises(Exception, match="Test exception"):
                enrich_ifc_with_df(
                    mock_ifc_loader,
                    sample_enrichment_df
                )
    
    # Should attempt to remove the file if an exception occurs
    mock_remove.assert_called_once() 