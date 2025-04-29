import pandas as pd
from pathlib import Path
import os
import shutil
import ifcopenshell
from .utils.ifc_loader import IfcLoader
from .utils.result_bundle import ResultBundle
from typing import Union, List, Optional, Dict, Any, Tuple
import yaml

def _create_globalid_mapping(loader: IfcLoader, 
                           df_enrichment: pd.DataFrame, 
                           key: str) -> pd.DataFrame:
    """Create GlobalId mapping for enrichment data."""
    df_space_info = loader.get_space_information()
    key_to_globalid = dict(zip(df_space_info[key], df_space_info['GlobalId']))
    
    df_enrichment = df_enrichment.copy()
    df_enrichment['GlobalId'] = df_enrichment[key].map(key_to_globalid)
    
    missing_keys = df_enrichment[df_enrichment['GlobalId'].isna()][key].unique()
    if len(missing_keys) > 0:
        print(f"Warning: Could not find GlobalIds for these {key}s: {missing_keys}")
    
    return df_enrichment

def _get_or_create_property_set(ifc_model: 'ifcopenshell.file', 
                              element: Any, 
                              pset_name: str) -> Any:
    """Get existing property set or create a new one."""
    for rel in element.IsDefinedBy:
        if hasattr(rel, 'RelatingPropertyDefinition'):
            pdef = rel.RelatingPropertyDefinition
            if pdef.is_a('IfcPropertySet') and pdef.Name == pset_name:
                return pdef
    
    new_pset = ifc_model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name=pset_name,
        Description="Enriched properties",
        HasProperties=[]
    )
    
    ifc_model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[element],
        RelatingPropertyDefinition=new_pset
    )
    
    return new_pset

def _create_ifc_value(ifc_model: 'ifcopenshell.file', value: Any) -> Any:
    """Create appropriate IFC value based on Python type."""
    if isinstance(value, bool):
        return ifc_model.create_entity("IfcBoolean", value)
    elif isinstance(value, str):
        return ifc_model.create_entity("IfcText", str(value))
    elif isinstance(value, (int, float)):
        return ifc_model.create_entity("IfcReal", float(value))
    else:
        return ifc_model.create_entity("IfcText", str(value))

def _add_properties_to_pset(ifc_model: 'ifcopenshell.file', 
                          pset: Any, 
                          element_data: pd.Series, 
                          exclude_columns: List[str]) -> None:
    """Add properties to property set from element data."""
    for column in [col for col in element_data.index if col not in exclude_columns]:
        value = element_data[column]
        if pd.notna(value):
            ifc_value = _create_ifc_value(ifc_model, value)
            prop = ifc_model.create_entity(
                "IfcPropertySingleValue",
                Name=column,
                NominalValue=ifc_value
            )
            pset.HasProperties = list(pset.HasProperties) + [prop]

def _initialize_enrichment_stats(df_enrichment: pd.DataFrame) -> Dict[str, Any]:
    """Initialize the enrichment statistics dictionary."""
    return {
        "total_elements": len(df_enrichment),
        "successfully_enriched": 0,
        "failed_elements": [],
        "attributes_added": 0,
        "property_sets_created": 0,
        "elements_by_type": {}
    }

def _update_element_stats(stats: Dict[str, Any], 
                        element_type: str, 
                        attributes_added: int) -> None:
    """Update statistics for a specific element type."""
    if element_type not in stats["elements_by_type"]:
        stats["elements_by_type"][element_type] = {
            "count": 0,
            "attributes_added": 0
        }
    stats["elements_by_type"][element_type]["count"] += 1
    stats["elements_by_type"][element_type]["attributes_added"] += attributes_added

def _process_element(new_ifc: 'ifcopenshell.file',
                    element_data: pd.Series,
                    pset_name: str,
                    key: str,
                    stats: Dict[str, Any]) -> None:
    """Process a single element for enrichment."""
    element = new_ifc.by_guid(element_data['GlobalId'])
    if element is None:
        return

    try:
        pset = _get_or_create_property_set(new_ifc, element, pset_name)
        if pset is not None:
            stats["property_sets_created"] += 1
        
        # Count attributes before adding
        initial_prop_count = len(pset.HasProperties) if pset else 0
        
        _add_properties_to_pset(new_ifc, pset, element_data, ['GlobalId', key])
        
        # Update statistics
        final_prop_count = len(pset.HasProperties) if pset else 0
        attributes_added = final_prop_count - initial_prop_count
        stats["attributes_added"] += attributes_added
        stats["successfully_enriched"] += 1
        
        # Track elements by type
        element_type = element.is_a()
        _update_element_stats(stats, element_type, attributes_added)
        
    except Exception as e:
        stats["failed_elements"].append({
            "GlobalId": element_data['GlobalId'],
            "error": str(e)
        })

def _create_output_path(loader: IfcLoader,
                       file_postfix: str,
                       output_dir: Optional[str] = None) -> Tuple[Path, str]:
    """Create the output path for the enriched IFC file."""
    if loader.file_path:
        input_path = Path(loader.file_path)
        if output_dir:
            output_path = Path(output_dir) / f"{input_path.stem}{file_postfix}{input_path.suffix}"
        else:
            output_path = input_path.parent / f"{input_path.stem}{file_postfix}{input_path.suffix}"
    else:
        output_path = Path("enriched.ifc")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path, str(output_path)

def enrich_ifc_with_df(ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
                      df_for_ifc_enrichment: pd.DataFrame,
                      key: str = "LongName",
                      pset_name: str = "Pset_Enrichment",
                      file_postfix: str = "_enriched",
                      output_dir: Optional[str] = None) -> ResultBundle:
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
    # Create loader if needed
    if isinstance(ifc_file, (str, ifcopenshell.file)):
        loader = IfcLoader(ifc_file)
    else:
        loader = ifc_file

    # Create GlobalId mapping if needed
    if 'GlobalId' not in df_for_ifc_enrichment.columns:
        df_for_ifc_enrichment = _create_globalid_mapping(loader, df_for_ifc_enrichment, key)

    # Create output path
    output_path, new_ifc_path = _create_output_path(loader, file_postfix, output_dir)

    # Initialize enrichment statistics
    enrichment_stats = _initialize_enrichment_stats(df_for_ifc_enrichment)

    # Copy the model
    loader.model.write(new_ifc_path)
    
    try:
        # Open new IFC file for modification
        new_ifc = ifcopenshell.open(new_ifc_path)
        
        # Process each element
        for _, element_data in df_for_ifc_enrichment.iterrows():
            _process_element(new_ifc, element_data, pset_name, key, enrichment_stats)
        
        # Save the enriched IFC file
        new_ifc.write(new_ifc_path)
        
        # Create result bundle with properly formatted YAML
        result = ResultBundle(
            dataframe=None,
            json={
                "ifc_path": new_ifc_path,
                "output_dir": str(output_path.parent),
                "helper_data": [{
                    "metadata": {
                        "extracted_ifc_metadata": {
                            "total_elements": len(loader.model.by_type("IfcRoot")),
                            "total_classifications": len(loader.model.by_type("IfcClassification")),
                            "total_systems": len(loader.model.by_type("IfcSystem")),
                            "total_attributes": sum(len(e.get_info()) for e in loader.model.by_type("IfcRoot")),
                            "total_unique_attributes": len(set(
                                attr for e in loader.model.by_type("IfcRoot")
                                for attr in e.get_info().keys()
                            ))
                        }
                    }
                }, yaml.safe_dump(enrichment_stats, sort_keys=False, default_flow_style=False, allow_unicode=True)]
            },
            folderpath=output_path.parent,
            summary=yaml.safe_dump(enrichment_stats, sort_keys=False, default_flow_style=False, allow_unicode=True)
        )
        
        return result
        
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

