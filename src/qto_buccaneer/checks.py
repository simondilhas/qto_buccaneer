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
from qto_buccaneer.utils.result_bundle import ResultBundle
from qto_buccaneer.tools.checks.compare_room_names import _create_comparison_df, _create_summary_data, _export_to_excel, _extract_ifc_rooms, _extract_excel_rooms, _create_error_result_bundle


def compare_room_names(
    metadata_actual_df: pd.DataFrame,
    target_program_df: pd.DataFrame,
    target_room_name_column: str = "Raumtypenname",
    actual_room_name_column: str = "Name",
    output_dir: Optional[str] = None,
    building_name: Optional[str] = None,
    layout_config: Optional[ExcelLayoutConfig] = None
) -> ResultBundle:
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
        ResultBundle: A ResultBundle containing the comparison results
    """
    try:
        # Extract and normalize room names from both sources
        ifc_rooms, ifc_spaces_df = _extract_ifc_rooms(metadata_actual_df, actual_room_name_column)
        excel_rooms = _extract_excel_rooms(target_program_df, target_room_name_column)
        
        # Create detailed comparison DataFrame
        detailed_df = _create_comparison_df(ifc_rooms, excel_rooms, ifc_spaces_df, actual_room_name_column)
        
        # Create summary data
        result_data = _create_summary_data(ifc_rooms, excel_rooms)
        
        # Create ResultBundle
        result_bundle = ResultBundle(
            dataframe=detailed_df,
            json=result_data,
            folderpath=Path(output_dir) if output_dir else None,
            summary=result_data,
        )
        
        # Export to Excel if output directory provided
        if output_dir:
            _export_to_excel(result_bundle, output_dir, building_name)
        
        return result_bundle
        
    except Exception as e:
        print(f"Error comparing room names: {str(e)}")
        import traceback
        traceback.print_exc()
        return _create_error_result_bundle(str(e))


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


