from qto_buccaneer.utils.ifc_loader import IfcLoader
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
import ifcopenshell
from pathlib import Path
from qto_buccaneer._utils._result_bundle import BaseResultBundle
import yaml

def enrich_ifc_with_df(
    ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
    df_for_ifc_enrichment: pd.DataFrame,
    key_ifc_element: str = "LongName",
    key_df_element: str = "LongName",
    pset_name: Optional[str] = "Pset_Enrichment",
) -> BaseResultBundle:

    """
    Enrich IFC elements with data from a DataFrame.

    Args:
        ifc_file: Either a file path, IfcLoader instance, or ifcopenshell model
        df_for_ifc_enrichment: DataFrame containing enrichment data
        key_ifc_element: Attribute name to match IFC elements (e.g. "LongName", "GlobalId")
        key_df_element: Column name in DataFrame to match with IFC elements
        pset_name: Name for the property set storing enriched data

    Returns:
        BaseResultBundle: Contains the enriched IFC model and enrichment statistics
    """
    # Initialize IFC loader
    loader = IfcLoader(ifc_file) if isinstance(ifc_file, (str, ifcopenshell.file)) else ifc_file

    # Prepare enrichment data
    if 'GlobalId' not in df_for_ifc_enrichment.columns:
        df_for_ifc_enrichment = _create_globalid_mapping(
            loader=loader,
            df_enrichment=df_for_ifc_enrichment,
            key_ifc_element=key_ifc_element,
            key_df_element=key_df_element
        )

    # Initialize enrichment statistics
    enrichment_stats = _initialize_enrichment_stats(df_for_ifc_enrichment)
    
    # Create a copy of the model for enrichment
    new_model = ifcopenshell.file()
    new_model.header = loader.model.header
    for entity in loader.model:
        new_model.add(entity)
    
    try:
        # Process each element in the DataFrame
        for _, element_data in df_for_ifc_enrichment.iterrows():
            _process_element(new_model, element_data, pset_name, key_ifc_element, key_df_element, enrichment_stats)
        
        result = _create_result_bundle(
            model=new_model,
            enrichment_stats=enrichment_stats,
            ifc_path=loader.file_path if isinstance(loader, IfcLoader) else None
        )
        result.ifc_model = new_model
        return result
        
    except Exception as e:
        raise RuntimeError(f"Failed to enrich IFC model: {str(e)}") from e
