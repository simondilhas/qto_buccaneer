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
    Calculate all metrics (base and derived) defined in the configuration.
    """
    results = []
    
    # Calculate base metrics
    for metric_name in config.get('metrics', {}).keys():
        metric_df = calculate_single_metric(
            ifc_path=ifc_path,
            config=config,
            metric_name=metric_name,
            file_info=file_info
        )
        results.append(metric_df)

    # Combine base metrics
    metrics_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    
    # Calculate derived metrics in order, updating the DataFrame after each calculation
    for metric_name, metric_config in config.get('derived_metrics', {}).items():
        metric_df = calculate_single_derived_metric(
            metric_name=metric_name,
            unit="ratio" if "/" in metric_config['formula'] else metrics_df.iloc[0]['unit'],
            formula=metric_config['formula'],
            df_metrics=metrics_df,  # Use the updated metrics DataFrame
            file_info=file_info
        )
        # Update the metrics DataFrame with the new derived metric
        metrics_df = pd.concat([metrics_df, metric_df], ignore_index=True)
    
    return metrics_df if not metrics_df.empty else pd.DataFrame(
        columns=["metric_name", "value", "unit", "category", "description", 
                "calculation_time", "status"] + (list(file_info.keys()) if file_info else [])
    )

def calculate_single_derived_metric(
    metric_name: str, 
    unit: str, 
    formula: str, 
    df_metrics: pd.DataFrame, 
    file_info: Optional[dict] = None
) -> pd.DataFrame:
    """
    Calculate a single derived metric based on existing metrics.

    Args:
        metric_name (str): Name of the derived metric to calculate
        unit (str): Unit of measurement for the result
        formula (str): Formula to calculate the derived metric
        df_metrics (pd.DataFrame): DataFrame containing the metrics to use in the calculation
        file_info (Optional[dict]): Additional file information to include in results

    Returns:
        pd.DataFrame: DataFrame containing the calculated derived metric
    """
    try:
        # Create a dict of variables for formula evaluation
        metric_values = df_metrics.set_index('metric_name')['value'].to_dict()
        
        # Evaluate the formula using the metric values
        value = eval(formula, {"__builtins__": {}}, metric_values)
        
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            value=value,
            unit=unit,
            category="derived",
            description=formula,  # Use formula as description for transparency
            **file_info or {}
        )])
        
    except NameError as e:
        # Handle case where a required metric is missing
        missing_metric = str(e).split("'")[1]
        error_msg = f"Required metric '{missing_metric}' not found in calculated metrics"
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message=error_msg,
            **file_info or {}
        )])
    except Exception as e:
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message=str(e),
            **file_info or {}
        )])

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



