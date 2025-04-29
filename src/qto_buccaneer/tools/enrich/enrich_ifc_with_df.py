from qto_buccaneer.utils.ifc_loader import IfcLoader
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import ifcopenshell
from pathlib import Path
from qto_buccaneer.utils.result_bundle import ResultBundle
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
        "enrichment_stats": {
            "total_elements": len(df_enrichment),
            "successfully_enriched": 0,
            "failed_elements": [],
            "attributes_added": 0,
            "property_sets_created": 0,
            "elements_by_type": {}
        }
    }

def _update_element_stats(stats: Dict[str, Any], 
                        element_type: str, 
                        attributes_added: int) -> None:
    """Update statistics for a specific element type."""
    if element_type not in stats["enrichment_stats"]["elements_by_type"]:
        stats["enrichment_stats"]["elements_by_type"][element_type] = {
            "count": 0,
            "attributes_added": 0
        }
    stats["enrichment_stats"]["elements_by_type"][element_type]["count"] += 1
    stats["enrichment_stats"]["elements_by_type"][element_type]["attributes_added"] += attributes_added

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
            stats["enrichment_stats"]["property_sets_created"] += 1
        
        # Count attributes before adding
        initial_prop_count = len(pset.HasProperties) if pset else 0
        
        _add_properties_to_pset(new_ifc, pset, element_data, ['GlobalId', key])
        
        # Update statistics
        final_prop_count = len(pset.HasProperties) if pset else 0
        attributes_added = final_prop_count - initial_prop_count
        stats["enrichment_stats"]["attributes_added"] += attributes_added
        stats["enrichment_stats"]["successfully_enriched"] += 1
        
        # Track elements by type
        element_type = element.is_a()
        _update_element_stats(stats, element_type, attributes_added)
        
    except Exception as e:
        stats["enrichment_stats"]["failed_elements"].append({
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

def _extract_ifc_metadata(model: ifcopenshell.file) -> Dict[str, int]:
    """Extract metadata from IFC model."""
    return {
        "total_elements": len(model.by_type("IfcRoot")),
        "total_classifications": len(model.by_type("IfcClassification")),
        "total_systems": len(model.by_type("IfcSystem")),
        "total_attributes": sum(len(e.get_info()) for e in model.by_type("IfcRoot")),
        "total_unique_attributes": len(set(
            attr for e in model.by_type("IfcRoot")
            for attr in e.get_info().keys()
        ))
    }

def _format_yaml(data: Dict) -> str:
    """Format data as YAML string."""
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)

def _create_result_bundle(
    ifc_path: str,
    output_dir: Path,
    enrichment_stats: Dict,
    model: ifcopenshell.file,
    output_filepath: str
) -> ResultBundle:
    """Create a ResultBundle with the enrichment results."""
    return ResultBundle(
        dataframe=None,
        json={
            "ifc_path": ifc_path,
            "output_dir": str(output_dir),
            "output_filepath": output_filepath,
            "helper_data": [{
                "metadata": {
                    "extracted_ifc_metadata": _extract_ifc_metadata(model)
                }
            }, enrichment_stats]
        },
        folderpath=output_dir,
        summary=enrichment_stats
    )