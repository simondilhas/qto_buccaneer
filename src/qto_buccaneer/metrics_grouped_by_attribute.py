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

def calculate_single_grouped_metric(ifc_path: str, config: dict, metric_name: str, file_info: Optional[dict] = None) -> pd.DataFrame:
    """Calculate a single metric grouped by an attribute.
    
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