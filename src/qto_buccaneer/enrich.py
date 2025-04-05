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

def enrich_ifc_with_df(ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
                       df_for_ifc_enrichment: pd.DataFrame,
                       key: str = "LongName",
                       pset_name: str = "Pset_Enrichment",
                       file_postfix: str = "_enriched") -> str:
    """
    Enrich IFC elements with data from a DataFrame.

    Args:
        ifc_file: Either a file path, IfcLoader instance, or ifcopenshell model
        df_for_ifc_enrichment: DataFrame containing enrichment data
        key: Attribute name to match IFC elements (e.g. "LongName", "GlobalId")
        pset_name: Name for the property set storing enriched data

    Returns:
        str: Path to the enriched IFC file
    """
    # Create loader if needed
    if isinstance(ifc_file, (str, ifcopenshell.file)):
        loader = IfcLoader(ifc_file)
    else:
        loader = ifc_file

    # If GlobalId is not in the DataFrame, create the mapping
    if 'GlobalId' not in df_for_ifc_enrichment.columns:
        print(f"Creating GlobalId mapping using {key}")
        # Get space information from IFC
        df_space_info = loader.get_space_information()
        
        # Create mapping dictionary
        key_to_globalid = dict(zip(df_space_info[key], df_space_info['GlobalId']))
        
        # Add GlobalId to enrichment DataFrame
        df_for_ifc_enrichment = df_for_ifc_enrichment.copy()
        df_for_ifc_enrichment['GlobalId'] = df_for_ifc_enrichment[key].map(key_to_globalid)
        
        # Check for missing mappings
        missing_keys = df_for_ifc_enrichment[df_for_ifc_enrichment['GlobalId'].isna()][key].unique()
        if len(missing_keys) > 0:
            print(f"Warning: Could not find GlobalIds for these {key}s: {missing_keys}")

    # Create new file path
    if loader.file_path:
        output_path = Path(loader.file_path)
        new_ifc_path = str(output_path.parent / f"{output_path.stem}_{file_postfix}{output_path.suffix}")
    else:
        new_ifc_path = "enriched.ifc"

    # Copy the model
    loader.model.write(new_ifc_path)
    
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

