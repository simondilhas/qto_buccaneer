import ifcopenshell
from qto_buccaneer.utils.ifc_loader import IfcLoader
from typing import Optional, Union
from qto_buccaneer._utils.enrich.enrich_ifc_with_metadata import enrich_ifc_with_metadata_internal
from qto_buccaneer._utils._result_bundle import BaseResultBundle
from qto_buccaneer._utils._general_tool_utils import validate_config
import logging

logger = logging.getLogger(__name__)

def enrich_ifc_with_spatial_data_internal(
    ifc_file: Union[str, IfcLoader, 'ifcopenshell.file', BaseResultBundle],
    config: dict,
) -> BaseResultBundle:
    """
    Add spatial relationship data to IFC elements as a new property set.
    
    Args:
        ifc_file: Either a file path, IfcLoader instance, ifcopenshell model, or BaseResultBundle
        config: Configuration dictionary containing:
            - description: Tool description
            - config:
                - keys:
                    - ifc: Key to match in IFC (default: "GlobalId")
                    - df: Key to match in DataFrame (default: "GlobalId")
                - pset_name: Name of the property set to create (default: "Pset_SpatialData")
                - file_postfix: Optional postfix for output filename (default: "sp")
                - output_dir: Optional output directory for the enriched IFC file
        
    Returns:
        BaseResultBundle containing:
            - ifc_model: The enriched IFC model
            - dataframe: The spatial relationship DataFrame
            - json: Summary of the enrichment process
    """
    validate_config(config)
    
    TOOL_NAME = config['description']
    logger.info(f"Starting {TOOL_NAME}")

    # Create loader if needed
    if isinstance(ifc_file, (str, ifcopenshell.file)):
        loader = IfcLoader(ifc_file)
    elif isinstance(ifc_file, BaseResultBundle):
        loader = IfcLoader(ifc_file.ifc_model)
    else:
        loader = ifc_file
    
    logger.info("Getting spatial data")
    spatial_df = loader.get_element_spatial_relationship()
    
    # Verify we have data to enrich with
    if spatial_df.empty:
        logger.warning("No spatial data found")
        summary_data = {
            TOOL_NAME: {
                "status": "Warning",
                "message": "No spatial data found",
                "elements_processed": 0
            }
        }
        return BaseResultBundle(
            ifc_model=loader.model,
            dataframe=spatial_df,
            json=summary_data
        )
    
    logger.info(f"Found {len(spatial_df)} elements with spatial data")
    
    try:
        # Prepare config for enrich_ifc_with_metadata
        enrichment_config = {
            "description": TOOL_NAME,
            "config": {
                "keys": {
                    "ifc": config.get('keys', {}).get('ifc', "GlobalId"),
                    "df": config.get('keys', {}).get('df', "GlobalId")
                },
                "pset_name": config.get('pset_name', 'Pset_SpatialData'),
                "file_postfix": config.get('file_postfix', 'sp'),
            }
        }


        
        
        # Enrich the IFC with spatial data
        result = enrich_ifc_with_metadata_internal(
            enrichment_df=spatial_df,
            ifc_file=loader,
            config=enrichment_config
        )
        
        logger.info(f"Finished {TOOL_NAME}")
        return result
        
    except Exception as e:
        logger.exception(f"{TOOL_NAME}: Processing failed")
        summary_data = {
            TOOL_NAME: {
                "status": "Error",
                "error": str(e),
                "elements_processed": 0
            }
        }
        return BaseResultBundle(
            ifc_model=loader.model,
            dataframe=None,
            json=summary_data
        )