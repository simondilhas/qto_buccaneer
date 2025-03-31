import pandas as pd
from pathlib import Path
import os
import shutil
import ifcopenshell
from .utils.ifc_loader import IfcLoader
from typing import Union, List, Optional

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

def enrich_ifc_with_df(ifc_file: str, 
               df_for_ifc_enrichment: pd.DataFrame,
               key: str = "LongName",
               pset_name: str = "Pset_Enrichment",
               ifc_entity: Optional[str] = None) -> str:
    """
    Enrich IFC elements with data from a DataFrame using a matching key.

    Args:
        ifc_file: Path to the IFC file
        df_for_ifc_enrichment: DataFrame containing enrichment data
        key: Attribute name to match IFC elements (e.g. "LongName", "GlobalId")
        pset_name: Name for the property set storing enriched data
        ifc_entity: Type of IFC entity to enrich (if None, enriches all suitable elements)

    Notes:
        - Matches any IFC entity type with matching key value
        - GlobalId is the only guaranteed unique key
        - Overwrites existing property set if same name exists

    Returns:
        Path to the new enriched IFC file
    """
    # Create new IFC file
    output_path = Path(ifc_file)
    new_ifc_path = str(output_path.parent / f"{output_path.stem}_enriched{output_path.suffix}")
    shutil.copy2(ifc_file, new_ifc_path)
    
    try:
        # Open new IFC file for modification
        new_ifc = ifcopenshell.open(new_ifc_path)
        
        # Process each element in our enrichment data
        for _, element_data in df_for_ifc_enrichment.iterrows():
            element = new_ifc.by_guid(element_data['GlobalId'])
            
            if element is not None:
                # Create or update property set
                # Find existing property set or create new one
                existing_pset = None
                for rel in element.IsDefinedBy:
                    if hasattr(rel, 'RelatingPropertyDefinition'):
                        pdef = rel.RelatingPropertyDefinition
                        if pdef.is_a('IfcPropertySet') and pdef.Name == pset_name:
                            existing_pset = pdef
                            break
                
                if not existing_pset:
                    existing_pset = new_ifc.create_entity(
                        "IfcPropertySet",
                        GlobalId=ifcopenshell.guid.new(),
                        Name=pset_name,
                        Description="Enriched properties",
                        HasProperties=[]
                    )
                    new_ifc.create_entity(
                        "IfcRelDefinesByProperties",
                        GlobalId=ifcopenshell.guid.new(),
                        RelatedObjects=[element],
                        RelatingPropertyDefinition=existing_pset
                    )
                
                # Add new properties
                # Exclude both GlobalId and the key column
                columns_to_add = [col for col in df_for_ifc_enrichment.columns 
                                if col != 'GlobalId' and col != key]
                
                for column in columns_to_add:
                    value = element_data[column]
                    if pd.notna(value):
                        if isinstance(value, bool):
                            ifc_value = new_ifc.create_entity("IfcBoolean", value)
                        elif isinstance(value, str):
                            ifc_value = new_ifc.create_entity("IfcText", str(value))
                        elif isinstance(value, (int, float)):
                            ifc_value = new_ifc.create_entity("IfcReal", float(value))
                        else:
                            ifc_value = new_ifc.create_entity("IfcText", str(value))
                        
                        prop = new_ifc.create_entity(
                            "IfcPropertySingleValue",
                            Name=column,
                            NominalValue=ifc_value
                        )
                        existing_pset.HasProperties = list(existing_pset.HasProperties) + [prop]
        
        # Save the enriched IFC file
        new_ifc.write(new_ifc_path)
        return new_ifc_path
        
    except Exception as e:
        if os.path.exists(new_ifc_path):
            os.remove(new_ifc_path)
        raise

