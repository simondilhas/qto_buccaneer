from typing import Union, Dict, Any, Optional
import pandas as pd
from pathlib import Path
import logging
from qto_buccaneer._utils._result_bundle import BaseResultBundle, MetricsResultBundle
from qto_buccaneer._utils._general_tool_utils import unpack_dataframe, validate_df, validate_config
from qto_buccaneer._utils.calculate.exp_data.metadata_filter_exp import MetadataFilter
import json
import yaml
import time

logger = logging.getLogger(__name__)

def calculate_metrics_internal(
    input_data: Union[pd.DataFrame, BaseResultBundle, Dict[str, Any]],
    config: Dict[str, Any],
) -> MetricsResultBundle:
    """
    Calculate metrics from IFC model metadata based on provided configuration.

    This function processes IFC model metadata to calculate various building metrics
    such as floor areas, volumes, and other architectural quantities based on the
    provided configuration. It supports different input formats and returns a
    standardized MetricsResultBundle containing both the calculated metrics DataFrame
    and a JSON summary.

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
    #validate_config(config)

    TOOL_NAME = config.get('tool_name', 'metrics_calculator')
    logger.info(f"Starting {TOOL_NAME}")

    # 1. Unpack and validate input data
    if isinstance(input_data, BaseResultBundle):
        df = input_data.to_df()  # This will handle zip_content and other special cases
        input_json = input_data.json
    elif isinstance(input_data, pd.DataFrame):
        df = input_data
        input_json = None
    elif isinstance(input_data, dict):
        if "elements" in input_data:
            df = pd.DataFrame.from_dict(input_data["elements"], orient='index')
        else:
            df = pd.DataFrame([input_data])
        input_json = input_data
    else:
        raise ValueError("Input must be a DataFrame, BaseResultBundle, or dictionary")

    # 2. Extract and validate required columns
    #required_columns = ['IfcEntity', 'Name', 'Qto_SpaceBaseQuantities.NetFloorArea']
    #validation = validate_df(df, required_columns=required_columns, df_name="Input DataFrame")
    #if not validation['is_valid']:
    #    # If validation fails, try to extract from zip_content if available
    #    if isinstance(input_data, BaseResultBundle) and input_data.json and "zip_content" in input_data.json:
    #        # Extract the zip content to a temporary directory
    #        temp_dir = Path("/tmp/ifc_extract")
    #        temp_dir.mkdir(exist_ok=True)
    #        input_data.save_geometry(temp_dir)
    #        
    #        # Look for JSON files in the extracted content
    #        json_files = list(temp_dir.glob("*.json"))
    #        if json_files:
    #            # Read the first JSON file found
    #            with open(json_files[0], 'r') as f:
    #                json_data = json.load(f)
    #                if "elements" in json_data:
    #                    df = pd.DataFrame.from_dict(json_data["elements"], orient="index")
    #                    # Revalidate with the new DataFrame
    #                    validation = validate_df(df, required_columns=required_columns, df_name="Extracted DataFrame")
    #                    if not validation['is_valid']:
    #                        raise ValueError(f"Validation failed after extracting from zip: {validation['errors']}")
    #                else:
    #                    raise ValueError("No elements found in extracted JSON file")
    #        else:
    #            raise ValueError("No JSON files found in extracted zip content")
    #    else:
    #        raise ValueError(f"Validation failed: {validation['errors']}")
#
    # 3. Process the data
    try:
        # Get metrics configuration
        metrics_config = config.get('metrics', {})
        if not metrics_config:
            logger.warning(f"No metrics configuration found in config: {config}")
            # Create empty DataFrame with correct structure
            empty_df = pd.DataFrame(columns=[
                'metric_name', 'value', 'unit', 'success', 
                'calculation_time', 'building', 'description', 
                'formula', 'components'
            ])
            return MetricsResultBundle(
                dataframe=empty_df,
                json={
                    TOOL_NAME: {
                        "status": "Warning",
                        "message": "No metrics configuration found",
                        "input_type": "DataFrame" if isinstance(input_data, pd.DataFrame) else "BaseResultBundle" if isinstance(input_data, BaseResultBundle) else "JSON"
                    }
                }
            )

        building_name = config.get('building_name', 'Example Building')
        start_time = time.time()

        # Initialize an empty list to store all metric results
        all_results = []
        failed_metrics = []

        # Calculate each metric
        for metric_name, metric_config in metrics_config.items():
            try:
                logger.info(f"Calculating metric: {metric_name}")
                # Calculate each component
                component_values = {}
                if 'formula' in metric_config['config']:
                    for component_name, component_config in metric_config['config']['components'].items():
                        # Filter the DataFrame for this component
                        filtered_df = MetadataFilter.filter_df_from_str(df, component_config['filter'])
                        if filtered_df.empty:
                            logger.warning(f"No elements found for component {component_name} with filter {component_config['filter']}")
                        # Calculate the sum of the specified quantity
                        component_values[component_name] = filtered_df[component_config['base_quantity']].sum()
                    
                    # Evaluate the formula
                    formula = metric_config['config']['formula']
                    # Replace component names with their values
                    for component_name, value in component_values.items():
                        formula = formula.replace(component_name, str(value))
                    # Evaluate the formula safely
                    try:
                        value = eval(formula)
                    except Exception as e:
                        raise ValueError(f"Error evaluating formula '{formula}': {str(e)}")
                else:
                    # Simple calculation without formula
                    filtered_df = MetadataFilter.filter_df_from_str(df, metric_config['config']['filter'])
                    if filtered_df.empty:
                        logger.warning(f"No elements found for metric {metric_name} with filter {metric_config['config']['filter']}")
                    value = filtered_df[metric_config['config']['base_quantity']].sum()

                # Create result DataFrame for this metric
                metric_result = pd.DataFrame({
                    'metric_name': [metric_config['name']],
                    'value': [value],
                    'unit': [metric_config['config']['unit']],
                    'success': [True],
                    'calculation_time': [time.time() - start_time],
                    'building': [building_name],
                    'description': [metric_config['description']],
                    'formula': [metric_config['config'].get('formula', '')],
                    'components': [str(metric_config['config'].get('components', {}))]
                })
                all_results.append(metric_result)
                logger.info(f"Successfully calculated metric: {metric_name}")

            except Exception as e:
                logger.error(f"Failed to calculate metric {metric_name}: {str(e)}")
                failed_metrics.append({
                    'metric_name': metric_name,
                    'error': str(e)
                })

        if not all_results:
            logger.warning("No metrics were calculated successfully")
            # Create empty DataFrame with correct structure
            empty_df = pd.DataFrame(columns=[
                'metric_name', 'value', 'unit', 'success', 
                'calculation_time', 'building', 'description', 
                'formula', 'components'
            ])
            return MetricsResultBundle(
                dataframe=empty_df,
                json={
                    TOOL_NAME: {
                        "status": "Warning",
                        "message": "No metrics were calculated successfully",
                        "failed_metrics": failed_metrics,
                        "input_type": "DataFrame" if isinstance(input_data, pd.DataFrame) else "BaseResultBundle" if isinstance(input_data, BaseResultBundle) else "JSON"
                    }
                }
            )

        # Combine all results into a single DataFrame
        combined_results = pd.concat(all_results, ignore_index=True)

        # Create summary data
        summary_data = {
            TOOL_NAME: {
                "status": "Success",
                "input_type": "DataFrame" if isinstance(input_data, pd.DataFrame) else "BaseResultBundle" if isinstance(input_data, BaseResultBundle) else "JSON",
                "metrics_calculated": len(combined_results),
                "building": building_name,
                "failed_metrics": failed_metrics,
                "original_json": input_json
            }
        }

        # 4. Package results
        result_bundle = MetricsResultBundle(
            dataframe=combined_results,
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
    'tool_name': 'metrics_calculator',
    'building_name': 'Example Building',
    'metrics': {
        'gf_gesamt': {
            'name': 'GF Gesamt',
            'description': 'Die Gesamte Geschossfläche',
            'config': {
                'quantity_type': 'area',
                'unit': 'm2',
                'formula': 'GF - LUF',
                'components': {
                    'GF': {
                        'filter': 'IfcEntity=IfcSpace AND Name=GrossArea',
                        'base_quantity': 'Qto_SpaceBaseQuantities.NetFloorArea'
                    },
                    'LUF': {
                        'filter': 'IfcEntity=IfcSpace AND LongName=LUF',
                        'base_quantity': 'Qto_SpaceBaseQuantities.NetFloorArea'
                    }
                }
            }
        }
    }
}

# Using DataFrame input
df = pd.read_json("ifc_model_metadata.json")
result = calculate_metrics(df, config)

# Using BaseResultBundle input
result_bundle = BaseResultBundle(dataframe=df, json={'metadata': 'value'})
result = calculate_metrics(result_bundle, config)

# Using JSON input
with open("ifc_model_metadata.json", 'r') as f:
    json_data = json.load(f)
result = calculate_metrics(json_data, config)
""" 