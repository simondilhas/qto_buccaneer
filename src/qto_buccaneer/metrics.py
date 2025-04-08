import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)


from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator
from qto_buccaneer.utils.config_loader import create_result_dict

def calculate_single_metric(ifc_path: str, config: dict, metric_name: str, file_info: Optional[dict] = None) -> pd.DataFrame:
    """
    Calculate a single metric from an IFC file based on the provided configuration.

    Args:
        ifc_path (str): Path to the IFC file to analyze
        config (dict): Configuration dictionary containing metric definitions.
            Expected format:
            {
                "metrics": {
                    "metric_name": {
                        "description": str,
                        "quantity_type": str,
                        "ifc_entity": str,
                        ...
                    }
                }
            }
        metric_name (str): Name of the metric to calculate (must exist in config)
        file_info (Optional[dict], optional): Additional file information to include in results. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing the calculated metric with columns:
            - metric_name: Name of the metric
            - value: Calculated value
            - unit: Unit of measurement
            - description: Metric description
            - error: Error message if calculation failed

    Raises:
        None: Errors are caught and returned in the DataFrame with error information

    Example:
        >>> config = {
        ...     "metrics": {
        ...         "gross_floor_area": {
        ...             "description": "Total floor area",
        ...             "quantity_type": "area",
        ...             "ifc_entity": "IfcSpace"
        ...         }
        ...     }
        ... }
        >>> df = calculate_single_metric("model.ifc", config, "gross_floor_area")
    """
    
    if metric_name not in config.get('metrics', {}):
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message="Metric not found in standard metrics configuration",
            **file_info or {}
        )])
    
    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    metric_config = config['metrics'][metric_name]
    
    try:
        result = _process_quantity_calculation(qto, metric_name, metric_config, file_info)
        return pd.DataFrame([result])
    except Exception as e:
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message=str(e),
            **file_info or {}
        )])

def calculate_all_metrics(config: Dict, ifc_path: str, file_info: Optional[dict] = None) -> pd.DataFrame:
    """
    Calculate all metrics defined in the configuration for a given IFC file.

    Args:
        config (Dict): Dictionary containing metrics configuration.
            Expected format:
            {
                "metrics": {
                    "metric_name": {
                        "description": str,
                        "quantity_type": str,
                        "ifc_entity": str,
                        ...
                    },
                    ...
                }
            }
        ifc_path (str): Path to the IFC file to analyze
        file_info (Optional[dict], optional): Additional file information to include in results. Defaults to None.

    Returns:
        pd.DataFrame: Combined DataFrame containing all metric results with columns:
            - metric_name: Name of the metric
            - value: Calculated value
            - unit: Unit of measurement
            - category: Metric category
            - description: Metric description
            - calculation_time: Time taken to calculate the metric
            - status: Success or error status
            - [file_info keys]: Additional columns from file_info if provided

    Notes:
        - If no metrics are defined in the config, returns an empty DataFrame with predefined columns
        - Each metric is calculated independently; errors in one calculation won't affect others

    Example:
        >>> config = {
        ...     "metrics": {
        ...         "gross_floor_area": {
        ...             "description": "Total floor area",
        ...             "quantity_type": "area",
        ...             "ifc_entity": "IfcSpace"
        ...         },
        ...         "wall_volume": {
        ...             "description": "Total wall volume",
        ...             "quantity_type": "volume",
        ...             "ifc_entity": "IfcWall"
        ...         }
        ...     }
        ... }
        >>> df = calculate_all_metrics(config, "model.ifc")
    """
    results = []
    for metric_name in config.get('metrics', {}).keys():
        metric_df = calculate_single_metric(
            ifc_path=ifc_path,
            config=config,
            metric_name=metric_name,
            file_info=file_info
        )
        results.append(metric_df)

    # Combine all results into a single DataFrame
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        # Create base columns list
        columns = [
            "metric_name", "value", "unit", "category", 
            "description", "calculation_time", "status"
        ]
        # Add file_info keys if present
        if file_info:
            columns.extend(file_info.keys())
        return pd.DataFrame(columns=columns)

def calculate_single_derived_metric(metric_name: str, unit: str, formula: str, df_metrics: pd.DataFrame, file_info: Optional[dict] = None) -> pd.DataFrame:
    """
    Calculate a single derived metric based on existing metrics.

    Args:
        metric_name (str): Name of the derived metric to calculate
        formula (str): Formula to calculate the derived metric
        df_metrics (pd.DataFrame): DataFrame containing the metrics to use in the calculation
        file_info (Optional[dict], optional): Additional file information to include in results. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing the calculated derived metric with columns:
            - metric_name: Name of the derived metric

    """

    try:
        # Evaluate the formula using the metrics DataFrame
        result = eval(formula, {'pd': pd}, {'df_metrics': df_metrics})
        
        # Create a DataFrame with the result
        result_df = pd.DataFrame([{
            "metric_name": metric_name,
            "value": result,
            "unit": unit,
            "category": "derived",
            "description": "",
            "calculation_time": datetime.now(),
            "status": "success",
        }])
        
        # Add file_info if provided
        if file_info:
            result_df.loc[:, file_info.keys()] = result_df.loc[:, file_info.keys()].apply(lambda x: x if x is not None else "")
        
        return result_df
    except Exception as e:
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message=str(e),
            **file_info or {}
        )])

def calculate_derived_metrics(config: dict, df_metrics: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate derived metrics based on existing metrics.

    Args:
        config (dict): Dictionary containing metrics configuration with derived_metrics section
        df_metrics (pd.DataFrame): DataFrame containing the calculated base metrics

    Returns:
        pd.DataFrame: DataFrame containing the calculated derived metrics
    """
    if 'derived_metrics' not in config:
        return pd.DataFrame()  # Return empty DataFrame if no derived metrics defined

    results = []
    
    for metric_name, metric_config in config['derived_metrics'].items():
        try:
            # Create a dict of variables for formula evaluation
            metric_values = df_metrics.set_index('metric_name')['value'].to_dict()
            
            # Evaluate the formula using the metric values
            try:
                value = eval(metric_config['formula'], {"__builtins__": {}}, metric_values)
            except NameError as e:
                # Handle case where a required metric is missing
                missing_metric = str(e).split("'")[1]
                raise ValueError(f"Required metric '{missing_metric}' not found in calculated metrics")
            
            results.append({
                "metric_name": metric_name,
                "value": value,
                "unit": "ratio" if "/" in metric_config['formula'] else df_metrics.iloc[0]['unit'],
                "category": "derived",
                "description": metric_config['description'],
                "calculation_time": datetime.now(),
                "status": "success"
            })
            
        except Exception as e:
            # Handle calculation errors
            results.append({
                "metric_name": metric_name,
                "value": None,
                "unit": "unknown",
                "category": "derived",
                "description": metric_config['description'],
                "calculation_time": datetime.now(),
                "status": f"error: {str(e)}"
            })

    return pd.DataFrame(results)

def _process_quantity_calculation(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: Optional[dict] = None) -> dict:
    """Process a single quantity calculation and format its result.
    
    Args:
        qto: QtoCalculator instance
        metric_name: Name of the metric to calculate
        metric_config: Configuration for the metric
        file_info: Optional dictionary with file information
    """
    try:
        value = qto.calculate_quantity(
            quantity_type=metric_config["quantity_type"],
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            subtract_filter=metric_config.get("subtract_filter"),
            subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
            ifc_entity=metric_config["ifc_entity"],
            pset_name=metric_config["pset_name"],
            prop_name=metric_config["prop_name"]
        )
        
        result = {
            "metric_name": metric_name,
            "value": round(value, 2) if value is not None else None,
            "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": metric_config["quantity_type"],
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": "success",
        }
        
        # Add file_info if provided
        if file_info:
            result.update(file_info)
            
        return result
        
    except Exception as e:
        result = {
            "metric_name": metric_name,
            "value": None,
            "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": "unknown",
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": f"error: {str(e)}",
        }
        
        # Add file_info if provided
        if file_info:
            result.update(file_info)
            
        return result

def _create_error_df(metric_name: str, error_message: str, file_info: Optional[dict] = None) -> pd.DataFrame:
    """Create a DataFrame for error cases.
    
    Args:
        metric_name: Name of the metric that caused the error
        error_message: Description of the error
        file_info: Optional dictionary with file information
    """
    result = {
        "metric_name": metric_name,
        "value": None,
        "unit": "unknown",  # Removed dependency on metric_config
        "category": "unknown",
        "description": "",
        "calculation_time": datetime.now(),
        "status": f"error: {error_message}",
    }
    
    # Add file_info if provided
    if file_info:
        result.update(file_info)
        
    return pd.DataFrame([result])



