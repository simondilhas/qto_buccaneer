import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urljoin

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
if not API_KEY_SECRET:
    raise ValueError(
        "IFC_TO_JSON_API_KEY environment variable not set. "
        "Please set it in your .env file or environment variables. "
        "Contact simon.dilhas@abstract.build to obtain a key."
    )

# Validate and clean BASE_URL
BASE_URL = os.getenv("IFC_TO_JSON_API_URL")
#BASE_URL = "http://localhost:8000"

def calculate_geometry_json_via_api(
    ifc_path: str,
    output_dir: str
) -> str:
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
        str: Path to the output directory containing the generated JSON files
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Upload IFC file and get geometry data
        _upload_ifc_file(
            file_path=ifc_path,
            output_dir=output_dir,
            include_geometry=True,
            include_metadata=True,
            debug=True
        )
            
        logger.info(f"Geometry JSON files generated in directory: {output_dir}")
        return output_dir
        
    except Exception as e:
        logger.error(f"Error in calculate_geometry_json: {str(e)}", exc_info=True)
        raise

def _get_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Internal function to get headers with API key for requests."""
    key = api_key or API_KEY_SECRET
    return {
        API_KEY_NAME: key
    }

def _upload_ifc_file(
    file_path: str,
    api_key: Optional[str] = None,
    base_url: str = BASE_URL,
    entities: Optional[List[str]] = None,
    include_geometry: bool = True,
    include_metadata: bool = True,
    output_dir: Optional[str] = None,
    debug: bool = False
) -> None:
    """Internal function to upload IFC file to the server and save the response as JSON files."""
    try:
        # Get base filename without extension
        base_filename = Path(file_path).stem
        
        # Set default output directory if not provided
        if output_dir is None:
            output_dir = os.path.join("output", base_filename)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
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
            
            # Download each file
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
                    
                    # Save the file directly in the output directory
                    output_path = os.path.join(output_dir, output_filename)
                    with open(output_path, 'w') as f:
                        json.dump(file_response.json(), f, indent=2)
                    logger.info(f"Saved {file_type} data to {output_path}")
                else:
                    logger.error(f"Failed to download {file_type} data: {file_response.status_code}")
            
        else:
            logger.error(f"Error uploading file: {response.status_code}")
            if debug:
                logger.error(f"Error details: {response.text}")
            
            # Save error response
            error_path = os.path.join(output_dir, 'error.json')
            with open(error_path, 'w') as f:
                json.dump({
                    'status_code': response.status_code,
                    'error': response.text
                }, f, indent=2)
            logger.info(f"Error details saved to {error_path}")
            
    except Exception as e:
        logger.error(f"Error in upload_ifc_file: {str(e)}", exc_info=True)

