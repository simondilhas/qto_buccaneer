import yaml

def load_config(config_path: str) -> dict:
    """
    Load metrics configuration from YAML file

    Example usage:
    config = load_config("src/qto_buccaneer/metrics_config.yaml")
    
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
        
def validate_config(config: dict) -> bool:
    """Validate the configuration for the metrics"""
    if not config:
        return False
    return True 

def get_metrics_config(config: dict) -> dict:
    """Get metrics configuration"""
    return config.get("metrics", {})

def get_room_metrics_config(config: dict) -> dict:
    """Get room metrics configuration"""
    return config.get("room_metrics", {})

