import os
import json
import logging
import requests
import zipfile
import io
from typing import Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from qto_buccaneer._utils._result_bundle import BaseResultBundle, GeometryResultBundle
from qto_buccaneer.utils.ifc_loader import IfcLoader
import ifcopenshell

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API Configuration
API_KEY_NAME = os.getenv("API_KEY_NAME", "test_key")
API_KEY_SECRET = os.getenv("IFC_TO_JSON_API_KEY")
BASE_URL = os.getenv("IFC_TO_JSON_API_URL")

class IFCAPIClient:
    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY_SECRET):
        """
        Initialize the IFC API client.
        
        Args:
            base_url: Base URL of the API (e.g., 'http://localhost:8000')
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {API_KEY_NAME: api_key}

    def upload_ifc(self, 
                  ifc_file: Union[str, Path, ifcopenshell.file, BaseResultBundle],
                  include_geometry: bool = True, 
                  include_metadata: bool = True) -> GeometryResultBundle:
        """
        Upload an IFC file and get the processed data as a GeometryResultBundle.
        
        Args:
            ifc_file: Path to the IFC file, ifcopenshell.file, or BaseResultBundle
            include_geometry: Whether to include geometry data
            include_metadata: Whether to include metadata
            
        Returns:
            GeometryResultBundle containing the processed data
        """
        try:
            # Create loader if needed
            if isinstance(ifc_file, (str, Path, ifcopenshell.file)):
                loader = IfcLoader(ifc_file)
            elif isinstance(ifc_file, BaseResultBundle):
                loader = IfcLoader(ifc_file.ifc_model)
            else:
                raise ValueError(f"Unsupported input type: {type(ifc_file)}")

            # Get base filename without extension
            base_filename = "ifc_model"
            if loader.file_path:
                base_filename = Path(loader.file_path).stem
            
            # Prepare the file for upload
            if not loader.file_path:
                # Create a temporary file since ifcopenshell.file.write() requires a file path
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.ifc', delete=False) as tmp:
                    loader.model.write(tmp.name)
                    files = {'file': (f"{base_filename}.ifc", open(tmp.name, 'rb'), 'application/octet-stream')}
            else:
                files = {'file': (os.path.basename(loader.file_path), open(loader.file_path, 'rb'), 'application/octet-stream')}
            
            # Make the upload request
            response = requests.post(
                f"{self.base_url}/api/v1/ifc/upload",
                headers=self.headers,
                files=files,
                params={
                    'include_geometry': str(include_geometry).lower(),
                    'include_metadata': str(include_metadata).lower()
                }
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Get the download URL and download the zip file
            download_url = response_data['download_urls']['all_data']
            zip_response = requests.get(
                f"{self.base_url}{download_url}",
                headers=self.headers
            )
            zip_response.raise_for_status()
            
            # Process the zip file and create BaseResultBundle
            return self._process_zip_response(
                zip_response=zip_response,
                response_data=response_data,
                base_filename=base_filename
            )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return self._create_error_bundle(
                error=str(e),
                base_filename=base_filename
            )

    def _process_zip_response(
        self,
        zip_response: requests.Response,
        response_data: Dict[str, Any],
        base_filename: str
    ) -> GeometryResultBundle:
        """
        Process the zip file response and create a GeometryResultBundle.
        
        Args:
            zip_response: The API response containing the zip file
            response_data: The original API response data
            base_filename: Base filename for output files
            
        Returns:
            GeometryResultBundle containing the processed data
        """
        # Create summary
        summary = {
            "Geometry and Metadata JSON": {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "base_filename": base_filename
            }
        }
        
        # Create a BytesIO object from the zip content
        zip_buffer = io.BytesIO(zip_response.content)
        
        # Extract metadata from the zip file
        metadata_df = None
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            # Find the metadata file
            metadata_files = [f for f in zip_file.namelist() if 'metadata' in f.lower()]
            if metadata_files:
                with zip_file.open(metadata_files[0]) as metadata_file:
                    metadata_data = json.load(metadata_file)
                    if "elements" in metadata_data:
                        # Convert elements to DataFrame
                        records = []
                        for key, value in metadata_data["elements"].items():
                            record = value.copy()
                            record['element_key'] = key
                            records.append(record)
                        metadata_df = pd.DataFrame(records)
        
        # Create and return GeometryResultBundle with both zip content and metadata
        return GeometryResultBundle(
            dataframe=metadata_df,
            json={
                "zip_content": zip_response.content,
                "metadata": metadata_data if metadata_files else None
            },
            folderpath=None,
            summary=summary
        )

    def _create_error_bundle(
        self,
        error: str,
        base_filename: str
    ) -> GeometryResultBundle:
        """
        Create an error GeometryResultBundle.
        
        Args:
            error: Error message
            base_filename: Base filename
            
        Returns:
            GeometryResultBundle containing error information
        """
        error_data = {
            "error": error,
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "base_filename": base_filename
        }
        
        return GeometryResultBundle(
            dataframe=None,
            json=error_data,
            folderpath=None,  # No output directory needed
            summary={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "base_filename": base_filename,
                "error_message": error
            }
        )

def calculate_geometry_json_via_api_internal(
    ifc_file: Union[str, Path, ifcopenshell.file, BaseResultBundle]
) -> GeometryResultBundle:
    """
    This module sends IFC geometry to an external FastAPI service 
    to convert it into JSON format for visualization.

    - Requires a separate license key.
    - Contact simon.dilhas@abstract.build to obtain a key.

    Usage:
    - Configure your API key in `.env`
    - Run this as part of your QTO pipeline if 3D JSON output is needed
        
    Args:
        ifc_file: Path to the IFC file, ifcopenshell.file, or BaseResultBundle
        
    Returns:
        GeometryResultBundle: A GeometryResultBundle containing:
            - json: The raw API response data
            - summary: Metadata about the operation including:
                - status: success/error
                - timestamp: When the operation was performed
                - files: List of generated files
                - Additional metadata about the operation
    """
    try:
        # Initialize the client
        client = IFCAPIClient()
        
        # Upload IFC file and get geometry data
        result_bundle = client.upload_ifc(
            ifc_file=ifc_file,
            include_geometry=True,
            include_metadata=True
        )
            
        logger.info("Geometry JSON data processed successfully")
        return result_bundle
        
    except Exception as e:
        logger.error(f"Error in calculate_geometry_json: {str(e)}", exc_info=True)
        raise 

def extract_zip_to_folder(zip_content: bytes, base_filename: str) -> Path:
    """
    Extract a zip file to a folder and return the path.
    
    Args:
        zip_content: The zip file content as bytes
        base_filename: Base name for the output folder
        
    Returns:
        Path: Path to the folder where files were extracted
    """
    # Create output directory
    output_dir = Path(f"{base_filename}_geometry")
    output_dir.mkdir(exist_ok=True)
    
    # Create a BytesIO object from the zip content
    zip_buffer = io.BytesIO(zip_content)
    
    # Extract all files from the zip
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        zip_file.extractall(output_dir)
    
    return output_dir 