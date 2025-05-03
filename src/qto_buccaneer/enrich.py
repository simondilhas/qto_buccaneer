import pandas as pd
from pathlib import Path
import os
import shutil
import ifcopenshell
from .utils.ifc_loader import IfcLoader
from ._utils._result_bundle import ResultBundle
from typing import Union, List, Optional, Dict, Any, Tuple
import yaml
from qto_buccaneer._utils.enrich.enrich_ifc_with_df import _create_globalid_mapping, _create_output_path, _initialize_enrichment_stats, _process_element, _create_result_bundle



def enrich_ifc_with_df(
    ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
    df_for_ifc_enrichment: pd.DataFrame,
    key: str = "LongName",
    pset_name: str = "Pset_Enrichment",
    file_postfix: str = "_enriched",
    output_dir: Optional[str] = None
) -> ResultBundle:
    """
    Enrich IFC elements with data from a DataFrame.

    Args:
        ifc_file: Either a file path, IfcLoader instance, or ifcopenshell model
        df_for_ifc_enrichment: DataFrame containing enrichment data
        key: Attribute name to match IFC elements (e.g. "LongName", "GlobalId")
        pset_name: Name for the property set storing enriched data
        file_postfix: Postfix to add to the output filename
        output_dir: Optional output directory for the enriched IFC file

    Returns:
        ResultBundle: Contains the path to the enriched IFC file, output directory, and enrichment statistics
    """
    # Initialize IFC loader
    loader = IfcLoader(ifc_file) if isinstance(ifc_file, (str, ifcopenshell.file)) else ifc_file

    # Prepare enrichment data
    if 'GlobalId' not in df_for_ifc_enrichment.columns:
        df_for_ifc_enrichment = _create_globalid_mapping(loader, df_for_ifc_enrichment, key)

    # Set up output paths
    output_path, new_ifc_path = _create_output_path(loader, file_postfix, output_dir)
    enrichment_stats = _initialize_enrichment_stats(df_for_ifc_enrichment)

    # Create a copy of the model for enrichment
    loader.model.write(new_ifc_path)
    
    try:
        # Open and enrich the new IFC file
        new_ifc = ifcopenshell.open(new_ifc_path)
        for _, element_data in df_for_ifc_enrichment.iterrows():
            _process_element(new_ifc, element_data, pset_name, key, enrichment_stats)
        new_ifc.write(new_ifc_path)
        
        return _create_result_bundle(
            ifc_path=new_ifc_path, 
            output_dir=output_path.parent, 
            enrichment_stats=enrichment_stats, 
            model=loader.model,
            output_filepath=new_ifc_path
            )
        
    except Exception as e:
        if os.path.exists(new_ifc_path):
            os.remove(new_ifc_path)
        raise RuntimeError(f"Failed to enrich IFC file: {str(e)}") from e

def enrich_df(df_model_data: pd.DataFrame, 
              df_enrichment_data: pd.DataFrame, 
              key: str) -> pd.DataFrame:
    """
    Enrich a DataFrame with data from another DataFrame on a given key. 
    The key is the column name that is used to merge the two DataFrames.

    Args:
        df_model_data: DataFrame with model data
        df_enrichment_data: DataFrame with enrichment data
        key: str, key LongName, Name, GlobalId, Description, Pset_SpaceCommon.IsExternal
    """
    return pd.merge(
        df_model_data,
        df_enrichment_data,
        on=key,
        how='left'
    )

