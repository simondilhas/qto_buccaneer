#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
import yaml
from pathlib import Path

def get_project_root() -> Path:
    """Get the root directory of the project."""
    # Try to find the root directory by looking for key files/directories
    current_dir = Path(__file__).parent.parent
    root_markers = [
        'pyproject.toml',
        'setup.py',
        'requirements.txt',
        '.git',
        'src'
    ]
    
    while current_dir != current_dir.parent:
        if any((current_dir / marker).exists() for marker in root_markers):
            return current_dir
        current_dir = current_dir.parent
    
    raise RuntimeError("Could not determine project root directory. Please run this script from within the project directory.")

def update_workflow_config(project_path: Path, project_name: str) -> None:
    """
    Update the workflow configuration file with the new project name.
    Preserves the original YAML formatting including comments and whitespace.
    
    Args:
        project_path (Path): Path to the project directory
        project_name (str): New project name to set in the config
    """
    workflow_config_path = project_path / "00_workflow_config.yaml"
    if workflow_config_path.exists():
        # Read the file line by line to preserve formatting
        with open(workflow_config_path, 'r') as f:
            lines = f.readlines()
        
        # Find and update the project_name line
        for i, line in enumerate(lines):
            if 'project_name:' in line:
                # Split the line at the colon to preserve indentation
                parts = line.split(':', 1)
                if len(parts) == 2:
                    # Preserve the indentation and add the new project name with quotes
                    indent = len(parts[0]) - len(parts[0].lstrip())
                    lines[i] = f"{' ' * indent}project_name: \"{project_name}\"\n"
                break
        
        # Write the file back with preserved formatting
        with open(workflow_config_path, 'w') as f:
            f.writelines(lines)

def create_new_project(project_names: list[str], is_private: bool = False, template_name: str = "example_project_template__public"):
    """
    Create new projects based on a template.
    
    Args:
        project_names (list[str]): List of names for the new projects
        is_private (bool): Whether the project should be private (default: False)
        template_name (str): Name of the template to use
    """
    try:
        # Get the root directory of the project
        root_dir = get_project_root()
        
        # Define template path
        template_path = root_dir / "templates" / template_name
        
        # Check if template exists
        if not template_path.exists():
            raise ValueError(f"Template '{template_name}' not found in {template_path}")
        
        for project_name in project_names:
            # Add appropriate tag to project name
            tag = "__private" if is_private else "__public"
            tagged_project_name = f"{project_name}{tag}"
            
            # Define project path
            projects_path = root_dir / "projects" / tagged_project_name
            
            # Check if project already exists
            if projects_path.exists():
                print(f"Warning: Project '{tagged_project_name}' already exists in {projects_path}, skipping...")
                continue
            
            # Create project directory
            projects_path.mkdir(parents=True)
            
            # Copy template to new project
            shutil.copytree(template_path, projects_path, dirs_exist_ok=True)
            
            # Update the workflow config file
            update_workflow_config(projects_path, tagged_project_name)
            
            print(f"Project '{tagged_project_name}' created successfully in {projects_path}")
            print("\nNext steps:")
            print(f"1. cd {projects_path}")
            print("2. Review and modify the project configuration as needed")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if isinstance(e, (OSError, shutil.Error)):
            print("\nThis might be due to:")
            print("- Insufficient permissions")
            print("- Disk space issues")
            print("- File system errors")
        raise

def main():
    parser = argparse.ArgumentParser(description="Create a new project from a template")
    parser.add_argument("project_name", help="Name of the new project")
    parser.add_argument("--template", default="example_project_template__public",
                       help="Name of the template to use (default: example_project_template__public)")
    parser.add_argument("--private", action="store_true",
                       help="Create a private project (default: public)")
    
    args = parser.parse_args()
    
    try:
        create_new_project([args.project_name], is_private=args.private, template_name=args.template)
    except Exception as e:
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 