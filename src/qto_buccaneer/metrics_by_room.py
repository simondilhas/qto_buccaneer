import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator

def calculate_room_metrics(qto: QtoCalculator, room_metrics_config: dict, file_info: dict) -> pd.DataFrame:
    """Calculate room-based metrics."""
    room_results = []
    
    for metric_name, metric_config in room_metrics_config.items():
        try:
            # Use _get_elements_by_space to calculate room-based metrics
            room_values = qto._get_elements_by_space(
                ifc_entity=metric_config["ifc_entity"],
                grouping_attribute=metric_config.get("grouping_attribute", "LongName"),
                room_reference_attribute_guid=metric_config.get("room_reference_attribute_guid", "ePset_abstractBIM.Spaces"),
                include_filter=metric_config.get("include_filter"),
                include_filter_logic=metric_config.get("include_filter_logic", "AND"),
                subtract_filter=metric_config.get("subtract_filter"),
                subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
                pset_name=metric_config.get("pset_name", "Qto_BaseQuantities"),
                prop_name=metric_config.get("prop_name", "NetArea")
            )
            
            # Convert room values to DataFrame records
            for room_name, value in room_values.items():
                room_results.append({
                    "metric_name": metric_name,
                    "room_name": room_name,
                    "value": round(value, 2) if value is not None else None,
                    "unit": metric_config.get("unit", "m²"),
                    "category": "room_based",
                    "description": metric_config.get("description", ""),
                    "calculation_time": datetime.now(),
                    "status": "success",
                    **file_info
                })
                
        except Exception as e:
            room_results.append({
                "metric_name": metric_name,
                "room_name": "unknown",
                "value": None,
                "unit": metric_config.get("unit", "m²"),
                "category": "room_based",
                "description": metric_config.get("description", ""),
                "calculation_time": datetime.now(),
                "status": f"error: {str(e)}",
                **file_info
            })
    
    return pd.DataFrame(room_results)

def calculate_single_room_metric(ifc_path: str, config: dict, metric_name: str, file_info: dict) -> Tuple[pd.DataFrame, Dict]:
    """Calculate a single room-based metric."""
    if metric_name not in config.get('room_based_metrics', {}):
        error_df = _create_error_df(metric_name, "Metric not found in room-based metrics configuration", file_info)
        return error_df, {}

    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    metric_config = config['room_based_metrics'][metric_name]

    try:
        # Use _get_elements_by_space for the specific metric
        room_values = qto._get_elements_by_space(
            ifc_entity=metric_config["ifc_entity"],
            grouping_attribute=metric_config.get("grouping_attribute", "LongName"),
            room_reference_attribute_guid=metric_config.get("room_reference_attribute_guid", "ePset_abstractBIM.Spaces"),
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            subtract_filter=metric_config.get("subtract_filter"),
            subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
            pset_name=metric_config.get("pset_name", "Qto_BaseQuantities"),
            prop_name=metric_config.get("prop_name", "NetArea")
        )

        # Create results
        results = []
        for room_name, value in room_values.items():
            results.append({
                "metric_name": metric_name,
                "room_name": room_name,
                "value": round(value, 2) if value is not None else None,
                "unit": metric_config.get("unit", "m²"),
                "category": "room_based",
                "description": metric_config.get("description", ""),
                "calculation_time": datetime.now(),
                "status": "success",
                **file_info
            })

        if results:
            df = pd.DataFrame(results)
            return df, room_values
        else:
            return _create_error_df(metric_name, "No results calculated", file_info), {}

    except Exception as e:
        return _create_error_df(metric_name, str(e), file_info), {}

def _create_error_df(metric_name: str, error_message: str, file_info: dict) -> pd.DataFrame:
    """Create a DataFrame for error cases."""
    return pd.DataFrame([{
        "metric_name": metric_name,
        "room_name": "unknown",
        "value": None,
        "unit": "m²",
        "category": "room_based",
        "description": "",
        "calculation_time": datetime.now(),
        "status": f"error: {error_message}",
        **file_info
    }]) 