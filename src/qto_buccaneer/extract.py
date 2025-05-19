import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urljoin
from qto_buccaneer._utils.extract.extract_geometry_and_metadata_via_api import calculate_geometry_json_via_api_internal
from qto_buccaneer._utils._result_bundle import BaseResultBundle, GeometryResultBundle, MetadataResultBundle
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
    ifc_file: Union[str, Path, ifcopenshell.file, BaseResultBundle],
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
        ifc_path (str): Path to the IFC file
        output_dir (str): Directory where the JSON file should be saved
        
    Returns:
        GeometryResultBundle: A GeometryResultBundle containing the geometry data and metadata
    """
    result_bundle = calculate_geometry_json_via_api_internal(
        ifc_file=ifc_file
    )
    return result_bundle
    

def extract_metadata_from_ifc(
        ifc_file_or_path: Union[str, Path, ifcopenshell.file],
    ) -> MetadataResultBundle:
    """Extract metadata from an IFC file.
    
    This function processes an IFC file to extract comprehensive metadata including:
    - Element properties and attributes
    - Classification data
    - System assignments
    - Parent-child relationships
    - Material information
    - Property sets and quantities
    
    The extracted data is organized into a structured format and returned in a MetadataResultBundle.

    Args:
        ifc_file_or_path (Union[str, Path, ifcopenshell.file]): Either a path to an IFC file or an already loaded IFC model

    Returns:
        MetadataResultBundle: A bundle containing:
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