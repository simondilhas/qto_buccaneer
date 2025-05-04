import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def load_config(path: Path, section: Optional[str] = None) -> Dict[str, Any]:
    """
    Load YAML file and optionally return a section.
    
    Args:
        path: Path to the YAML configuration file
        section: Optional section name to extract from the config
        
    Returns:
        Dictionary containing the configuration or the specified section
    """
    try:
        with path.open() as f:
            config = yaml.safe_load(f)
            return config.get(section, {}) if section else config
    except Exception as e:
        logger.error(f"Failed to load config from {path}: {str(e)}")
        raise

# For backward compatibility
load_column_definitions = lambda path: load_config(path, "column_definitions")

def check_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Check the config for the required keys."""
    required_keys = ['filter', 'keys', 'return_values']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required key: {key}")
    return config
