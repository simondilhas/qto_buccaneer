#!/usr/bin/env python3
"""
Script to add new buildings to an existing project.
Creates the necessary folder structure based on the workflow config.
"""

import os
import sys
import yaml
import argparse
from pathlib import Path

def get_project_root() -> Path:
    """Get the root directory of the project."""
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
    
    raise RuntimeError("Could not determine project root directory.")

def add_building_to_project(project_name: str, building_name: str):
    """
    Add a new building to an existing project.
    Creates the necessary folder structure based on the workflow configuration.
    
    Args:
        project_name (str): Name of the project (with __public or __private tag)
        building_name (str): Name of the new building to add
    """
    try:
        # Get the root directory of the project
        root_dir = get_project_root()
        
        # Define project path
        project_path = root_dir / "projects" / project_name
        
        # Check if project exists
        if not project_path.exists():
            raise ValueError(f"Project '{project_name}' not found in {project_path}")
        
        # Load workflow configuration
        workflow_config_path = project_path / "00_workflow_config.yaml"
        if not workflow_config_path.exists():
            raise ValueError(f"Workflow configuration not found in {workflow_config_path}")
        
        with open(workflow_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get building folders from config
        building_folders = config.get('building_folder', [])
        if not building_folders:
            raise ValueError("No building folders defined in workflow configuration")
        
        # Create building directory and subfolders
        building_path = project_path / "buildings" / building_name
        
        # Check if building already exists
        if building_path.exists():
            print(f"Building '{building_name}' already exists, skipping...")
            return
        
        building_path.mkdir(parents=True, exist_ok=True)
        
        # Create all required subfolders
        for folder in building_folders:
            folder_path = building_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"Created folder: {folder_path}")
        
        # Update workflow config with new building
        if 'buildings' not in config:
            config['buildings'] = []
        
        # Check if building is already in config
        building_exists = False
        for building in config['buildings']:
            if isinstance(building, dict) and building.get('name') == building_name:
                building_exists = True
                break
        
        if not building_exists:
            # Add building with empty repairs list
            new_building = {'name': building_name}
            # Only add repairs field if it exists in the original config
            for original_building in buildings:
                if isinstance(original_building, dict) and original_building.get('name') == building_name:
                    if 'repairs' in original_building:
                        new_building['repairs'] = original_building['repairs']
                    break
            
            config['buildings'].append(new_building)
            with open(workflow_config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            print(f"Added building '{building_name}' to workflow configuration")
        
        print(f"\nBuilding '{building_name}' added successfully to project '{project_name}'")
        print(f"Location: {building_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise

def add_new_building_to_project_from_list(project_name: str, buildings: list[str]):
    """
    Add multiple buildings to an existing project.
    Creates the necessary folder structure for each building.
    
    Args:
        project_name (str): Name of the project (with __public or __private tag)
        buildings (list[str]): List of building names to add
    """
    for building_name in buildings:
        add_building_to_project(project_name, building_name)


def main():
    parser = argparse.ArgumentParser(description="Add a new building to an existing project")
    parser.add_argument("project_name", help="Name of the project (with __public or __private tag)")
    parser.add_argument("building_name", help="Name of the new building to add")
    
    args = parser.parse_args()
    
    try:
        add_building_to_project(args.project_name, args.building_name)
    except Exception as e:
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 