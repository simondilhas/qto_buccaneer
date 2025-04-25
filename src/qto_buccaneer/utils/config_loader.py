import yaml
import os
import inspect
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

def find_config_file(config_name: str, search_paths: List[str] = None) -> str:
    """
    Find a configuration file in various possible locations.
    
    Args:
        config_name: Name of the config file to find
        search_paths: Optional list of paths to search. If None, uses default search paths.
    
    Returns:
        str: Path to the found config file
        
    Raises:
        FileNotFoundError: If config file cannot be found in any search path
    """
    if search_paths is None:
        # Get the frame of the caller
        frame = inspect.currentframe()
        try:
            # Go up two frames to get the caller of load_config
            caller_frame = frame.f_back.f_back
            caller_path = caller_frame.f_globals.get('__file__', '')
            caller_dir = os.path.dirname(os.path.abspath(caller_path))
        finally:
            del frame  # Ensure frame is deleted to avoid reference cycles
            
        # Default search paths in order of priority:
        # 1. Directory of the calling script
        # 2. Current working directory
        # 3. Project root directory
        search_paths = [
            caller_dir,
            os.getcwd(),
            str(Path(__file__).parent.parent.parent)
        ]
    
    for path in search_paths:
        config_path = os.path.join(path, config_name)
        if os.path.exists(config_path):
            return config_path
            
    raise FileNotFoundError(
        f"Could not find config file '{config_name}' in any of these locations: {search_paths}"
    )

def load_config(config_name: str, search_paths: List[str] = None) -> dict:
    """
    Load metrics configuration from YAML file.
    
    Args:
        config_name: Name of the config file to load
        search_paths: Optional list of paths to search for the config file
        
    Returns:
        dict: Loaded configuration
        
    Raises:
        FileNotFoundError: If config file cannot be found
    """
    config_path = find_config_file(config_name, search_paths)
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_column_definitions(config_name: str = "metrics_config_abstractBIM.yaml") -> dict:
    """
    Load column definitions from the metrics config file.
    
    Args:
        config_name: Name of the config file containing column definitions
        
    Returns:
        dict: Column definitions from the config file
    """
    config = load_config(config_name)
    return config.get('column_definitions', {})

def create_result_dict(metric_name: str, error_message: str = None, **kwargs) -> dict:
    """
    Create a standardized result dictionary using column definitions from config.
    
    Args:
        metric_name: Name of the metric
        error_message: Optional error message if the calculation failed
        **kwargs: Additional fields to include in the result
        
    Returns:
        dict: Standardized result dictionary
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

def validate_top_level_structure(config: Dict) -> bool:
    """
    Validate that config has required top-level sections.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        bool: True if valid, raises ValueError if not
    """
    required_sections = {"metrics", "room_based_metrics"}
    missing = required_sections - set(config.keys())
    if missing:
        raise ValueError(f"Missing required sections in config: {missing}")
    return True

def validate_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate the configuration file.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, validation_messages)
    """
    messages = []
    is_valid = True
    
    try:
        # Validate top-level structure
        validate_top_level_structure(config)
        messages.append("✓ Top-level structure is valid")
    except ValueError as e:
        is_valid = False
        messages.append(f"❌ {str(e)}")
    
    return is_valid, messages

# ... rest of the validation functions ... 