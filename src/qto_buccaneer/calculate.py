from typing import Union, Dict, Any, List
import pandas as pd
from qto_buccaneer._utils._result_bundle import BaseResultBundle, MetricsResultBundle
from qto_buccaneer._utils.calculate.calculate_metrics import calculate_metrics_internal
import logging

logger = logging.getLogger(__name__)

def calculate_metrics(
    input_data: Union[pd.DataFrame, BaseResultBundle, Dict[str, Any]],
    config: Dict[str, Any],
) -> MetricsResultBundle:
    """
    Calculate metrics from IFC model metadata based on provided configuration.

    This function processes IFC model metadata to calculate various building metrics
    such as floor areas, volumes, and other architectural quantities based on the
    provided configuration. It supports different input formats and returns a
    standardized MetricsResultBundle containing the calculated metrics.

    Args:
        input_data: Input data in one of the following formats:
                   - pandas DataFrame containing IFC model metadata
                   - BaseResultBundle containing IFC model metadata
                   - JSON-compatible dictionary with IFC model metadata
        config: Configuration dictionary containing:
               - metrics: Dictionary of metric configurations
               - building_name: Name of the building (optional)

    Returns:
        MetricsResultBundle containing:
        - dataframe: DataFrame with calculated metrics
        - json: Summary data in JSON format
    """
    logger.info("Starting metrics calculation")
    
    # Calculate metrics using internal function
    result = calculate_metrics_internal(input_data, config)
    
    # Validate the result
    if result.dataframe is None or result.dataframe.empty:
        logger.warning("No metrics were calculated - empty DataFrame returned")
        # Create an empty DataFrame with the expected columns
        result.dataframe = pd.DataFrame(columns=[
            'metric_name', 'value', 'unit', 'success', 
            'calculation_time', 'building', 'description', 
            'formula', 'components'
        ])
    
    if result.json is None:
        logger.warning("No summary data was generated - empty JSON returned")
        result.json = {
            config.get('tool_name', 'metrics_calculator'): {
                "status": "Warning",
                "message": "No metrics were calculated",
                "input_type": "DataFrame" if isinstance(input_data, pd.DataFrame) else "BaseResultBundle" if isinstance(input_data, BaseResultBundle) else "JSON"
            }
        }
    
    logger.info(f"Finished metrics calculation. Calculated {len(result.dataframe)} metrics")
    return result


def calculate_all_metrics(
    input_data: Union[pd.DataFrame, BaseResultBundle, Dict[str, Any]],
    config: Dict[str, Any],
) -> MetricsResultBundle:
    """
    Calculate all metrics from IFC model metadata based on provided configuration.

    This function processes IFC model metadata to calculate various building metrics
    such as floor areas, volumes, and other architectural quantities based on the
    provided configuration. It supports different input formats and returns a
    standardized MetricsResultBundle containing all calculated metrics.

    Args:
        input_data: Input data in one of the following formats:
                   - pandas DataFrame containing IFC model metadata
                   - BaseResultBundle containing IFC model metadata
                   - JSON-compatible dictionary with IFC model metadata
        config: Configuration dictionary containing:
               - metrics: Dictionary of metric configurations
               - building_name: Name of the building (optional)

    Returns:
        MetricsResultBundle containing:
        - dataframe: DataFrame with all calculated metrics
        - json: Summary data in JSON format
    """
    logger.info("Starting calculation of all metrics")
    
    # Initialize lists to store results
    all_metrics_dfs: List[pd.DataFrame] = []
    all_summaries: List[Dict[str, Any]] = []
    
    # Calculate metrics for each configuration
    for metric_name, metric_config in config.get('metrics', {}).items():
        logger.info(f"Calculating metric: {metric_name}")
        
        # Create a single metric config
        single_metric_config = {
            'tool_name': config.get('tool_name', 'metrics_calculator'),
            'building_name': config.get('building_name', 'Example Building'),
            'metrics': {metric_name: metric_config}
        }
        
        # Calculate metrics for this configuration
        result = calculate_metrics_internal(input_data, single_metric_config)
        
        # Store the results
        if result.dataframe is not None and not result.dataframe.empty:
            all_metrics_dfs.append(result.dataframe)
        if result.json is not None:
            all_summaries.append(result.json)
    
    # Merge all DataFrames
    if all_metrics_dfs:
        combined_df = pd.concat(all_metrics_dfs, ignore_index=True)
    else:
        logger.warning("No metrics were calculated - empty DataFrame returned")
        combined_df = pd.DataFrame(columns=[
            'metric_name', 'value', 'unit', 'success', 
            'calculation_time', 'building', 'description', 
            'formula', 'components'
        ])
    
    # Merge all summaries
    combined_summary = {}
    for summary in all_summaries:
        combined_summary.update(summary)
    
    if not combined_summary:
        logger.warning("No summary data was generated - empty JSON returned")
        combined_summary = {
            config.get('tool_name', 'metrics_calculator'): {
                "status": "Warning",
                "message": "No metrics were calculated",
                "input_type": "DataFrame" if isinstance(input_data, pd.DataFrame) else "BaseResultBundle" if isinstance(input_data, BaseResultBundle) else "JSON"
            }
        }
    
    logger.info(f"Finished calculation of all metrics. Calculated {len(combined_df)} metrics")
    
    # Create final MetricsResultBundle
    return MetricsResultBundle(
        dataframe=combined_df,
        json=combined_summary
    )