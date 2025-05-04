
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.ifc_qto_calculator import QtoCalculator
from qto_buccaneer.utils._config_loader import load_config
from typing import Optional
import pandas as pd
from datetime import datetime


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