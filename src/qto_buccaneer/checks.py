# TODO: add checks from reports here
import pandas as pd
import os
from qto_buccaneer.scripts.building_summary import BuildingSummary
from qto_buccaneer.utils import load_config
from qto_buccaneer.utils.metadata_filter import MetadataFilter
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union
from qto_buccaneer.reports import ExcelLayoutConfig

from qto_buccaneer.tools.checks.compare_target_actual import compare_target_actual
import json
from qto_buccaneer.utils._result_bundle import ResultBundle
from qto_buccaneer.tools.checks.compare_room_names import _create_comparison_df, _create_summary_data, _export_to_excel, _extract_ifc_rooms, _extract_excel_rooms, _create_error_result_bundle


def compare_room_names(
    actual_df: pd.DataFrame,
    target_df: pd.DataFrame,
    config_path: Path,
    rule_name: str,
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

