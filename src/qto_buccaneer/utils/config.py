import yaml
from typing import Dict, Any, List, Tuple

def load_config(config_path: str) -> dict:
    """
    Load metrics configuration from YAML file
    Example usage:
    config = load_config("src/qto_buccaneer/metrics_config.yaml")
    
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
        
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


def validate_filter(filter_config: Any, metric_name: str, filter_type: str) -> Tuple[List[str], List[str]]:
    """Validate filter structure."""
    messages = []
    errors = []
    
    # Handle empty or missing filters
    if filter_config is None:
        messages.append(f"✓ {filter_type} is not defined (optional)")
        return messages, errors  # Return tuple of lists
        
    if filter_config == {}:
        messages.append(f"✓ {filter_type} is empty (optional)")
        return messages, errors  # Return tuple of lists
        
    if not isinstance(filter_config, dict):
        error_msg = f"{metric_name} {filter_type} must be a dictionary, got: {filter_config}"
        errors.append(error_msg)
        messages.append(f"❌ {error_msg}")
        return messages, errors  # Return tuple of lists
    
    # Check each filter value
    for key, value in filter_config.items():
        valid = (
            isinstance(value, (str, bool, int, float)) or
            isinstance(value, list) or
            (isinstance(value, tuple) and len(value) == 2) or
            value is None
        )
        if valid:
            messages.append(f"✓ Valid {filter_type} value for '{key}': {value}")
        else:
            error_msg = f"{metric_name} {filter_type} has invalid value for '{key}': {value}"
            errors.append(error_msg)
            messages.append(f"❌ Invalid {filter_type} value for '{key}': {value}")
    
    return messages, errors  # Return tuple of lists
    
def validate_metric_structure(metric_config: Dict[str, Any], metric_name: str) -> Tuple[List[str], List[str]]:
    """Validate structure of a single metric configuration."""
    messages = [f"\n  Checking metric '{metric_name}':"]
    errors = []
    
    # Check required fields
    required_fields = {
        "quantity_type", 
        "description",
        "ifc_entity",
        "pset_name",
        "prop_name"
    }
    
    missing = required_fields - set(metric_config.keys())
    if missing:
        errors.append(f"Metric '{metric_name}' missing required fields: {missing}")
        messages.append(f"  ❌ Missing required fields: {missing}")
    else:
        messages.append("  ✓ All required fields present")
    
    # Validate quantity_type
    if metric_config.get("quantity_type") not in ["area", "volume"]:
        errors.append(f"Metric '{metric_name}' has invalid quantity_type: {metric_config.get('quantity_type')}")
        messages.append(f"  ❌ Invalid quantity_type: {metric_config.get('quantity_type')}")
    else:
        messages.append(f"  ✓ Valid quantity_type: {metric_config['quantity_type']}")
    
    # Validate filters
    if "include_filter" in metric_config:
        filter_messages, filter_errors = validate_filter(metric_config["include_filter"], metric_name, "include_filter")
        messages.extend(f"  {msg}" for msg in filter_messages)
        errors.extend(filter_errors)
            
    if "subtract_filter" in metric_config:
        filter_messages, filter_errors = validate_filter(metric_config["subtract_filter"], metric_name, "subtract_filter")
        messages.extend(f"  {msg}" for msg in filter_messages)
        errors.extend(filter_errors)
    
    return messages, errors

def validate_room_metric_structure(metric_config: Dict[str, Any], metric_name: str) -> Tuple[List[str], List[str]]:
    """Validate structure of a single room metric configuration."""
    messages = [f"\n  Checking room metric '{metric_name}':"]
    errors = []
    
    required_fields = {
        "ifc_entity",
        "pset_name",
        "prop_name"
    }
    
    missing = required_fields - set(metric_config.keys())
    if missing:
        errors.append(f"Room metric '{metric_name}' missing required fields: {missing}")
        messages.append(f"  ❌ Missing required fields: {missing}")
    else:
        messages.append("  ✓ All required fields present")
    
    # Validate optional fields
    if "grouping_attribute" in metric_config:
        if isinstance(metric_config["grouping_attribute"], str):
            messages.append("  ✓ Valid grouping_attribute")
        else:
            errors.append(f"Room metric '{metric_name}' grouping_attribute must be a string")
            messages.append("  ❌ grouping_attribute must be a string")
    
    if "include_filter" in metric_config:
        filter_messages, filter_errors = validate_filter(metric_config["include_filter"], metric_name, "include_filter")
        messages.extend(f"  {msg}" for msg in filter_messages)
        errors.extend(filter_errors)
    
    return messages, errors

def validate_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate the complete configuration structure.
    
    Args:
        config: Complete configuration dictionary
    
    Returns:
        tuple: (is_valid, messages)
            - is_valid: True if all checks pass
            - messages: List of validation messages
    """
    messages = []
    errors = []
    
    # Check if config exists
    if not config:
        errors.append("Configuration is empty")
        return False, ["❌ Configuration is empty"]
    messages.append("✓ Configuration exists")

    # Validate top-level structure
    required_sections = {"metrics", "room_based_metrics"}
    missing = required_sections - set(config.keys())
    if missing:
        errors.append(f"Missing required sections: {missing}")
        messages.append(f"❌ Missing required sections: {missing}")
    else:
        messages.append("✓ All required sections present")

    # Validate metrics
    messages.append("\nChecking standard metrics:")
    for metric_name, metric_config in config.get("metrics", {}).items():
        metric_messages, metric_errors = validate_metric_structure(metric_config, metric_name)
        messages.extend(f"  {msg}" for msg in metric_messages)
        errors.extend(metric_errors)

    # Validate room metrics
    messages.append("\nChecking room-based metrics:")
    for metric_name, metric_config in config.get("room_based_metrics", {}).items():
        room_messages, room_errors = validate_room_metric_structure(metric_config, metric_name)
        messages.extend(f"  {msg}" for msg in room_messages)
        errors.extend(room_errors)

    # Add summary
    messages.append("\nValidation Summary:")
    if errors:
        messages.append("❌ Found the following issues:")
        for error in errors:
            messages.append(f"  - {error}")
    else:
        messages.append("✓ All checks passed successfully!")

    return len(errors) == 0, messages

def get_metrics_config(config: dict) -> dict:
    """Get metrics configuration"""
    return config.get("metrics", {})
def get_room_based_metrics_config(config: dict) -> dict:
    """Get room metrics configuration"""
    return config.get("room_based_metrics", {})