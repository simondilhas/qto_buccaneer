import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urljoin
from qto_buccaneer.tools.geometry.calculate_geometry_json_via_api import _upload_ifc_file, _validate_api_key

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables


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
        # Validate API key
        _validate_api_key()
        
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
