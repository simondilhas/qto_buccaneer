import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict

import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)


from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator

def calculate_all_metrics(qto: QtoCalculator, metrics_config: dict, file_info: dict) -> pd.DataFrame:
    """Calculate standard (non-room) metrics."""

    standard_results = [
        _process_quantity_calculation(qto, metric_name, metric_config, file_info)
        for metric_name, metric_config in metrics_config.items()
    ]
    return pd.DataFrame(standard_results)

def calculate_single_metric(ifc_path: str, config: dict, metric_name: str, file_info: dict) -> pd.DataFrame:
    """Calculate a single standard metric."""
    
    if metric_name not in config.get('metrics', {}):
        return _create_error_df(metric_name, "Metric not found in standard metrics configuration", file_info)
    
    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    metric_config = config['metrics'][metric_name]
    
    try:
        result = _process_quantity_calculation(qto, metric_name, metric_config, file_info)
        return pd.DataFrame([result])
    except Exception as e:
        return _create_error_df(metric_name, str(e), file_info)

def _process_quantity_calculation(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: dict) -> dict:
    """Process a single quantity calculation and format its result."""

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
            "metric_name": metric_name,
            "value": round(value, 2) if value is not None else None,
            "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": metric_config["quantity_type"],
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": "success",
            **file_info,
        }
    except Exception as e:
        return {
            "metric_name": metric_name,
            "value": None,
            "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": "unknown",
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": f"error: {str(e)}",
            **file_info,
        }

def _create_error_df(metric_name: str, error_message: str, file_info: dict) -> pd.DataFrame:
    """Create a DataFrame for error cases."""
    return pd.DataFrame([{
        "metric_name": metric_name,
        "value": None,
        "unit": "m²",
        "category": "unknown",
        "description": "",
        "calculation_time": datetime.now(),
        "status": f"error: {error_message}",
        **file_info
    }]) 



