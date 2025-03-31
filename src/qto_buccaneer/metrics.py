import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict, Literal, List
import yaml

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator
from qto_buccaneer.reports import format_console_output, export_to_excel
from qto_buccaneer.utils.config import load_config

config = load_config("src/qto_buccaneer/metrics_config.yaml")


def calculate_all_metrics(ifc_path: str, config_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate all metrics defined in the configuration file.
    
    Args:
        ifc_path: Path to the IFC file
        config_path: Path to config file
    
    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: 
            - Standard metrics DataFrame with columns: metric_name, value, unit, etc.
            - Room metrics DataFrame with columns: room_name, metric_name, value, unit, etc.
    """
    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    config = load_config(config_path)

    file_info = {
        "filename": Path(ifc_path).name,
        **loader.get_project_info()
    }

    # Calculate standard metrics
    standard_results = [
        _calculate_single_metric(qto, metric_name, metric_config, file_info)
        for metric_name, metric_config in config.get("metrics", {}).items()
    ]
    standard_df = pd.DataFrame(standard_results)
    
    # Calculate room-based metrics
    room_results = []
    for metric_name, metric_config in config.get("room_metrics", {}).items():
        result = _calculate_metric_per_room(qto, metric_name, metric_config, file_info)
        if result is not None:
            room_results.extend(result)
    
    room_df = pd.DataFrame(room_results)

    return standard_df, room_df

def _calculate_single_metric(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: dict) -> dict:
    """Internal helper function to calculate a single metric."""
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
        
        return {
            **file_info,
            "metric_name": metric_name,
            "value": round(value, 2) if value is not None else None,
            "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": metric_config["quantity_type"],
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": "success"
        }
    except Exception as e:
        return {
            **file_info,
            "metric_name": metric_name,
            "value": None,
            "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": "unknown",
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": f"error: {str(e)}"
        }

def _calculate_metric_per_room(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: dict) -> List[dict]:
    """Internal helper function to calculate a room-based metric."""
    try:
        values = qto.calculate_by_room(
            ifc_entity=metric_config["ifc_entity"],
            grouping_attribute=metric_config.get("grouping_attribute", "LongName"),
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            pset_name=metric_config["pset_name"],
            prop_name=metric_config["prop_name"]
        )
        
        # Convert room results to list of dicts for DataFrame
        return [
            {
                **file_info,
                "metric_name": metric_name,
                "room_name": room_name,
                "value": round(value, 2) if value is not None else None,
                "unit": "m²",  # Assuming all room metrics are areas
                "calculation_time": datetime.now(),
                "status": "success"
            }
            for room_name, value in values.items()
        ]
    except Exception as e:
        print(f"Error calculating {metric_name}: {e}")
        return None


    
