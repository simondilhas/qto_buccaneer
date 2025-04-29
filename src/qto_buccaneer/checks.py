# TODO: add checks from reports here
import pandas as pd
import os
from qto_buccaneer.scripts.building_summary import BuildingSummary
from qto_buccaneer.utils import load_config
from qto_buccaneer.utils.metadata_filter import MetadataFilter
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from qto_buccaneer.reports import ExcelLayoutConfig
from qto_buccaneer.tools.checks.compare_target_actual import RoomComparisonResult
from qto_buccaneer.tools.checks.compare_target_actual import BuildingComparison, _save_results, _load_filter_config, _get_check_config
import json

def compare_room_names(
    metadata_actual_df: pd.DataFrame,
    target_program_df: pd.DataFrame,
    target_room_name_column: str = "Raumtypenname",
    actual_room_name_column: str = "Name",
    output_dir: Optional[str] = None,
    building_name: Optional[str] = None,
    layout_config: Optional[ExcelLayoutConfig] = None
    ) -> dict:
    """
    Compare room names between IFC spaces and a room program.
    
    Args:
        metadata_actual_df: DataFrame containing IFC metadata including spaces (actual state)
        target_program_df: DataFrame containing room program information (target state)
        target_room_name_column: Column name in Excel containing target room names
        actual_room_name_column: Column name in IFC containing actual room names
        output_dir: Directory where Excel files should be saved
        building_name: Name of the building (used in output filenames)
        layout_config: Optional ExcelLayoutConfig for custom formatting
        
    Returns:
        dict: Dictionary containing the comparison results in a format suitable for the building summary
    """
    try:
        # Filter for IFC spaces
        ifc_spaces_df = metadata_actual_df[metadata_actual_df['IfcEntity'] == 'IfcSpace']
        
        # Get room names from IFC and convert to lowercase, filtering out None values
        ifc_rooms = set(ifc_spaces_df[actual_room_name_column].dropna().str.lower().unique())
        
        # Get room names from Excel and convert to lowercase, filtering out None values
        excel_rooms = set(target_program_df[target_room_name_column].dropna().str.lower().unique())
        
        # Create comparison DataFrame for Excel export
        all_rooms = ifc_rooms.union(excel_rooms)
        data = []
        for room in sorted(all_rooms):
            room_data = {
                "Room Name": room,
                "Status": "In Both" if room in ifc_rooms and room in excel_rooms else "Only in IFC" if room in ifc_rooms else "Only in Excel",
                "GlobalId": ""  # Default empty GlobalId
            }
            
            # Add GlobalId for rooms that exist in IFC
            if room in ifc_rooms:
                ifc_room = ifc_spaces_df[ifc_spaces_df[actual_room_name_column].str.lower() == room]
                if not ifc_room.empty:
                    room_data["GlobalId"] = ifc_room["GlobalId"].iloc[0]
            
            data.append(room_data)
            
        detailed_df = pd.DataFrame(data)
        
        # Create RoomComparisonResult instance
        comparison = RoomComparisonResult(detailed_df, ifc_rooms, excel_rooms)
        
        # Export to Excel if output directory provided
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            building_prefix = f"{building_name}_" if building_name else ""
            output_path = os.path.join(output_dir, f"{building_prefix}room_name_comparison.xlsx")
            comparison.to_excel(output_path, layout_config)
        
        return comparison.to_yaml()
        
    except Exception as e:
        print(f"Error comparing room names: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "room_comparison": {
                "status": "error",
                "summary": f"Error comparing room names: {str(e)}",
                "target": {},
                "ifc": {}
            }
        }

   
def compare_target_actual(
    target_df: pd.DataFrame,
    actual_metadata_df: pd.DataFrame,
    output_dir: str,
    config_dir: str,
    building_name: str,
) -> BuildingComparison:
    """
    Compare target and actual building data.
    
    Args:
        target_df: DataFrame containing target room data
        actual_metadata_df: DataFrame containing actual room data
        output_dir: Directory to save output files
        filter_dir: Either a YAML string or a path to a YAML file containing filter configuration
        building_name: Name of the building for output files
        
    Returns:
        BuildingComparison object containing comparison results
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load and process configuration
    filter_config = _load_filter_config(config_dir)
    check_config = _get_check_config(filter_config)
    
    # Extract configuration values
    target_key = check_config['key_target_column']
    target_area_column = check_config['area_target_column']
    actual_key = check_config['key_actual_column']
    actual_area_column = check_config['area_actual_column']
    tolerance = check_config.get('tolerance', 0.1)
    return_values = check_config.get('return_values', [])
    
    filter_str = check_config.get('filter', '')
    if filter_str:
        actual_df = MetadataFilter.filter_df_from_str(actual_metadata_df, filter_str)


    actual_df.columns = [f"{col}_actual" for col in actual_df.columns]
    target_df.columns = [f"{col}_target" for col in target_df.columns]
        
    merged_df = pd.merge(
        target_df,
        actual_df,
        how='outer',
        left_on=[target_key],
        right_on=[actual_key],
    )
    merged_df.to_excel(output_path / f"{building_name}_merged.xlsx", index=False)
    
    merged_df_1 = _calculate_differences(
        merged_df=merged_df, 
        tolerance=tolerance, 
        target_area_column=target_area_column,
        actual_area_column=actual_area_column,
        key_target_column=target_key,
        key_actual_column=actual_key
    )
    
    merged_df_1.to_excel(output_path / f"{building_name}_merged_1.xlsx", index=False)
    
    
    # Create BuildingComparison object
    comparison = BuildingComparison(merged_df, return_values=return_values, area_target_column=target_area_column, area_actual_column=actual_area_column)
    
    # Save results
    _save_results(comparison, output_path, building_name)
    
    return comparison


