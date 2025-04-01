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

def calculate_all_metrics(config: Dict, ifc_path: str, file_info: Optional[dict] = None) -> pd.DataFrame:
    """
    Calculate all metrics defined in the config for a given IFC file.
    
    Args:
        config: Dictionary containing metrics configuration
        filepath: Path to the IFC file
        file_info: Optional dictionary with file information
        
    Returns:
        pd.DataFrame: Combined DataFrame of all metric results
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

def calculate_single_metric(ifc_path: str, config: dict, metric_name: str, file_info: Optional[dict] = None) -> pd.DataFrame:
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



