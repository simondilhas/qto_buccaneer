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
    Calculate all metrics (base, relationship-based, derived, space-based, and grouped) defined in the configuration.
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

    # Calculate space-based metrics
    for metric_name in config.get('room_based_metrics', {}).keys():
        metric_df = calculate_single_metric_by_space(
            ifc_path=ifc_path,
            config=config,
            metric_name=metric_name,
            file_info=file_info
        )
        results.append(metric_df)

    # Calculate grouped metrics
    for metric_name in config.get('grouped_by_attribute_metrics', {}).keys():
        metric_df = calculate_single_grouped_metric(
            ifc_path=ifc_path,
            config=config,
            metric_name=metric_name,
            file_info=file_info
        )
        results.append(metric_df)

    # Combine all metrics
    metrics_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame(
        columns=["metric_name", "value", "unit", "category", "description", 
                "calculation_time", "status"] + (list(file_info.keys()) if file_info else [])
    )
    
    # Calculate derived metrics in order, updating the DataFrame after each calculation
    for metric_name, metric_config in config.get('derived_metrics', {}).items():
        metric_df = calculate_single_derived_metric(
            metric_name=metric_name,
            unit=metric_config.get('unit', 'unknown'),
            formula=metric_config['formula'],
            df_metrics=metrics_df,
            file_info=file_info
        )
        # Update the metrics DataFrame with the new derived metric
        metrics_df = pd.concat([metrics_df, metric_df], ignore_index=True)
    
    return metrics_df

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
        unit (str): Unit of measurement for the result (from config)
        formula (str): Formula to calculate the derived metric
        df_metrics (pd.DataFrame): DataFrame containing the metrics to use in the calculation
        file_info (Optional[dict]): Additional file information to include in results

    Returns:
        pd.DataFrame: DataFrame containing the calculated derived metric
    """
    try:
        # Create a dict of variables for formula evaluation
        metric_values = df_metrics.set_index('metric_name')['value'].to_dict()
        
        # Get units of input metrics
        input_metrics = [m for m in metric_values.keys() if m in formula]
        input_units = df_metrics[df_metrics['metric_name'].isin(input_metrics)]['unit'].unique()
        
        # Evaluate the formula using the metric values
        value = eval(formula, {"__builtins__": {}}, metric_values)
        
        # Determine unit and category based on formula and input units
        if "/" in formula:
            unit = "ratio"
            category = "ratio"
        elif all(u == "m²" for u in input_units):
            unit = "m²"
            category = "area"
        elif all(u == "m³" for u in input_units):
            unit = "m³"
            category = "volume"
        elif all(u == "count" for u in input_units):
            unit = "count"
            category = "count"
            value = int(value) if value is not None else None
        else:
            # Use the unit from config as fallback
            category = "derived"
        
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            value=round(value, 2) if value is not None and unit != "count" else value,
            unit=unit,
            category=category,
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

def calculate_single_metric_by_space(ifc_path: str, config: dict, metric_name: str, file_info: dict) -> pd.DataFrame:
    """Calculate a single room-based metric."""
    
    if metric_name not in config.get('room_based_metrics', {}):
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message="Metric not found in room-based metrics configuration",
            **file_info
        )])

    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    metric_config = config['room_based_metrics'][metric_name]
    grouping_attribute = metric_config.get("grouping_attribute", "LongName")
    metric_by_group = f"{metric_name}_by_{grouping_attribute.lower()}"

    try:
        room_values = qto._get_elements_by_space(
            ifc_entity=metric_config["ifc_entity"],
            grouping_attribute=grouping_attribute,
            room_reference_attribute_guid=metric_config.get("room_reference_attribute_guid", "ePset_abstractBIM.Spaces"),
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            subtract_filter=metric_config.get("subtract_filter"),
            subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
            pset_name=metric_config.get("pset_name", "Qto_BaseQuantities"),
            prop_name=metric_config.get("prop_name", "NetArea")
        )

        # Create results for each room/space
        results = []
        for room_name, value in room_values.items():
            results.append(create_result_dict(
                metric_name=f"{metric_by_group}_{room_name}",
                value=value,
                unit="m³" if metric_config.get("quantity_type") == "volume" else "m²",
                category=metric_config.get("quantity_type", "area"),
                description=metric_config.get("description", ""),
                **file_info
            ))

        if results:
            return pd.DataFrame(results)
        else:
            return pd.DataFrame([create_result_dict(
                metric_name=metric_by_group,
                error_message="No results calculated",
                **file_info
            )])

    except Exception as e:
        return pd.DataFrame([create_result_dict(
            metric_name=metric_by_group,
            error_message=str(e),
            **file_info
        )])

def _process_quantity_calculation(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: Optional[dict] = None) -> dict:
    """Process a single quantity calculation and format its result."""
    try:
        value = qto.calculate_quantity(
            quantity_type=metric_config["quantity_type"],
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            subtract_filter=metric_config.get("subtract_filter"),
            subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
            ifc_entity=metric_config["ifc_entity"],
            pset_name=metric_config.get("pset_name"),  # Make pset_name optional for count
            prop_name=metric_config.get("prop_name")   # Make prop_name optional for count
        )
        
        # Determine unit based on quantity_type
        if metric_config["quantity_type"] == "volume":
            unit = "m³"
        elif metric_config["quantity_type"] == "area":
            unit = "m²"
        elif metric_config["quantity_type"] == "count":
            unit = "count"
            value = int(value) if value is not None else None  # Convert count to integer
        else:
            unit = "unknown"
        
        result = {
            "metric_name": metric_name,
            "value": value,  # Don't round counts
            "unit": unit,
            "category": metric_config["quantity_type"],
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": "success",
        }
        
        # Round non-count values
        if value is not None and metric_config["quantity_type"] not in ["count"]:
            result["value"] = round(value, 2)
        
        # Add file_info if provided
        if file_info:
            result.update(file_info)
            
        return result
        
    except Exception as e:
        result = {
            "metric_name": metric_name,
            "value": None,
            "unit": "count" if metric_config["quantity_type"] == "count" else 
                   "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": "unknown",
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": f"error: {str(e)}",
        }
        
        if file_info:
            result.update(file_info)
            
        return result

def _process_space_relationship_calculation(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: Optional[dict] = None) -> dict:
    """Process a single relationship-based calculation and format its result."""
    try:
        grouping_attribute = metric_config.get("grouping_attribute")
        
        # Determine if this is a Pset attribute or direct attribute
        if '.' in grouping_attribute:
            # For Pset attributes (e.g., "Pset_abstractBIM.Normal")
            pset_name, attr_name = grouping_attribute.split('.')
            grouping_name = attr_name.lower()
        else:
            # For direct attributes (e.g., "LongName")
            grouping_name = grouping_attribute.lower()
            
        metric_by_group = f"{metric_name}_by_{grouping_name}"
        
        room_values = qto._get_elements_by_space(
            ifc_entity=metric_config["ifc_entity"],
            grouping_attribute=grouping_attribute,
            room_reference_attribute_guid=metric_config.get("room_reference_attribute_guid", "ePset_abstractBIM.Spaces"),
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            subtract_filter=metric_config.get("subtract_filter"),
            subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
            pset_name=metric_config.get("pset_name", "Qto_BaseQuantities"),
            prop_name=metric_config.get("prop_name", "NetArea")
        )
        
        # Create results for each group
        results = []
        for group_value, value in room_values.items():
            # Simply convert the value to string, replacing spaces with underscores
            clean_group_value = str(group_value).replace(" ", "_").lower()
            
            results.append(create_result_dict(
                metric_name=f"{metric_by_group}_{clean_group_value}",
                value=value,
                unit="m³" if metric_config.get("quantity_type") == "volume" else "m²",
                category=metric_config.get("quantity_type", "area"),
                description=metric_config.get("description", ""),
                **file_info or {}
            ))
        if results:
            return results[0]  # Return the first result as a single-row DataFrame
        else:
            return create_result_dict(
                metric_name=metric_by_group,
                error_message="No results calculated",
                **file_info or {}
            )
    except Exception as e:
        return create_result_dict(
            metric_name=metric_name,
            error_message=str(e),
            **file_info or {}
        )

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

def calculate_single_room_metric(ifc_path: str, config: dict, metric_name: str, file_info: dict) -> pd.DataFrame:
 
    """Calculate a single room-based metric."""
 

    
 
    if metric_name not in config.get('room_based_metrics', {}):
 
        return _create_error_df(metric_name, "Metric not found in room-based metrics configuration", file_info)
 

 
    loader = IfcLoader(ifc_path)
 
    qto = QtoCalculator(loader)
 
    metric_config = config['room_based_metrics'][metric_name]
 
    grouping_attribute = metric_config.get("grouping_attribute", "LongName")
 
    metric_by_group = f"{metric_name}_by_{grouping_attribute.lower()}"
 

 
    try:
 
        room_values = qto._get_elements_by_space(
 
            ifc_entity=metric_config["ifc_entity"],
 
            grouping_attribute=grouping_attribute,
 
            room_reference_attribute_guid=metric_config.get("room_reference_attribute_guid", "ePset_abstractBIM.Spaces"),
 
            include_filter=metric_config.get("include_filter"),
 
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
 
            subtract_filter=metric_config.get("subtract_filter"),
 
            subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
 
            pset_name=metric_config.get("pset_name", "Qto_BaseQuantities"),
 
            prop_name=metric_config.get("prop_name", "NetArea")
 
        )
 

 
        # Create results for each room/space
 
        results = []
 
        for room_name, value in room_values.items():
 
            results.append({
 
                "metric_name": f"{metric_by_group}_{room_name}",
 
                "value": round(value, 2) if value is not None else None,
 
                "unit": "m³" if metric_config.get("quantity_type") == "volume" else "m²",
 
                "category": metric_config.get("quantity_type", "area"),
 
                "description": metric_config.get("description", ""),
 
                "calculation_time": datetime.now(),
 
                "status": "success",
 
                **file_info
 
            })
 

 
        if results:
 
            return pd.DataFrame(results)
 
        else:
 
            return _create_error_df(metric_by_group, "No results calculated", file_info)
 

 
    except Exception as e:
 
        return _create_error_df(metric_by_group, str(e), file_info)

def _create_error_df(metric_name: str, error_message: str, file_info: dict) -> pd.DataFrame:
    """Create a DataFrame for error cases."""
    return pd.DataFrame([create_result_dict(
        metric_name=metric_name,
        error_message=error_message,
        **file_info
    )])

def calculate_single_grouped_metric(ifc_path: str, config: dict, metric_name: str, file_info: Optional[dict] = None) -> pd.DataFrame:
    """Calculate a single metric grouped by an attribute. This helps to dynamically calculate metrics based on the attribute values in the IFC.
    
    Args:
        ifc_path: Path to the IFC file
        config: Configuration dictionary
        metric_name: Name of the metric to calculate
        file_info: Optional additional file information
    
    Returns:
        DataFrame containing the calculated metrics, one row per group
    """
    if metric_name not in config.get('grouped_by_attribute_metrics', {}):
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message="Metric not found in grouped metrics configuration",
            **file_info or {}
        )])

    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    metric_config = config['grouped_by_attribute_metrics'][metric_name]
    
    try:
        # Get grouped values using the new method
        grouped_values = qto._get_elements_by_attribute(
            ifc_entity=metric_config["ifc_entity"],
            grouping_attribute=metric_config["grouping_attribute"],
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            subtract_filter=metric_config.get("subtract_filter"),
            subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
            pset_name=metric_config.get("pset_name"),
            prop_name=metric_config.get("prop_name")
        )

        # Create results for each group
        results = []
        for group_value, value in grouped_values.items():
            # Convert the group value to string and clean it
            clean_group_value = str(group_value).replace(" ", "_").lower()
            
            results.append(create_result_dict(
                metric_name=f"{metric_name}_{clean_group_value}",
                value=value,
                unit=_determine_unit(metric_config.get("quantity_type", "area")),
                category=metric_config.get("quantity_type", "area"),
                description=metric_config.get("description", ""),
                **file_info or {}
            ))

        if results:
            return pd.DataFrame(results)
        else:
            return pd.DataFrame([create_result_dict(
                metric_name=metric_name,
                error_message="No results calculated",
                **file_info or {}
            )])

    except Exception as e:
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message=str(e),
            **file_info or {}
        )])

def _determine_unit(quantity_type: str) -> str:
    """Helper function to determine the unit based on quantity type."""
    if quantity_type == "volume":
        return "m³"
    elif quantity_type == "area":
        return "m²"
    elif quantity_type == "count":
        return "count"
    return "unknown"

