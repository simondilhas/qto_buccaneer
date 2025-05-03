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

from qto_buccaneer._utils.checks.compare_target_actual import compare_target_actual
import json
from qto_buccaneer._utils._result_bundle import ResultBundle
from qto_buccaneer._utils.checks.compare_room_names import _create_comparison_df, _create_summary_data, _export_to_excel, _extract_ifc_rooms, _extract_excel_rooms, _create_error_result_bundle
import logging
from qto_buccaneer._utils._general_tool_utils import unpack_dataframe, validate_df, validate_config

logger = logging.getLogger(__name__)

def compare_room_names(
    df_target: Union[pd.DataFrame, ResultBundle],
    df_actual: Union[pd.DataFrame, ResultBundle],
    config: Dict,
    output_path: Path,
    layout_config: Optional[ExcelLayoutConfig] = None
) -> ResultBundle:
    """
    Compare room names between IFC spaces and a room program, following the tool_template pattern.
    """
    validate_config(config)

    TOOL_NAME = config.get('tool_name', 'compare_room_names')
    logger.info(f"Starting {TOOL_NAME}")

    # 1. Unpack DataFrame
    target_df = unpack_dataframe(df_target)
    actual_df = unpack_dataframe(df_actual)


    # 2. Extract required columns from config
    required_actual_columns = config.get('actual_columns', ['Name'])
    required_target_columns = config.get('target_columns', ['Raumtypenname'])

    # 3. Validate DataFrame
    validation = validate_df(target_df, required_columns=required_actual_columns, df_name="Actual DataFrame")
    if not validation['is_valid']:
        raise ValueError(f"Validation failed: {validation['errors']}")

    validation = validate_df(actual_df, required_columns=required_target_columns, df_name="Target DataFrame")
    if not validation['is_valid']:
        raise ValueError(f"Validation failed: {validation['errors']}")


    # 4. Process DataFrame
    result_bundle = _process_room_name_comparison(
        target_df,
        actual_df,
        config,
        output_path,
        layout_config
    )

    # 5. Save results
    logger.info(f"Saving results to {output_path}")
    result_bundle.save_excel(output_path)
    result_bundle.save_summary(output_path.with_suffix(".yml"))

    logger.info(f"Finished {TOOL_NAME}")
    return result_bundle

def _process_room_name_comparison(
    target_df: pd.DataFrame,
    actual_df: pd.DataFrame,
    config: Dict,
    output_path: Path,
    layout_config: Optional[ExcelLayoutConfig] = None
) -> ResultBundle:
    """
    Core logic for room name comparison.
    """
    try:
        # Extract and normalize room names from both sources
        target_df = config['target_df']
        actual_room_name_column = config.get('actual_room_name_column', 'Name')
        target_room_name_column = config.get('target_room_name_column', 'Raumtypenname')
        building_name = config.get('building_name', None)

        ifc_rooms, ifc_spaces_df = _extract_ifc_rooms(df, actual_room_name_column)
        excel_rooms = _extract_excel_rooms(target_df, target_room_name_column)

        detailed_df = _create_comparison_df(ifc_rooms, excel_rooms, ifc_spaces_df, actual_room_name_column)
        result_data = _create_summary_data(ifc_rooms, excel_rooms)

        result_bundle = ResultBundle(
            dataframe=detailed_df,
            json=result_data,
            folderpath=output_path.parent,
            summary=result_data,
        )

        if output_path:
            _export_to_excel(result_bundle, output_path, building_name)

        return result_bundle

    except Exception as e:
        logger.exception("Error comparing room names")
        return _create_error_result_bundle(str(e))

