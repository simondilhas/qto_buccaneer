import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urljoin
from qto_buccaneer._utils.extract.extract_geometry_and_metadata_via_api import _upload_ifc_file, _validate_api_key
from qto_buccaneer._utils._result_bundle import ResultBundle
from qto_buccaneer._utils.extract.extract_metadata_from_ifc import extract_metadata_from_ifc_privat
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

def extract_geometry_and_metadata_via_api(
    ifc_path: str,
    output_dir: str
) -> ResultBundle:
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
        ResultBundle: A ResultBundle containing the geometry data and metadata
    """
    try:
        # Validate API key
        _validate_api_key()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
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
        raise

def extract_metadata_from_ifc(
        ifc_file_or_path: Union[str, Path, ifcopenshell.file],
    ) -> ResultBundle:
    
    """Extract metadata from an IFC file.
    
    This function processes an IFC file to extract comprehensive metadata including:
    - Element properties and attributes
    - Classification data
    - System assignments
    - Parent-child relationships
    - Material information
    - Property sets and quantities
    
    The extracted data is organized into a structured format and returned in a ResultBundle.

    Args:
        ifc_file_or_path (Union[str, Path, ifcopenshell.file]): Either a path to an IFC file or an already loaded IFC model

    Returns:
        ResultBundle: A bundle containing:
            - dataframe: pandas DataFrame with all extracted metadata
            - json: Dictionary containing the complete metadata structure
            - summary: Summary statistics

    Example:
        >>> result = extract_metadata_from_ifc("path/to/model.ifc")
        >>> df = result.to_df()  # Get the DataFrame
        >>> json_data = result.to_dict()  # Get the JSON data
    """

    result_bundle = extract_metadata_from_ifc_privat(
        ifc_file_or_path=ifc_file_or_path
    )

    return result_bundle