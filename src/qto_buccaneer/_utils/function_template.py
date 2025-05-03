

from typing import Union, Dict, Any
import pandas as pd
from pathlib import Path
import logging
from qto_buccaneer._utils._result_bundle import ResultBundle
from qto_buccaneer._utils._general_tool_utils import unpack_dataframe, validate_df, validate_config


logger = logging.getLogger(__name__)

def tool_template(
    df_1: Union[pd.DataFrame, ResultBundle],
    df_2: Union[pd.DataFrame, ResultBundle], #different inputs like ifc, df, ...
    config: Dict[str, Any],
    output_path: Path
) -> ResultBundle:
    """
    Template for a data processing tool.

    Pattern:
    1. Unpack the DataFrame (handles both DataFrame and ResultBundle).
    2. Extract required configuration.
    3. Validate the DataFrame using `validate_df`.
    4. Process the DataFrame.
    5. Package and return results as a ResultBundle.

    Args:
        df: Input data as DataFrame or ResultBundle.
        config: Configuration dictionary.
        output_path: Path for output files.

    Returns:
        ResultBundle with processed data and summary.
    """

    validate_config(config)

    TOOL_NAME = config['tool_name']

    logger.info(f"Starting {TOOL_NAME}")

    # 1. Unpack DataFrame
    df = unpack_dataframe(df)

    # 2. Extract required columns
    required_columns = config['actual_columns']

    # 3. Validate DataFrame
    validation = validate_df(df, required_columns=required_columns, df_name="Actual DataFrame")
    if not validation['is_valid']:
        raise ValueError(f"Validation failed: {validation['errors']}")

    # TODO: validation for config after the config file structure is optimized

    # 4. Process DataFrame
    
    df, summary_data = _process_tool_logic(df, config)

    # 5. Package results
     # your summary logic here

    result_bundle = ResultBundle(
        dataframe=df,
        json=summary_data,
        folderpath=output_path.parent,
        summary=summary_data
    )

    # 6. Save results
    logger.info(f"Saving results to {output_path}")
    
    result_bundle.save_excel(output_path)
    result_bundle.save_summary(output_path.with_suffix(".yml"))


    # 7. Return results
    logger.info(f"Finished {TOOL_NAME}")
    return result_bundle



# Define elsewhere:
def _process_tool_logic(df, config):
    """Core data processing logic for the tool"""
    try:
        # Tool-specific processing logic here
        tool_name = config['tool_name']

        summary_data = {
        tool_name: {
            "status": "Success",
            "summary": "Useful tool summary data"
        }
    } 
        return df, summary_data
    except Exception as e:
        logger.exception(f"{config['tool_name']}: Processing failed")
        raise RuntimeError(f"Processing failed in {config['tool_name']}: {str(e)}")