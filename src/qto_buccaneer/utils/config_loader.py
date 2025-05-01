import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

def load_config(path: Path, section: Optional[str] = None) -> Dict[str, Any]:
    """Load YAML file and optionally return a section."""
    with path.open() as f:
        config = yaml.safe_load(f)
        return config.get(section, {}) if section else config

# For backward compatibility
load_column_definitions = lambda path: load_config(path, "column_definitions")


# TODO  Remove this function
def create_result_dict(
    metric_name: str,
    error_message: Optional[str] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Create a standardized result dictionary using column definitions from config.
    
    Args:
        metric_name: Name of the metric
        error_message: Optional error message if the calculation failed
        **kwargs: Additional fields to include in the result
        
    Returns:
        Dict[str, Any]: Standardized result dictionary
    """
    result = {
        "metric_name": metric_name,
        "value": None if error_message else kwargs.get('value'),
        "unit": kwargs.get('unit', 'm²'),
        "category": kwargs.get('category', 'unknown'),
        "description": kwargs.get('description', ''),
        "calculation_time": datetime.now(),
        "status": f"error: {error_message}" if error_message else "success"
    }
    # Add any additional info
    result.update({k: v for k, v in kwargs.items() if k not in result})
    return result
