import yaml
from pathlib import Path
from typing import Dict, Optional, List

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

def load_workflow(project_path: Path, workflow_name: str = "standard") -> Dict:
    """Load workflow configuration.
    
    First tries to load from project's workflows directory,
    then falls back to default templates.
    """
    # Try project-specific workflow first
    project_workflow = project_path / "workflows" / f"{workflow_name}.yaml"
    if project_workflow.exists():
        with open(project_workflow, 'r') as f:
            return yaml.safe_load(f)
    
    # Fall back to default template
    template_path = Path(__file__).parent.parent / "src" / "qto_buccaneer" / "workflows" / "templates" / f"{workflow_name}.yaml"
    if not template_path.exists():
        raise FileNotFoundError(f"Workflow template not found: {workflow_name}")
    
    with open(template_path, 'r') as f:
        return yaml.safe_load(f)

def get_workflow_steps(workflow: Dict, include_optional: bool = False) -> List[Dict]:
    """Get list of workflow steps, optionally including optional steps."""
    if include_optional:
        return workflow['steps']
    return [step for step in workflow['steps'] if step.get('required', True)] 