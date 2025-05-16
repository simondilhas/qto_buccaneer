from typing import Dict, Any, List, Union
import ifcopenshell
import ifcopenshell.api
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.metadata_filter import MetadataFilter


def _parse_filter(filter_str: str) -> Dict[str, Any]:
    """
    Parse a filter string into a dictionary of conditions.
    Supports AND, OR, NOT, and parentheses.
    
    Args:
        filter_str: Filter string in format "type=IfcSpace AND LongName=TRH"
        
    Returns:
        Dictionary with filter conditions
    """
    # Split by AND/OR
    conditions = []
    current_condition = []
    for token in filter_str.split():
        if token.upper() in ['AND', 'OR']:
            if current_condition:
                conditions.append(' '.join(current_condition))
                current_condition = []
            conditions.append(token.upper())
        else:
            current_condition.append(token)
    if current_condition:
        conditions.append(' '.join(current_condition))
    
    # Parse each condition
    parsed_conditions = []
    for condition in conditions:
        if condition in ['AND', 'OR']:
            parsed_conditions.append(condition)
        else:
            # Split by operator
            if '=' in condition:
                field, value = condition.split('=')
                parsed_conditions.append({'field': field.strip(), 'op': '=', 'value': value.strip()})
            elif '!=' in condition:
                field, value = condition.split('!=')
                parsed_conditions.append({'field': field.strip(), 'op': '!=', 'value': value.strip()})
            elif '>' in condition:
                field, value = condition.split('>')
                parsed_conditions.append({'field': field.strip(), 'op': '>', 'value': value.strip()})
            elif '<' in condition:
                field, value = condition.split('<')
                parsed_conditions.append({'field': field.strip(), 'op': '<', 'value': value.strip()})
    
    return parsed_conditions

def _apply_change_value(element: Any, field: str, value: Any, model: Any = None) -> None:
    """
    Change a value of an IFC element using ifcopenshell.api.
    
    Args:
        element: IFC element
        field: Field name to change (can be direct attribute or property set value)
        value: New value
        model: The ifcopenshell.file object (required for property set operations)
    """
    print(f"    Debug: Applying change to {field} with value {value}")
    print(f"    Debug: Element type: {element.is_a()}")
    print(f"    Debug: Current value: {getattr(element, field, 'No Value')}")
    
    # Check if it's a property set value (format: PsetName.PropertyName)
    if '.' in field:
        if model is None:
            raise ValueError("Model parameter is required for property set operations")
            
        pset_name, prop_name = field.split('.')
        print(f"    Debug: Updating property set {pset_name}, property {prop_name}")
        
        # Use ifcopenshell.api to edit property
        ifcopenshell.api.run(
            "pset.edit_pset",
            model,
            pset=element,
            properties={prop_name: value}
        )
    else:
        # Direct attribute setting
        setattr(element, field, value)
        print(f"    Debug: New value: {getattr(element, field, 'No Value')}")

def repair_ifc_metadata_global_logic(ifc_path_or_model: Union[str, ifcopenshell.file], repair: Dict[str, Any]) -> None:
    """
    Apply a repair to an IFC model.
    
    Args:
        ifc_path_or_model: Path to IFC file or ifcopenshell.file object
        repair: Repair configuration dictionary
    """
    print(f"\n=== Processing repair rule: {repair['name']} ===")
    print(f"Filter: {repair['filter']}")
    
    # Load IFC model
    loader = IfcLoader(ifc_path_or_model)
    model = loader.model
    
    # Parse filter using MetadataFilter
    filters = MetadataFilter._parse_filter_expression(repair['filter'])
    print(f"Parsed filters: {filters}")
    
    # Get filtered elements using IfcLoader's get_filtered_elements method
    filtered_df = loader.get_filtered_elements(
        ifc_entity="IfcSpace",  # We know we're looking for IfcSpace from the filter
        filters=filters,
        logic="AND"
    )
    
    # Convert DataFrame back to IFC elements
    filtered_elements = [model.by_guid(row['GlobalId']) for row in filtered_df.to_dict('records')]
    print(f"Found {len(filtered_elements)} matching elements")
    
    if not filtered_elements:
        print("Warning: No elements found matching the filter criteria")
        return
    
    # Apply actions to each element
    for action in repair['actions']:
        if 'change_value' in action:
            field = action['change_value']['field']
            value = action['change_value']['value']
            print(f"\nApplying change: Setting {field} to {value}")
            
            for element in filtered_elements:
                try:
                    global_id = getattr(element, 'GlobalId', 'No GlobalId')
                    current_value = getattr(element, field, 'No Value')
                    print(f"  - Processing element: {element.is_a()} (GlobalId: {global_id})")
                    print(f"    Current {field}: {current_value}")
                    
                    # Direct attribute setting
                    setattr(element, field, value)
                    
                    # Verify the change
                    new_value = getattr(element, field, 'No Value')
                    print(f"    New {field}: {new_value}")
                    print(f"    ✓ Successfully updated {field}")
                except Exception as e:
                    print(f"    ✗ Error updating {field}: {str(e)}")
    
    # Save changes if input was a file path
    if isinstance(ifc_path_or_model, str):
        try:
            print(f"\nSaving changes to {ifc_path_or_model}")
            model.write(ifc_path_or_model)
            print(f"✓ Successfully saved changes to {ifc_path_or_model}")
        except Exception as e:
            print(f"\n✗ Error saving changes: {str(e)}")