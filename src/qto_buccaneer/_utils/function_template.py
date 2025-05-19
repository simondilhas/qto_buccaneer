from typing import Union, Dict, Any, Optional
import pandas as pd
from pathlib import Path
import logging
from qto_buccaneer._utils._result_bundle import BaseResultBundle
from qto_buccaneer._utils._general_tool_utils import unpack_dataframe, validate_df, validate_config
import json
import yaml
import zipfile
import io

logger = logging.getLogger(__name__)

def process_metadata(
    input_data: Union[pd.DataFrame, BaseResultBundle, Dict[str, Any]],
    config: Dict[str, Any],
) -> BaseResultBundle:
    """
    Process metadata from various input formats and return a standardized BaseResultBundle.

    This function handles different input formats (DataFrame, BaseResultBundle, or JSON dictionary)
    and processes them according to the provided configuration. It validates the input,
    processes the data, and returns a BaseResultBundle containing both the processed DataFrame
    and JSON summary.

    Args:
        input_data: Input data in one of the following formats:
                   - pandas DataFrame
                   - BaseResultBundle
                   - JSON-compatible dictionary
        config: Configuration dictionary containing processing parameters

    Returns:
        BaseResultBundle containing:
        - dataframe: Processed DataFrame
        - json: Summary data in JSON format
    """
    validate_config(config)

    TOOL_NAME = config.get('tool_name', 'metadata_processor')
    logger.info(f"Starting {TOOL_NAME}")

    # 1. Unpack and validate input data
    if isinstance(input_data, BaseResultBundle):
        df = input_data.to_df()
        input_json = input_data.json
    elif isinstance(input_data, pd.DataFrame):
        df = input_data
        input_json = None
    elif isinstance(input_data, dict):
        df = pd.DataFrame([input_data])
        input_json = input_data
    else:
        raise ValueError("Input must be a DataFrame, BaseResultBundle, or dictionary")

    # 2. Extract and validate required columns
    required_columns = config.get('required_columns', [])
    if required_columns:
        validation = validate_df(df, required_columns=required_columns, df_name="Input DataFrame")
        if not validation['is_valid']:
            raise ValueError(f"Validation failed: {validation['errors']}")

    # 3. Process the data
    try:
        # Process DataFrame
        processed_df = df.copy()
        
        # Create summary data
        summary_data = {
            TOOL_NAME: {
                "status": "Success",
                "input_type": "DataFrame" if isinstance(input_data, pd.DataFrame) else "BaseResultBundle" if isinstance(input_data, BaseResultBundle) else "JSON",
                "row_count": len(processed_df),
                "column_count": len(processed_df.columns),
                "columns": list(processed_df.columns),
                "original_json": input_json
            }
        }

        # 4. Package results
        result_bundle = BaseResultBundle(
            dataframe=processed_df,
            json=summary_data
        )

        logger.info(f"Finished {TOOL_NAME}")
        return result_bundle

    except Exception as e:
        logger.exception(f"{TOOL_NAME}: Processing failed")
        raise RuntimeError(f"Processing failed in {TOOL_NAME}: {str(e)}")

# Example usage:
"""
config = {
    'tool_name': 'metadata_processor',
    'required_columns': ['column1', 'column2']
}

# Using DataFrame input
df = pd.DataFrame({'column1': [1, 2], 'column2': ['a', 'b']})
result = process_metadata(df, config)

# Using BaseResultBundle input
result_bundle = BaseResultBundle(dataframe=df, json={'metadata': 'value'})
result = process_metadata(result_bundle, config)

# Using JSON input
json_data = {'column1': 1, 'column2': 'a'}
result = process_metadata(json_data, config)
"""