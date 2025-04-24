import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

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
API_KEY_SECRET = os.getenv("API_KEY_SECRET", "test_secret_key")

def get_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Get headers with API key for requests.
    
    Args:
        api_key (Optional[str]): API key to use. If None, uses the default from environment variables.
    """
    key = api_key or API_KEY_SECRET
    return {
        API_KEY_NAME: key
    }

def upload_ifc_file(
    file_path: str,
    api_key: Optional[str] = None,
    base_url: str = "http://0.0.0.0:8000",
    entities: Optional[List[str]] = None,
    include_geometry: bool = True,
    include_metadata: bool = True,
    output_dir: Optional[str] = None,
    debug: bool = False
) -> None:
    """Upload IFC file to the server and save the response as JSON files.
    
    This function uploads an IFC file to a server that converts it to JSON format,
    then downloads and saves the resulting JSON files.
    
    Args:
        file_path (str): Path to the IFC file to upload
        api_key (Optional[str]): API key for authentication. If None, uses the default from environment variables.
        base_url (str): Base URL of the API server
        entities (Optional[List[str]]): List of IFC entities to include in the output.
            If None, all entities will be included.
        include_geometry (bool): Whether to include geometry data in the output
        include_metadata (bool): Whether to include metadata in the output
        output_dir (Optional[str]): Directory to save the output files.
            If None, a directory named after the input file will be created in 'output/'.
        debug (bool): Whether to enable debug logging
        
    Returns:
        None
    """
    try:
        # Get base filename without extension
        base_filename = Path(file_path).stem
        
        # Set default output directory if not provided
        if output_dir is None:
            output_dir = os.path.join("output", base_filename)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get headers with API key
        headers = get_headers(api_key)
        
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
            
            # Log the request details for debugging
            if debug:
                logger.debug(f"Making request to: {base_url}/api/v1/ifc/upload")
                logger.debug(f"With params: {params}")
            
            # Make the request
            response = requests.post(
                f"{base_url}/api/v1/ifc/upload",
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

def check_health(base_url: str = "http://0.0.0.0:8000", api_key: Optional[str] = None) -> Dict[str, Any]:
    """Check API health status."""
    url = f"{base_url}/api/v1/health"
    
    try:
        logger.debug("Checking API health...")
        response = requests.get(url, headers=get_headers(api_key))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking health: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Server response: {e.response.text}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {} 