import pandas as pd
from pathlib import Path
import os
import shutil
import ifcopenshell
from .utils.ifc_loader import IfcLoader
from typing import Union, List, Optional, Dict, Any

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

class EnrichmentError(Exception):
    """Base exception for enrichment-related errors"""
    pass

class InvalidDataError(EnrichmentError):
    """Exception raised for invalid input data"""
    pass

class ElementNotFoundError(EnrichmentError):
    """Exception raised when an element cannot be found in the IFC model"""
    pass

class PropertyCreationError(EnrichmentError):
    """Exception raised when a property cannot be created"""
    pass

def enrich_ifc_with_df(ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
                       df_for_ifc_enrichment: pd.DataFrame,
                       key: str = "LongName",
                       pset_name: str = "Pset_Enrichment",
                       file_postfix: str = "_enriched",
                       output_dir: Optional[str] = None,
                       skip_errors: bool = False) -> str:
    """
    Enrich IFC elements with data from a DataFrame.
    
    Args:
        ifc_file: Path to IFC file, IfcLoader instance, or ifcopenshell.file
        df_for_ifc_enrichment: DataFrame with enrichment data
        key: Column name to use for matching elements (default: "LongName")
        pset_name: Property set name for new properties (default: "Pset_Enrichment")
        file_postfix: Postfix to add to output file name (default: "_enriched")
        output_dir: Output directory (default: same as input file)
        skip_errors: Whether to skip errors and continue (default: False)
        
    Returns:
        Path to enriched IFC file
    """
    new_ifc_path = None
    errors = []
    
    try:
        # Validate input data
        if df_for_ifc_enrichment is None or df_for_ifc_enrichment.empty:
            raise InvalidDataError("Enrichment DataFrame is empty or None")
            
        # Create loader if needed
        if isinstance(ifc_file, (str, ifcopenshell.file)):
            loader = IfcLoader(ifc_file)
        else:
            loader = ifc_file

        # Create new file path first
        if loader.file_path:
            input_path = Path(loader.file_path)
            if output_dir:
                output_path = Path(output_dir) / f"{input_path.stem}{file_postfix}{input_path.suffix}"
            else:
                output_path = input_path.parent / f"{input_path.stem}{file_postfix}{input_path.suffix}"
        else:
            output_path = Path("enriched.ifc")

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        new_ifc_path = str(output_path)

        # Copy the model
        loader.model.write(new_ifc_path)

        # Verificăm GlobalId sau cheia specificată
        if 'GlobalId' not in df_for_ifc_enrichment.columns:
            if key not in df_for_ifc_enrichment.columns:
                raise InvalidDataError(f"Key column '{key}' not found in enrichment DataFrame")
                
            print(f"Creating GlobalId mapping using {key}")
            # Get space information from IFC
            df_space_info = loader.get_space_information()
            
            if key not in df_space_info.columns:
                raise InvalidDataError(f"Key column '{key}' not found in IFC space information")
            
            # Create mapping dictionary
            key_to_globalid = dict(zip(df_space_info[key], df_space_info['GlobalId']))
            
            # Add GlobalId to enrichment DataFrame
            df_for_ifc_enrichment = df_for_ifc_enrichment.copy()
            df_for_ifc_enrichment['GlobalId'] = df_for_ifc_enrichment[key].map(key_to_globalid)
            
            # Check for missing mappings
            missing_keys = df_for_ifc_enrichment[df_for_ifc_enrichment['GlobalId'].isna()][key].unique()
            if len(missing_keys) > 0:
                print(f"Warning: Could not find GlobalIds for these {key}s: {missing_keys}")
                if not skip_errors and len(missing_keys) == len(df_for_ifc_enrichment):
                    raise ElementNotFoundError(f"Could not find any matching elements in the IFC model using key '{key}'")

        # Open new IFC file for modification
        new_ifc = ifcopenshell.open(new_ifc_path)
        
        # Organizăm proprietățile pe seturi de proprietăți
        pset_properties = {}
        
        # Process each element in our enrichment data
        for idx, element_data in df_for_ifc_enrichment.iterrows():
            try:
                # Skip rows with missing GlobalId
                if pd.isna(element_data.get('GlobalId')):
                    if not skip_errors:
                        errors.append(f"Row {idx}: Missing GlobalId")
                    continue
                
                element = new_ifc.by_guid(element_data['GlobalId'])
                
                if element is None:
                    if not skip_errors:
                        errors.append(f"Row {idx}: Element with GlobalId {element_data['GlobalId']} not found")
                    continue
                
                # Organizăm proprietățile pe seturi de proprietăți
                pset_properties = {}
                
                # Add new properties
                columns_to_add = [col for col in df_for_ifc_enrichment.columns 
                                if col != 'GlobalId' and col != key]
                
                for column in columns_to_add:
                    try:
                        value = element_data[column]
                        if pd.notna(value):
                            # Verificăm dacă proprietatea are format Pset.Property
                            if '.' in column:
                                parts = column.split('.')
                                if len(parts) >= 2:
                                    current_pset = '.'.join(parts[:-1])
                                    prop_name = parts[-1]
                                    
                                    if current_pset not in pset_properties:
                                        pset_properties[current_pset] = []
                                    
                                    pset_properties[current_pset].append((prop_name, value))
                            else:
                                # Proprietate fără pset specificat - folosim pset_name implicit
                                if pset_name not in pset_properties:
                                    pset_properties[pset_name] = []
                                
                                pset_properties[pset_name].append((column, value))
                    except Exception as prop_error:
                        if not skip_errors:
                            errors.append(f"Row {idx}, Column {column}: {str(prop_error)}")
                
                # Adăugăm proprietățile organizate pe seturi
                for current_pset_name, properties in pset_properties.items():
                    if not properties:
                        continue
                        
                    # Găsim sau creăm setul de proprietăți
                    existing_pset = None
                    for rel in element.IsDefinedBy:
                        if hasattr(rel, 'RelatingPropertyDefinition'):
                            pdef = rel.RelatingPropertyDefinition
                            if pdef.is_a('IfcPropertySet') and pdef.Name == current_pset_name:
                                existing_pset = pdef
                                break
                    
                    if not existing_pset:
                        existing_pset = new_ifc.create_entity(
                            "IfcPropertySet",
                            GlobalId=ifcopenshell.guid.new(),
                            Name=current_pset_name,
                            Description=f"Properties for {current_pset_name}",
                            HasProperties=[]
                        )
                        new_ifc.create_entity(
                            "IfcRelDefinesByProperties",
                            GlobalId=ifcopenshell.guid.new(),
                            RelatedObjects=[element],
                            RelatingPropertyDefinition=existing_pset
                        )
                    
                    # Adăugăm proprietățile la setul curent
                    for prop_name, prop_value in properties:
                        # Verificăm dacă proprietatea există deja
                        existing_prop = None
                        for prop in existing_pset.HasProperties:
                            if prop.Name == prop_name:
                                existing_prop = prop
                                break
                        
                        # Creăm valoarea IFC
                        if isinstance(prop_value, bool):
                            ifc_value = new_ifc.create_entity("IfcBoolean", prop_value)
                        elif isinstance(prop_value, str):
                            ifc_value = new_ifc.create_entity("IfcText", str(prop_value))
                        elif isinstance(prop_value, (int, float)):
                            ifc_value = new_ifc.create_entity("IfcReal", float(prop_value))
                        else:
                            ifc_value = new_ifc.create_entity("IfcText", str(prop_value))
                        
                        if existing_prop:
                            # Actualizăm proprietatea existentă
                            existing_prop.NominalValue = ifc_value
                        else:
                            # Creăm o proprietate nouă
                            prop = new_ifc.create_entity(
                                "IfcPropertySingleValue",
                                Name=prop_name,
                                NominalValue=ifc_value
                            )
                            existing_pset.HasProperties = list(existing_pset.HasProperties) + [prop]
            except Exception as elem_error:
                if not skip_errors:
                    errors.append(f"Row {idx}: {str(elem_error)}")
        
        # If there were errors and we're not skipping them, raise an exception
        if errors and not skip_errors:
            error_msg = f"Encountered {len(errors)} errors during enrichment:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n... and {len(errors) - 10} more errors"
            raise PropertyCreationError(error_msg)
        
        # Save the enriched IFC file
        new_ifc.write(new_ifc_path)
        return new_ifc_path
        
    except Exception as e:
        # Clean up temporary file if something went wrong
        if new_ifc_path and os.path.exists(new_ifc_path):
            try:
                os.remove(new_ifc_path)
            except OSError:
                pass  # Ignorăm erorile la ștergerea fișierului
        raise

