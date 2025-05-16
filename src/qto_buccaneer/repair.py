from typing import Union, List, Dict, Any, Optional
from pathlib import Path
import ifcopenshell
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer._utils.repair.apply_repair import _apply_repair
from qto_buccaneer._utils.repair.repair_ifc_metadata_global import repair_ifc_metadata_global_logic



def repair_ifc_metadata_global(ifc_path_or_model: Union[str, ifcopenshell.file], config: Dict[str, Any], output_dir: Optional[Union[str, Path]] = None) -> str:
    """
    Apply global repairs to an IFC model based on the provided configuration.
    
    Args:
        ifc_path_or_model: Path to IFC file or ifcopenshell.file object
        config: Project configuration dictionary containing repairs section with named repair rules
        output_dir: Optional directory to save the repaired model. If None, overwrites the input file.
        
    Returns:
        str: Path to the repaired IFC file
    """
    print("\n=== Processing global repairs ===")
    
    # Get repairs section from config
    repairs = config.get('repairs', {})
    if not repairs:
        print("ℹ Info: No repairs section found in config")
        return str(ifc_path_or_model) if isinstance(ifc_path_or_model, str) else ""
    
    # Get all repair rules
    repair_rules = {k: v for k, v in repairs.items() if isinstance(v, dict) and 'config' in v}
    if not repair_rules:
        print("ℹ Info: No repair rules defined in repairs section")
        return str(ifc_path_or_model) if isinstance(ifc_path_or_model, str) else ""
    
    print(f"Found {len(repair_rules)} repair rules to apply")
    
    # Load IFC model
    loader = IfcLoader(ifc_path_or_model)
    
    # Apply each repair rule
    for rule_name, rule_data in repair_rules.items():
        print(f"\nProcessing rule: {rule_name}")
        if 'description' in rule_data:
            print(f"Description: {rule_data['description']}")
        
        # Extract repair configuration
        repair_config = rule_data['config']
        if not isinstance(repair_config, dict):
            print(f"✗ Error: Invalid config format for rule '{rule_name}'")
            continue
            
        # Convert repair format to match what repair_ifc_metadata_global_logic expects
        repair = {
            'name': rule_name,
            'filter': repair_config['filter'],
            'actions': repair_config['actions']  # Pass actions directly
        }
        
        # Apply the repair
        try:
            repair_ifc_metadata_global_logic(loader.model, repair)
            print(f"✓ Successfully applied rule: {rule_name}")
        except Exception as e:
            print(f"✗ Error applying rule '{rule_name}': {str(e)}")
    
    # Determine output path
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(ifc_path_or_model, str):
            output_path = output_dir / Path(ifc_path_or_model).name
        else:
            output_path = output_dir / "repaired.ifc"
    else:
        output_path = ifc_path_or_model if isinstance(ifc_path_or_model, str) else None
    
    # Save the modified model
    if output_path:
        try:
            loader.model.write(str(output_path))
            print(f"✓ Successfully saved repaired model to: {output_path}")
        except Exception as e:
            print(f"✗ Error saving repaired model: {str(e)}")
            return str(ifc_path_or_model) if isinstance(ifc_path_or_model, str) else ""
    
    return str(output_path) if output_path else ""

def repair_ifc_metadata_per_building(ifc_path_or_model: Union[str, ifcopenshell.file], config: Dict[str, Any], building_name: str, output_dir: Optional[Union[str, Path]] = None) -> str:
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
        _apply_repair(loader.model, repair)
    
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