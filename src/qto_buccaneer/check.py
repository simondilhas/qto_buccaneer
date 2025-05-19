# TODO: add checks from reports here
import pandas as pd
import os
from qto_buccaneer.utils.building_summary import BuildingSummary
from qto_buccaneer.utils import load_config
from qto_buccaneer.utils.metadata_filter import MetadataFilter
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from qto_buccaneer.report import ExcelLayoutConfig
from qto_buccaneer._utils.checks.compare_target_actual import process_compare_target_actual_logic
import json
from qto_buccaneer._utils._result_bundle import BaseResultBundle
import logging
from qto_buccaneer._utils._general_tool_utils import unpack_dataframe, validate_df, validate_config

from qto_buccaneer._utils.checks.check_dimensions import process_check_dimensions
from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader
from qto_buccaneer._utils.checks.check_building_inside_envelop import process_check_building_inside_envelop
from dotenv import load_dotenv
logger = logging.getLogger(__name__)

load_dotenv()

def compare_target_actual(
    target_df: Union[pd.DataFrame, BaseResultBundle],
    actual_df: Union[pd.DataFrame, BaseResultBundle],
    config: Dict[str, Any]
) -> BaseResultBundle:
    """
    Compare target and actual building data.
    
    Args:
        target_df: Target data as DataFrame or BaseResultBundle
        actual_df: Actual data as DataFrame or BaseResultBundle
        config: Configuration dictionary containing tool_name, tool_description, and tool_config
        
    Returns:
        BaseResultBundle containing comparison results
        
    Example:
        config = {
            'tool_name': 'room_name_and_area_comparison',
            'tool_description': 'Compare the target room program against the actual room program',
            'tool_config': {
                'tolerance': 5,  # in percent
                'filter': 'IfcEntity=IfcSpace AND (PredefinedType=EXTERNAL OR PredefinedType=INTERNAL)',
                'key_target_column': 'LongName',
                'key_actual_column': 'LongName',
                'area_target_column': 'Soll m2',
                'area_actual_column': 'Qto_SpaceBaseQuantities.NetFloorArea',
                'return_values_target': [
                    'LongName',
                    'Raumbezeichnung',
                    'Soll m2',
                    'Aussenraum',
                    'Bereich'
                ],
                'return_values_actual': [
                    'LongName',
                    'Qto_SpaceBaseQuantities.NetFloorArea',
                    'Pset_SpatialData.BuildingStory',
                    'Pset_SpatialData.ElevationOfStory',
                    'Pset_Enrichment.SiA-2016',
                    'Pset_Enrichment.Bereich',
                    'PredefinedType',
                    'GlobalId',
                    'id'
                ]
            }
        }
        
        result = compare_target_actual(
            target_df=target_data,
            actual_df=actual_data,
            config=config
        )
    """
    #validate_config(config)
    # TODO: add a concept for config checker

    logger.info(f"Starting Compare Target Actual")

    # 1. Unpack DataFrames
    target_df = unpack_dataframe(target_df)
    actual_df = unpack_dataframe(actual_df)

    # 2. Extract required columns from tool_config
    required_columns_target = config.get('return_values_target', [])
    required_columns_actual = config.get('return_values_actual', [])

    # 3. Validate DataFrames
    validation_target = validate_df(target_df, required_columns=required_columns_target, df_name="Target DataFrame")
    if not validation_target['is_valid']:
        raise ValueError(f"Target DataFrame validation failed: {validation_target['errors']}")

    validation_actual = validate_df(actual_df, required_columns=required_columns_actual, df_name="Actual DataFrame")
    if not validation_actual['is_valid']:
        raise ValueError(f"Actual DataFrame validation failed: {validation_actual['errors']}")

    # 4. Process DataFrames
    df, summary_data = process_compare_target_actual_logic(target_df, actual_df, config)

    

    # 5. Package results
    result_bundle = BaseResultBundle(
        dataframe=df,
        json=summary_data,
        summary=summary_data
    )

    # 6. Return results
    logger.info(f"Finished Compare Target Actual")
    return result_bundle



def check_dimensions(
    data_dir: Path,
    check_config: dict,
) -> Dict[str, Any]:
    """
    Check room dimensions against specified criteria.
    
    Args:
        data_dir: Path to the directory containing metadata.json and geometry files
        check_config: Configuration dictionary for dimension checks
        
    Returns:
        Dictionary containing check results
    """
    logger.info("Starting check_dimensions")
    
    ifc = IfcJsonLoader(
    json_paths=str(data_dir),
    properties_json=str(data_dir / "ifc_model_metadata.json")
    )

    check_filter = check_config["config"]["filter"]
    filtered_elements = ifc.get_elements_by_filter(check_filter)
    
    # Process the dimension checks
    result = process_check_dimensions(
        input_dict=filtered_elements,
        config=check_config
    )
    
    
    return result


def check_building_inside_envelop(
    ifc_dir: Path,
    reference_file: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Check if the building is inside the envelop.
    """
    logger.info("Starting check_building_inside_envelop")

    load_dotenv()

    API_URL = os.getenv("BUILDING_ENVELOP_CHECK_API_URL")

    df_result = process_check_building_inside_envelop(
    ifc_dir=ifc_dir,
    reference_file=reference_file,
    output_dir=output_dir
    )

    return df_result