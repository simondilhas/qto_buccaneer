from pathlib import Path
import pandas as pd
import sys
import os
import ifcopenshell
from typing import Optional, Union

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.enrich import enrich_ifc_with_df


def add_spatial_data_to_ifc(
    ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
    pset_name: str = "Pset_SpatialData",
    ifc_entity: Optional[str] = None
) -> str:
    """
    Add spatial relationship data to IFC elements as a new property set.
    
    Args:
        ifc_file: Either a file path, IfcLoader instance, or ifcopenshell model
        pset_name: Name of the property set to create
        ifc_entity: Optional filter for specific IFC entity types
        
    Returns:
        str: Path to the enriched IFC file
    """
    print("Loading IFC")
    # Create loader if needed
    if isinstance(ifc_file, (str, ifcopenshell.file)):
        loader = IfcLoader(ifc_file)
    else:
        loader = ifc_file
    
    print("Getting spatial data")
    spatial_df = loader.get_element_spatial_relationship(ifc_entity=ifc_entity)
    
    # Verify we have data to enrich with
    if spatial_df.empty:
        print("No spatial data found")
        return loader.file_path or "no_spatial_data.ifc"
    
    print(f"Found {len(spatial_df)} elements with spatial data")
    
    # Only keep necessary columns for enrichment
    #columns_to_keep = ['GlobalId', 'Building.Story', 'Story.Elevation']
    #spatial_df = spatial_df[columns_to_keep]
    print(spatial_df)
    
    print("Starting enrichment")
    try:
        result = enrich_ifc_with_df(
            ifc_file=loader,  # Pass the loader directly
            df_for_ifc_enrichment=spatial_df,
            key="GlobalId",
            pset_name=pset_name,
            file_postfix="sp"
        )
        print("Enrichment complete")
        return result
    except Exception as e:
        print(f"Enrichment failed: {e}")
        return loader.file_path or "enrichment_failed.ifc"

