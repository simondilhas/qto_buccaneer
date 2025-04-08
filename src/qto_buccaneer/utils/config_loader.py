import yaml
from pathlib import Path

def load_column_definitions() -> dict:
    """Load column definitions from the metrics config file."""
    config_path = Path(__file__).parent.parent / "configs" / "metrics_config_abstractBIM.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('column_definitions', {})

def create_result_dict(metric_name: str, error_message: str = None, **kwargs) -> dict:
    """Create a standardized result dictionary using column definitions from config."""
    from datetime import datetime
    
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