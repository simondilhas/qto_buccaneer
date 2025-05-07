import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urljoin
from qto_buccaneer._utils._result_bundle import BaseResultBundle
from qto_buccaneer.utils.ifc_loader import IfcLoader
from logging import getLogger
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = getLogger(__name__)

load_dotenv()

# API Configuration
API_KEY_NAME = os.getenv("API_KEY_NAME", "test_key")
API_KEY_SECRET = os.getenv("IFC_TO_JSON_API_KEY")
BASE_URL = os.getenv("IFC_TO_JSON_API_URL")




def _validate_api_key(api_key: Optional[str] = None) -> str:
    """Validate that an API key is available."""
    key = api_key or API_KEY_SECRET
    if not key:
        raise ValueError(
            "IFC_TO_JSON_API_KEY environment variable not set. "
            "Please set it in your .env file or environment variables. "
            "Contact simon.dilhas@abstract.build to obtain a key."
        )
    return key

def _get_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Internal function to get headers with API key for requests."""
    key = _validate_api_key(api_key)
    return {
        API_KEY_NAME: key
    }

def _create_geometry_result_bundle(
    response_data: Dict[str, Any],
    output_dir: Path,
    base_filename: str,
    metadata: Optional[Dict[str, Any]] = None
) -> BaseResultBundle:
    """Create a BaseResultBundle from the geometry API response.
    
    Args:
        response_data: The raw response data from the API
        output_dir: Directory where files will be saved
        base_filename: Base filename for output files
        metadata: Optional additional metadata to include
        
    Returns:
        BaseResultBundle containing the geometry data and metadata
    """
    # Create summary data with Geometry and Metadata JSON as top-level key
    summary = {
        "Geometry and Metadata JSON": {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "base_filename": base_filename,
            "files": response_data.get('files', []),
            "extracted_ifc_metadata": metadata or {},
            **(metadata or {})
        }
    }
    
    # Load data into DataFrame if files are available
    dataframe = None
    if "files" in response_data:
        records = []
        for file in response_data["files"]:
            file_path = output_dir / f"{file}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records.extend(data)
                    elif isinstance(data, dict) and "elements" in data:
                        for key, value in data["elements"].items():
                            record = value.copy()
                            record['element_key'] = key
                            records.append(record)
        if records:
            dataframe = pd.DataFrame(records)
    
    # Create the BaseResultBundle
    return BaseResultBundle(
        dataframe=dataframe,
        json=response_data,
        folderpath=output_dir,
        summary=summary
    )

def _upload_ifc_file(
    file_path: str,
    api_key: Optional[str] = None,
    base_url: str = BASE_URL,
    entities: Optional[List[str]] = None,
    include_geometry: bool = True,
    include_metadata: bool = True,
    output_dir: Optional[str] = None,
    debug: bool = False
) -> BaseResultBundle:
    """Upload IFC file to the server and return a BaseResultBundle with the response.
    
    Args:
        file_path: Path to the IFC file
        api_key: Optional API key (defaults to environment variable)
        base_url: Base URL for the API
        entities: Optional list of entity types to include
        include_geometry: Whether to include geometry data
        include_metadata: Whether to include metadata
        output_dir: Optional output directory
        debug: Whether to enable debug logging
        
    Returns:
        BaseResultBundle containing the API response and saved files
    """
    try:
        # Get base filename without extension
        base_filename = Path(file_path).stem
        
        # Set default output directory if not provided
        if output_dir is None:
            output_dir = os.path.join("output", base_filename)
        output_dir = Path(output_dir)
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get headers with API key
        headers = _get_headers(api_key)
        
        # Log the headers for debugging
        if debug:
            logger.debug(f"Using headers: {headers}")
        
        # Prepare the file for upload
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
            
            # Prepare query parameters
            params = {}
            if entities:
                params['entities'] = entities
            if not include_geometry:
                params['include_geometry'] = 'false'
            if not include_metadata:
                params['include_metadata'] = 'false'
            
            # Construct the upload URL
            upload_url = f"{base_url}/api/v1/ifc/upload"
            
            # Log the request details for debugging
            if debug:
                logger.debug(f"Making request to: {upload_url}")
                logger.debug(f"With params: {params}")
            
            # Make the request
            response = requests.post(
                upload_url,
                headers=headers,
                files=files,
                params=params
            )
        
        if response.status_code == 200:
            # Process the response
            response_data = response.json()
            logger.info(f"Successfully processed IFC file. Generated files: {response_data['files']}")
            
            # Create metadata for the BaseResultBundle
            metadata = {
                "status_code": response.status_code,
                "entities": entities,
                "include_geometry": include_geometry,
                "include_metadata": include_metadata
            }
            
            # Create BaseResultBundle
            result_bundle = _create_geometry_result_bundle(
                response_data=response_data,
                output_dir=output_dir,
                base_filename=base_filename,
                metadata=metadata
            )
            
            # Download each file and save it
            for file_type, download_url in response_data['download_urls'].items():
                file_url = f"{base_url}{download_url}"
                file_response = requests.get(file_url, headers=headers)
                
                if file_response.status_code == 200:
                    # Determine the output filename
                    if '_metadata' in file_type:
                        output_filename = f"{base_filename}_metadata.json"
                    else:
                        # Remove _geometry suffix and add .json
                        entity_type = file_type.replace('_geometry', '')
                        output_filename = f"{entity_type}.json"
                    
                    # Save the file
                    output_path = output_dir / output_filename
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(file_response.json(), f, indent=2, ensure_ascii=False)
                    logger.info(f"Saved {file_type} data to {output_path}")
                else:
                    logger.error(f"Failed to download {file_type} data: {file_response.status_code}")
            
            return result_bundle
            
        else:
            logger.error(f"Error uploading file: {response.status_code}")
            if debug:
                logger.error(f"Error details: {response.text}")
            
            # Create error BaseResultBundle
            error_data = {
                'status_code': response.status_code,
                'error': response.text
            }
            
            error_bundle = BaseResultBundle(
                dataframe=None,
                json=error_data,
                folderpath=output_dir,
                summary={
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "base_filename": base_filename,
                    "error_code": response.status_code,
                    "error_message": response.text
                }
            )
            
            # Save error response
            error_path = output_dir / 'error.json'
            error_bundle.save_json(error_path)
            logger.info(f"Error details saved to {error_path}")
            
            return error_bundle
            
    except Exception as e:
        logger.error(f"Error in upload_ifc_file: {str(e)}", exc_info=True)
        
        # Create error BaseResultBundle
        error_bundle = BaseResultBundle(
            dataframe=None,
            json={"error": str(e)},
            folderpath=output_dir,
            summary={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "base_filename": base_filename,
                "error_message": str(e)
            }
        )
        
        return error_bundle

def calculate_geometry_json_via_api(
    ifc_path: str,
    output_dir: str
) -> BaseResultBundle:
    """
    This module sends IFC geometry to an external FastAPI service 
    to convert it into JSON format for visualization.

    - Requires a separate license key.
    - Contact simon.dilhas@abstract.build to obtain a key.

    Usage:
    - Configure your API key in `.env`
    - Run this as part of your QTO pipeline if 3D JSON output is needed
        
    Args:
        ifc_path (str): Path to the IFC file
        output_dir (str): Directory where the JSON file should be saved
        
    Returns:
        BaseResultBundle: A BaseResultBundle containing:
            - json: The raw API response data
            - folderpath: Path to the output directory
            - summary: Metadata about the operation including:
                - status: success/error
                - timestamp: When the operation was performed
                - files: List of generated files
                - Additional metadata about the operation
    """
    try:
        # Validate API key
        _validate_api_key()
        
        # Upload IFC file and get geometry data
        result_bundle = _upload_ifc_file(
            file_path=ifc_path,
            output_dir=output_dir,
            include_geometry=True,
            include_metadata=True,
            debug=True
        )
            
        logger.info(f"Geometry JSON files generated in directory: {output_dir}")
        return result_bundle
        
    except Exception as e:
        logger.error(f"Error in calculate_geometry_json: {str(e)}", exc_info=True)
        
        # Create error BaseResultBundle
        error_bundle = BaseResultBundle(
            dataframe=None,
            json={"error": str(e)},
            folderpath=Path(output_dir),
            summary={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "base_filename": Path(ifc_path).stem,
                "error_message": str(e)
            }
        )
        
        return error_bundle

