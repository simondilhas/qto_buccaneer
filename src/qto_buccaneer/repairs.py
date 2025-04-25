from typing import Union, List, Dict, Any, Optional
from pathlib import Path
import ifcopenshell
from .utils.ifc_loader import IfcLoader

def parse_filter(filter_str: str) -> Dict[str, Any]:
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

def apply_filter(loader: IfcLoader, filter_str: str) -> List[Any]:
    """
    Apply a filter to the IFC model and return matching elements.
    
    Args:
        loader: IfcLoader instance
        filter_str: Filter string in format "type=IfcSpace AND LongName=TRH"
        
    Returns:
        List of matching IFC elements
    """
    conditions = parse_filter(filter_str)
    if not conditions:
        return []
    
    # Get all elements of the specified type, or all IfcProduct elements if no type specified
    type_condition = next((c for c in conditions if isinstance(c, dict) and c['field'] == 'type'), None)
    if type_condition:
        elements = loader.model.by_type(type_condition['value'])
        if not elements:
            return []
    else:
        print(f"Warning: No type specified in filter '{filter_str}'. Will check all IfcProduct elements.")
        elements = loader.model.by_type("IfcProduct")
    
    # Apply remaining conditions
    filtered_elements = []
    for element in elements:
        matches = True
        for condition in conditions:
            if isinstance(condition, dict) and condition['field'] != 'type':
                value = getattr(element, condition['field'], None)
                if condition['op'] == '=':
                    matches = matches and str(value) == condition['value']
                elif condition['op'] == '!=':
                    matches = matches and str(value) != condition['value']
                elif condition['op'] == '>':
                    matches = matches and float(value) > float(condition['value'])
                elif condition['op'] == '<':
                    matches = matches and float(value) < float(condition['value'])
        
        if matches:
            filtered_elements.append(element)
    
    return filtered_elements

def apply_change_value(element: Any, field: str, value: Any, model: Any = None) -> None:
    """
    Change a value of an IFC element.
    
    Args:
        element: IFC element
        field: Field name to change (can be direct attribute or property set value)
        value: New value
        model: The ifcopenshell.file object (required for property set operations)
    """
    # Check if it's a property set value (format: PsetName.PropertyName)
    if '.' in field:
        if model is None:
            raise ValueError("Model parameter is required for property set operations")
            
        pset_name, prop_name = field.split('.')
        
        # Debug: Print all property sets and their properties
        print(f"\nDebug: Checking property sets for element {element.is_a()} (GlobalId: {getattr(element, 'GlobalId', 'No GlobalId')})")
        for definition in getattr(element, "IsDefinedBy", []):
            if not hasattr(definition, "RelatingPropertyDefinition"):
                continue
                
            prop_def = definition.RelatingPropertyDefinition
            if prop_def is None:
                continue
                
            if prop_def.is_a("IfcPropertySet"):
                print(f"  Property Set: {prop_def.Name}")
                for prop in getattr(prop_def, "HasProperties", []):
                    print(f"    - Property: {prop.Name} (Value: {getattr(prop, 'NominalValue', getattr(prop, 'Value', 'No Value'))})")
        
        # Find the property set
        pset = None
        for definition in getattr(element, "IsDefinedBy", []):
            if not hasattr(definition, "RelatingPropertyDefinition"):
                continue
                
            prop_def = definition.RelatingPropertyDefinition
            if prop_def is None:
                continue
                
            if prop_def.is_a("IfcPropertySet") and prop_def.Name.lower() == pset_name.lower():
                pset = prop_def
                break
        
        if pset is None:
            raise ValueError(f"Property set '{pset_name}' not found on element")
        
        # Find the property
        prop = None
        for existing_prop in getattr(pset, "HasProperties", []):
            if existing_prop.Name.lower() == prop_name.lower():
                prop = existing_prop
                break
        
        if prop is None:
            raise ValueError(f"Property '{prop_name}' not found in property set '{pset_name}'")
        
        # Update the property value
        if hasattr(prop, "NominalValue"):
            # Get the existing value to determine its type
            existing_value = prop.NominalValue
            if existing_value is not None:
                # Create new value with the same type as the existing value
                if existing_value.is_a("IfcLabel"):
                    prop.NominalValue = model.create_entity("IfcLabel", str(value))
                elif existing_value.is_a("IfcBoolean"):
                    prop.NominalValue = model.create_entity("IfcBoolean", bool(value))
                elif existing_value.is_a("IfcInteger"):
                    prop.NominalValue = model.create_entity("IfcInteger", int(value))
                elif existing_value.is_a("IfcReal"):
                    prop.NominalValue = model.create_entity("IfcReal", float(value))
                elif existing_value.is_a("IfcText"):
                    prop.NominalValue = model.create_entity("IfcText", str(value))
                else:
                    prop.NominalValue = value
            else:
                prop.NominalValue = value
        elif hasattr(prop, "Value"):
            # Get the existing value to determine its type
            existing_value = prop.Value
            if existing_value is not None:
                # Create new value with the same type as the existing value
                if existing_value.is_a("IfcLabel"):
                    prop.Value = model.create_entity("IfcLabel", str(value))
                elif existing_value.is_a("IfcBoolean"):
                    prop.Value = model.create_entity("IfcBoolean", bool(value))
                elif existing_value.is_a("IfcInteger"):
                    prop.Value = model.create_entity("IfcInteger", int(value))
                elif existing_value.is_a("IfcReal"):
                    prop.Value = model.create_entity("IfcReal", float(value))
                elif existing_value.is_a("IfcText"):
                    prop.Value = model.create_entity("IfcText", str(value))
                else:
                    prop.Value = value
            else:
                prop.Value = value
        else:
            raise ValueError(f"Property '{prop_name}' has no value attribute to update")
    else:
        # Handle direct attribute
        if hasattr(element, field):
            setattr(element, field, value)
        else:
            raise AttributeError(f"Element has no attribute '{field}'")

def apply_repair(ifc_path_or_model: Union[str, ifcopenshell.file], repair: Dict[str, Any]) -> None:
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
    
    # Apply filter to get matching elements
    elements = apply_filter(loader, repair['filter'])
    print(f"Found {len(elements)} matching elements")
    
    if not elements:
        print("Warning: No elements found matching the filter criteria")
        return
    
    # Apply actions to each element
    for action in repair['actions']:
        if action.get('change_value'):
            field = action['change_value']['field']
            value = action['change_value']['value']
            print(f"\nApplying change: Setting {field} to {value}")
            
            for element in elements:
                try:
                    global_id = getattr(element, 'GlobalId', 'No GlobalId')
                    print(f"  - Processing element: {element.is_a()} (GlobalId: {global_id})")
                    apply_change_value(element, field, value, model)
                    print(f"    ✓ Successfully updated {field}")
                except Exception as e:
                    print(f"    ✗ Error updating {field}: {str(e)}")
    
    # Save changes if input was a file path
    if isinstance(ifc_path_or_model, str):
        try:
            model.write(ifc_path_or_model)
            print(f"\n✓ Successfully saved changes to {ifc_path_or_model}")
        except Exception as e:
            print(f"\n✗ Error saving changes: {str(e)}")

def apply_repairs(ifc_path_or_model: Union[str, ifcopenshell.file], config: Dict[str, Any], building_name: str, output_dir: Optional[Union[str, Path]] = None) -> str:
    """
    Apply repairs to an IFC model for a specific building.
    
    Args:
        ifc_path_or_model: Path to IFC file or ifcopenshell.file object
        config: Project configuration dictionary containing buildings and their repairs
        building_name: Name of the building to apply repairs for
        output_dir: Optional directory to save the repaired model. If None, overwrites the input file.
        
    Returns:
        str: Path to the repaired IFC file
    """
    print(f"\n=== Processing building: {building_name} ===")
    
    # Find the building in the config
    building = next((b for b in config['buildings'] if b['name'] == building_name), None)
    if not building:
        print(f"✗ Error: Building '{building_name}' not found in config")
        return str(ifc_path_or_model) if isinstance(ifc_path_or_model, str) else ""
    
    # Get repairs for this building
    repairs = building.get('repairs', [])
    if not repairs:
        print(f"ℹ Info: No repairs defined for building '{building_name}'")
        return str(ifc_path_or_model) if isinstance(ifc_path_or_model, str) else ""
    
    print(f"Found {len(repairs)} repair rules to apply")
    
    # Load IFC model
    loader = IfcLoader(ifc_path_or_model)
    
    # Apply each repair
    for repair in repairs:
        apply_repair(loader.model, repair)
    
    # Determine output path
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(ifc_path_or_model, str):
            output_path = output_dir / Path(ifc_path_or_model).name
        else:
            output_path = output_dir / f"{building_name}_repaired.ifc"
    else:
        output_path = ifc_path_or_model if isinstance(ifc_path_or_model, str) else None
    
    # Save changes
    if output_path:
        try:
            loader.model.write(str(output_path))
            print(f"\n✓ Successfully saved repaired model to: {output_path}")
            return str(output_path)
        except Exception as e:
            print(f"\n✗ Error saving repaired model: {str(e)}")
            return ""
    else:
        return ""
