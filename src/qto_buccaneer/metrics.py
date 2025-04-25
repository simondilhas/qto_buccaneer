import pandas as pd
from datetime import datetime
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

def calculate_all_metrics(config: Dict, ifc_path: str, file_info: Optional[dict] = None, output_dir: Optional[str] = None) -> pd.DataFrame:
    """
    Calculate all metrics (base, relationship-based, derived, space-based, and grouped) defined in the configuration.

    This function processes an IFC file and calculates all metrics defined in the configuration file. It handles:
    - Standard metrics (single values for the entire project)
    - Room-based metrics (calculations grouped by room)
    - Grouped-by-attribute metrics (calculations grouped by specific attributes)
    - Derived metrics (calculated from other metrics using formulas)

    Args:
        config (Dict): Configuration dictionary containing metric definitions.
                      Usually loaded from metrics_config_abstractBIM.yaml
        ifc_path (str): Path to the IFC file to analyze
        file_info (Optional[dict]): Additional file metadata. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing calculated metrics with columns:
            - metric_name: Name of the metric
            - value: Calculated numeric value
            - unit: Unit of measurement (m², m³, ratio, etc.)
            - category: Type of measurement (area, volume, ratio, count)
            - description: Description of what is being measured
            - calculation_time: When the metric was calculated
            - status: Calculation status (success/error)

    Example:
        ```python
        from qto_buccaneer.utils.config import load_config
        from qto_buccaneer.metrics import calculate_all_metrics

        # Load configuration
        config = load_config("src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml")

        # Calculate metrics
        ifc_path = "path/to/your/model.ifc"
        results = calculate_all_metrics(config, ifc_path)

        # View results
        print(results[["metric_name", "value", "unit"]])

        # Example output:
        #      metric_name      value  unit
        # 0    gross_floor_area  1500.0   m²
        # 1    gross_volume     4500.0   m³
        # 2    windows_count       25.0    -
        ```

    Note:
        The configuration file must follow the structure defined in metrics_config_abstractBIM.yaml.
        See the configs package documentation for details on metric configuration.
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

    This function evaluates a formula using values from previously calculated metrics
    to generate a new derived metric. The formula can reference any metric name
    present in the input DataFrame.

    Args:
        metric_name (str): Name of the derived metric to calculate
        unit (str): Unit of measurement for the result (from config)
        formula (str): Formula to calculate the derived metric using metric names
                      as variables (e.g., "gross_volume / gross_floor_area")
        df_metrics (pd.DataFrame): DataFrame containing the metrics to use in the calculation.
                                 Must include columns: metric_name, value
        file_info (Optional[dict]): Additional file information to include in results

    Returns:
        pd.DataFrame: DataFrame containing the calculated derived metric with columns:
            - metric_name: Name of the derived metric
            - value: Calculated numeric value
            - unit: Unit of measurement
            - category: "derived"
            - description: Description of the metric
            - calculation_time: Timestamp of calculation
            - status: "success" or error message

    Example:
        ```python
        # Example metrics DataFrame
        df_metrics = pd.DataFrame({
            'metric_name': ['gross_volume', 'gross_floor_area'],
            'value': [4500.0, 1500.0],
            'unit': ['m³', 'm²']
        })

        # Calculate average height
        result = calculate_single_derived_metric(
            metric_name="average_height",
            unit="m",
            formula="gross_volume / gross_floor_area",
            df_metrics=df_metrics
        )

        print(result[["metric_name", "value", "unit"]])
        # Output:
        #   metric_name  value unit
        # 0 average_height  3.0    m
        ```

    Note:
        - The formula must use metric names exactly as they appear in df_metrics
        - All metrics referenced in the formula must exist in df_metrics
        - Division by zero and other mathematical errors are handled gracefully
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
    """
    Calculate a single room-based metric, grouping results by space/room attributes.

    This function calculates quantities for building elements (like windows, doors, etc.)
    and groups them based on the spaces they're associated with. It's useful for analyzing
    how elements are distributed across different room types or spaces.

    Args:
        ifc_path (str): Path to the IFC file to analyze
        config (dict): Configuration dictionary containing the metric definition.
                      Must include room_based_metrics section.
        metric_name (str): Name of the room-based metric to calculate
        file_info (dict): Dictionary containing file metadata

    Returns:
        pd.DataFrame: DataFrame containing the calculated metrics grouped by space,
                     with columns:
            - metric_name: Name of the metric
            - space_name: Name or identifier of the space
            - value: Calculated numeric value
            - unit: Unit of measurement (m², m³, count)
            - category: Type of measurement
            - description: Description of what is being measured
            - calculation_time: When the metric was calculated
            - status: Calculation status (success/error)
    """
    
    if metric_name not in config.get('room_based_metrics', {}):
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message="Metric not found in room-based metrics configuration",
            **file_info
        )])

    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    metric_config = config['room_based_metrics'][metric_name]

    try:
        # Use the relationship calculation method for room-based metrics
        results = _process_space_relationship_calculation(qto, metric_name, metric_config, file_info)
        return pd.DataFrame(results)
    except Exception as e:
        return pd.DataFrame([create_result_dict(
            metric_name=metric_name,
            error_message=str(e),
            **file_info
        )])

def calculate_single_room_metric(ifc_path: str, config: dict, metric_name: str, file_info: dict) -> pd.DataFrame:
    """
    Calculate a single room-based metric for analyzing room/space properties.

    This function calculates quantities specifically for rooms/spaces in the IFC model.
    Unlike calculate_single_metric_by_space which groups other elements by space,
    this function directly measures properties of the spaces themselves.

    Args:
        ifc_path (str): Path to the IFC file to analyze
        config (dict): Configuration dictionary containing the metric definition.
                      Must include room_based_metrics section.
        metric_name (str): Name of the room metric to calculate
        file_info (dict): Dictionary containing file metadata

    Returns:
        pd.DataFrame: DataFrame containing the calculated room metrics with columns:
            - metric_name: Name of the metric
            - room_type: Type or category of the room
            - room_name: Name or number of the room
            - value: Calculated numeric value
            - unit: Unit of measurement (m², m³)
            - category: Type of measurement
            - description: Description of what is being measured
            - calculation_time: When the metric was calculated
            - status: Calculation status (success/error)
    """
    
    if metric_name not in config.get('room_based_metrics', {}):
        return _create_error_df(metric_name, "Metric not found in room-based metrics configuration", file_info)
    
    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    metric_config = config['room_based_metrics'][metric_name]
    
    try:
        # Get the room values using _get_elements_by_space
        room_values = qto._get_elements_by_space(
            ifc_entity=metric_config["ifc_entity"],
            pset_name=metric_config["pset_name"],
            prop_name=metric_config["prop_name"],
            grouping_attribute=metric_config["grouping_attribute"],
            room_reference_attribute_guid=metric_config["room_reference_attribute_guid"],
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND")
        )
        
        # Create results for each room/space
        results = []
        for room_name, value in room_values.items():
            results.append({
                "metric_name": metric_name,
                "room_name": room_name,
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
            return _create_error_df(metric_name, "No results calculated", file_info)
    except Exception as e:
        return _create_error_df(metric_name, str(e), file_info)

def calculate_single_grouped_metric(
    ifc_path: str,
    config: dict,
    metric_name: str,
    file_info: Optional[dict] = None,
) -> pd.DataFrame:
    """Calculate a single grouped metric."""
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
        ifc_entity = metric_config["ifc_entity"]
        grouping_attribute = metric_config.get("grouping_attribute")
        grouping_pset = metric_config.get("grouping_pset")
        pset_name = metric_config.get("pset_name")
        prop_name = metric_config.get("prop_name")
        include_filter = metric_config.get("include_filter")
        include_filter_logic = metric_config.get("include_filter_logic", "AND")
        subtract_filter = metric_config.get("subtract_filter")
        subtract_filter_logic = metric_config.get("subtract_filter_logic", "AND")
        quantity_type = metric_config.get("quantity_type", "area")

        # Get grouped values
        grouped_values = qto._get_elements_by_attribute(
            ifc_entity=ifc_entity,
            grouping_attribute=grouping_attribute,
            grouping_pset=grouping_pset,
            include_filter=include_filter,
            include_filter_logic=include_filter_logic,
            subtract_filter=subtract_filter,
            subtract_filter_logic=subtract_filter_logic,
            pset_name=pset_name,
            prop_name=prop_name,
        )

        # Create results for each group
        results = []
        for group_value, value in grouped_values.items():
            # Clean up the group value for use in metric name
            clean_group_value = str(group_value).replace(" ", "_").lower()
            # Create the metric name with the group value appended
            full_metric_name = f"{metric_name}_{clean_group_value}"
            
            results.append({
                "metric_name": full_metric_name,
                "value": value,
                "unit": "m²" if quantity_type == "area" else "m³" if quantity_type == "volume" else "count",
                "category": quantity_type,
                "description": metric_config["description"],
                "calculation_time": datetime.now(),
                "status": "success",
                **(file_info or {})
            })

        if not results:
            return pd.DataFrame([create_result_dict(
                metric_name=metric_name,
                error_message="No results calculated",
                **file_info or {}
            )])

        return pd.DataFrame(results)

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

def _process_space_relationship_calculation(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: Optional[dict] = None) -> list:
    """Process a single relationship-based calculation and format its result."""
    try:
        # Get required parameters from config
        grouping_attribute_orProperty = metric_config["grouping_attribute"]
        
        # Determine if this is a Pset attribute or direct attribute
        if '.' in grouping_attribute_orProperty:
            # For Pset attributes (e.g., "Pset_abstractBIM.Normal")
            pset_name, attr_name = grouping_attribute_orProperty.split('.')
            grouping_name = attr_name.lower()
            # For Pset attributes, we need pset_name
            grouping_pset = pset_name
        else:
            # For direct attributes (e.g., "SpacesName")
            grouping_name = grouping_attribute_orProperty.lower()
            # For direct attributes, we don't need pset_name
            grouping_pset = None
            
        metric_by_group = f"{metric_name}_by_{grouping_name}"
        
        # Get room values with required parameters
        room_values = qto._get_elements_by_space(
            ifc_entity=metric_config["ifc_entity"],
            grouping_pset=grouping_pset,
            grouping_attribute_or_property=grouping_attribute_orProperty,
            room_reference_attribute_guid=metric_config["room_reference_attribute_guid"],
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            metric_pset_name=metric_config.get("metric_pset_name"),
            metric_prop_name=metric_config.get("metric_prop_name")
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
            return results  # Return all results
        else:
            return [create_result_dict(
                metric_name=metric_by_group,
                error_message="No results calculated",
                **file_info or {}
            )]
    except Exception as e:
        return [create_result_dict(
            metric_name=metric_name,
            error_message=str(e),
            **file_info or {}
        )]

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

