import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator


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
    return pd.DataFrame([{
        "metric_name": metric_name,
        "value": None,
        "unit": "m²",  # Default to m² for errors as we don't have metric_config
        "category": "unknown",
        "description": "",
        "calculation_time": datetime.now(),
        "status": f"error: {error_message}",
        **file_info
    }])
