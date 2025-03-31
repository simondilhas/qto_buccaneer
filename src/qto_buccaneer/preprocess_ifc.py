from pathlib import Path
import pandas as pd
import sys
import os
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.enriche import enrich_ifc_with_df


def add_spatial_data_to_ifc(ifc_file: str, 
                           pset_name: str = "Pset_SpatialData",
                           ifc_entity: Optional[str] = None) -> str:
    """
    Add spatial relationship data to IFC elements as a new property set.
    """
    print("Loading IFC")
    ifc_loader = IfcLoader(ifc_file)
    
    print("Getting spatial data")
    spatial_df = ifc_loader.get_element_spatial_relationship(ifc_entity=ifc_entity)
    
    # Verify we have data to enrich with
    if spatial_df.empty:
        print("No spatial data found")
        return ifc_file
    
    print(f"Found {len(spatial_df)} elements with spatial data")
    
    # Only keep necessary columns for enrichment
    #columns_to_keep = ['GlobalId', 'Building.Story', 'Story.Elevation']
    spatial_df = spatial_df[columns_to_keep]
    print(spatial_df)
    
    print("Starting enrichment")
    try:
        result = enrich_ifc_with_df(
            ifc_file=ifc_file,
            df_for_ifc_enrichment=spatial_df,
            key="GlobalId",
            pset_name=pset_name
        )
        print("Enrichment complete")
        return result
    except Exception as e:
        print(f"Enrichment failed: {e}")
        return ifc_file

if __name__ == "__main__":
    input_file = "examples/Mustermodell V1_abstractBIM.ifc"
    try:
        enriched_file = add_spatial_data_to_ifc(input_file)
        print(f"Created: {enriched_file}")
    except Exception as e:
        print(f"Error: {e}") 