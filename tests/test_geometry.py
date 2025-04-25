import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests
import logging

from qto_buccaneer.geometry import calculate_geometry_json_via_api

@pytest.fixture
def mock_env_vars():
    """Fixture to set up mock environment variables."""
    with patch.dict(os.environ, {
        "API_KEY_NAME": "test_key",
        "IFC_TO_JSON_API_KEY": "test_api_key",
        "IFC_TO_JSON_API_URL": "http://test-api.example.com"
    }):
        yield

@pytest.fixture
def mock_response():
    """Fixture to create a mock API response."""
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "files": ["geometry.json", "metadata.json"],
        "download_urls": {
            "geometry": "/download/geometry.json",
            "metadata": "/download/metadata.json"
        }
    }
    return mock_response

@pytest.fixture
def mock_download_response():
    """Fixture to create mock download responses."""
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0]],
        "faces": [[0, 1, 2]]
    }
    return mock_response

def test_calculate_geometry_json_via_api_success(
    mock_env_vars,
    mock_response,
    mock_download_response,
    tmp_path
):
    """Test the successful workflow of converting IFC to JSON geometry."""
    # Setup test files
    ifc_path = tmp_path / "test.ifc"
    output_dir = tmp_path / "output"
    ifc_path.write_text("dummy IFC content")
    
    # Mock the API calls
    with patch('requests.post', return_value=mock_response) as mock_post, \
         patch('requests.get', return_value=mock_download_response) as mock_get:
        
        # Run the function
        result_path = calculate_geometry_json_via_api(
            ifc_path=str(ifc_path),
            output_dir=str(output_dir)
        )
        
        # Verify the API calls
        mock_post.assert_called_once()
        assert mock_get.call_count == 2  # Called for both geometry and metadata
        
        # Verify the output
        assert result_path == str(output_dir)
        assert os.path.exists(output_dir)
        
        # Verify the output files were created
        geometry_file = output_dir / "geometry.json"
        metadata_file = output_dir / "metadata.json"
        assert geometry_file.exists()
        assert metadata_file.exists()
        
        # Verify the content of the files
        with open(geometry_file) as f:
            geometry_data = json.load(f)
            assert "vertices" in geometry_data
            assert "faces" in geometry_data

def test_calculate_geometry_json_via_api_failure(
    mock_env_vars,
    tmp_path,
    caplog
):
    """Test error handling when API request fails."""
    # Setup test files
    ifc_path = tmp_path / "test.ifc"
    output_dir = tmp_path / "output"
    ifc_path.write_text("dummy IFC content")
    
    # Mock a failed API response
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    # Set up logging capture
    caplog.set_level(logging.ERROR)
    
    with patch('requests.post', return_value=mock_response) as mock_post:
        # Run the function
        result_path = calculate_geometry_json_via_api(
            ifc_path=str(ifc_path),
            output_dir=str(output_dir)
        )
        
        # Verify the API call was made
        mock_post.assert_called_once()
        
        # Verify error was logged
        assert "Error uploading file: 500" in caplog.text
        assert "Error details: Internal Server Error" in caplog.text
        
        # Verify error file was created
        error_file = output_dir / "error.json"
        assert error_file.exists()
        
        # Verify error file content
        with open(error_file) as f:
            error_data = json.load(f)
            assert error_data["status_code"] == 500
            assert "Internal Server Error" in error_data["error"]

def test_calculate_geometry_json_via_api_download_failure(
    mock_env_vars,
    mock_response,
    tmp_path,
    caplog
):
    """Test error handling when file download fails."""
    # Setup test files
    ifc_path = tmp_path / "test.ifc"
    output_dir = tmp_path / "output"
    ifc_path.write_text("dummy IFC content")
    
    # Mock a failed download response
    mock_download_response = MagicMock(spec=requests.Response)
    mock_download_response.status_code = 404
    
    # Set up logging capture
    caplog.set_level(logging.ERROR)
    
    with patch('requests.post', return_value=mock_response) as mock_post, \
         patch('requests.get', return_value=mock_download_response) as mock_get:
        
        # Run the function
        result_path = calculate_geometry_json_via_api(
            ifc_path=str(ifc_path),
            output_dir=str(output_dir)
        )
        
        # Verify the API calls were made
        mock_post.assert_called_once()
        mock_get.assert_called()
        
        # Verify error was logged
        assert "Failed to download" in caplog.text
        assert "404" in caplog.text 