import yaml
from pathlib import Path
from typing import Dict, Optional, List
import sys

def load_project_data(project_path: Path) -> Dict:
    """Load project data from YAML file.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        Dict: Project data
    """
    config_path = project_path / "project_data.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Project data file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_project_path(project_path: Path, relative_path: str) -> Path:
    """Get absolute path for a project directory or file.
    
    Args:
        project_path: Path to the project directory
        relative_path: Relative path from project root
        
    Returns:
        Path: Absolute path
    """
    return project_path / relative_path

def save_project_data(project_path: Path, data: Dict) -> None:
    """Save project data to YAML file.
    
    Args:
        project_path: Path to the project directory
        data: Project data to save
    """
    config_path = project_path / "project_data.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

def save_building_data(building_path: Path, data: Dict) -> None:
    """Save building data to YAML file.
    
    Args:
        building_path: Path to the building directory
        data: Building data to save
    """
    config_path = building_path / "building_data.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

def load_workflow(config_name: str) -> Dict:
    """Load workflow configuration.
    
    Args:
        config_name: Name of the workflow config file (e.g. '00_workflow_config.yaml')
        
    Returns:
        Dict: Workflow configuration
    """
    # Get the directory where the calling script is located
    script_dir = Path(sys.argv[0]).parent
    config_path = script_dir / config_name
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
            
    raise FileNotFoundError(f"Workflow config not found: {config_path}")

def get_workflow_steps(workflow: Dict, include_optional: bool = False) -> List[Dict]:
    """Get list of workflow steps, optionally including optional steps."""
    if include_optional:
        return workflow['steps']
    return [step for step in workflow['steps'] if step.get('required', True)] 