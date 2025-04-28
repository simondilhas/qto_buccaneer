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
from typing import Union, Optional
from qto_buccaneer.scripts.building_summary import BuildingSummary

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

def _copy_files_to_building(source_folder: Union[Path, str], building_path: Path, building_name: str) -> None:
    """
    Copy files from source folder to building folders based on file type.
    
    Args:
        source_folder (Union[Path, str]): Path to folder containing files to copy
        building_path (Path): Path to the building directory
        building_name (str): Name of the building
    """
    source_folder = Path(source_folder) if isinstance(source_folder, str) else source_folder
    source_folder = source_folder.resolve()
    
    if not source_folder.exists():
        raise ValueError(f"Source files folder not found: {source_folder}")
        
    for file in source_folder.glob("*"):
        if file.is_file():
            # Determine target folder based on file type
            if file.suffix.lower() == '.ifc':
                if 'abstractbim' in file.name.lower():
                    target_folder = building_path / "01_abstractbim_model"
                    target_file = target_folder / f"{building_name}_abstractBIM.ifc"
                else:
                    target_folder = building_path / "00_original_input_data"
                    target_file = target_folder / file.name
            elif file.suffix.lower() in ['.json', '.yaml', '.yml']:
                target_folder = building_path / "config"
                target_file = target_folder / file.name
            else:
                target_folder = building_path / "00_original_input_data"
                target_file = target_folder / file.name
            
            # Ensure target folder exists
            target_folder.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(file, target_file)
            print(f"Copied {file.name} to {target_folder}")

def _update_workflow_config(project_path: Union[Path, str], building_name: str) -> None:
    """
    Update the workflow configuration with a new building.
    This function only updates the YAML config file, preserving its formatting.
    
    Args:
        project_path (Union[Path, str]): Path to the project directory
        building_name (str): Name of the building to add
    """
    try:
        # Convert to Path object if string is provided
        project_path = Path(project_path) if isinstance(project_path, str) else project_path
        project_path = project_path.resolve()
        
        if not str(project_path).startswith(str(get_project_root() / "projects")):
            raise ValueError(f"Project path must be inside a project directory under projects/")
            
        # Load workflow configuration
        workflow_config_path = project_path / "00_workflow_config.yaml"
        if not workflow_config_path.exists():
            raise ValueError(f"Workflow configuration not found in {workflow_config_path}")
            
        # Read the file line by line to preserve formatting
        with open(workflow_config_path, 'r') as f:
            lines = f.readlines()
            
        # Parse the YAML content
        config = yaml.safe_load(''.join(lines))
            
        # Check if building is already in config
        building_exists = False
        buildings_list = config.get('buildings', [])
        if buildings_list is None:  # Handle case where buildings: is empty
            buildings_list = []
            
        # Ensure all buildings are in dict format
        buildings_list = [{'name': b} if isinstance(b, str) else b for b in buildings_list]
            
        for building in buildings_list:
            if isinstance(building, dict) and building.get('name') == building_name:
                building_exists = True
                break
                
        if not building_exists:
            # Find the buildings section in the file
            buildings_section_start = None
            for i, line in enumerate(lines):
                if line.strip().startswith('buildings:'):
                    buildings_section_start = i
                    break
                    
            if buildings_section_start is None:
                # If no buildings section exists, add it at the end
                new_building = f"  - name: \"{building_name}\"\n"
                lines.append("\nbuildings:\n")
                lines.append(new_building)
            else:
                # Find the indentation level of the buildings section
                indent = len(lines[buildings_section_start]) - len(lines[buildings_section_start].lstrip())
                
                # Add the new building with proper indentation
                new_building = f"{' ' * indent}  - name: \"{building_name}\"\n"
                
                # Find where to insert the new building
                insert_pos = buildings_section_start + 1
                while insert_pos < len(lines) and lines[insert_pos].strip() and not lines[insert_pos].strip().startswith('-'):
                    insert_pos += 1
                    
                lines.insert(insert_pos, new_building)
                
            # Write the file back with preserved formatting
            with open(workflow_config_path, 'w') as f:
                f.writelines(lines)
                
            print(f"Added building '{building_name}' to workflow configuration")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise

def add_building_to_project(project_name: str, building_name: str, source_files_folder: Optional[Union[Path, str]] = None):
    """
    Add a new building to an existing project.
    
    This function:
    1. Creates the necessary folder structure based on the workflow configuration
    2. Updates the workflow configuration with the new building
    3. Optionally copies files from a source folder to the building's folders
    4. Creates a building summary YAML file with metadata about the building
    
    Args:
        project_name (str): Name of the project (with __public or __private tag)
        building_name (str): Name of the new building to add
        source_files_folder (Optional[Union[Path, str]]): Path to folder containing files to copy
    
    Returns:
        None
    
    Raises:
        ValueError: If the project doesn't exist or has invalid configuration
    """
    try:
        # Get project root and validate project path
        project_root = get_project_root()
        project_path = project_root / "projects" / project_name
        
        if not project_path.exists():
            raise ValueError(f"Project '{project_name}' not found in {project_root / 'projects'}")
            
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
        building_path.mkdir(parents=True, exist_ok=True)
        
        # Create all required subfolders
        for folder in building_folders:
            (building_path / folder).mkdir(parents=True, exist_ok=True)
            print(f"Created folder: {folder}")
        
        # Create building summary in the building folder
        summary_path = building_path / f"{building_name}_summary.yaml"
        
        # Only create summary if it doesn't exist
        if not summary_path.exists():
            # Create and update building summary using template
            summary = BuildingSummary(summary_path)
            summary.set_name(building_name)  # Set the actual building name
            summary.add_metric("description", f"This is {building_name}")
            summary.save()
            print(f"Created building summary for '{building_name}'")
        else:
            print(f"Building summary for '{building_name}' already exists, skipping creation")
        
        # Update workflow configuration
        _update_workflow_config(project_path, building_name)
        
        # Copy files if source folder is provided
        if source_files_folder:
            _copy_files_to_building(source_files_folder, building_path, building_name)
            
        print(f"Successfully added building '{building_name}' to project '{project_name}'")
        
    except Exception as e:
        print(f"Error adding building to project: {e}", file=sys.stderr)
        raise

def add_new_building_to_project_from_list(project_name: str, buildings: list[Union[str, dict]]) -> None:
    """
    Add multiple buildings to a project from a list of building names or dictionaries.
    
    Args:
        project_name (str): Name of the project
        buildings (list[Union[str, dict]]): List of building names or dictionaries with 'name' key
    
    Example:
        >>> add_new_building_to_project_from_list("example_project__public", ["Building1", "Building2"])
        >>> # Or with dictionaries:
        >>> add_new_building_to_project_from_list("example_project__public", [{"name": "Building1"}, {"name": "Building2"}])
    """
    for building in buildings:
        # Extract building name from dictionary if needed
        building_name = building["name"] if isinstance(building, dict) else building
        add_building_to_project(project_name, building_name)

def create_buildings_from_files(input_folder_path: Union[Path, str], project_path: Union[Path, str], target_folder: str = "00_original_input_data") -> None:
    """
    Create buildings from files in the input folder.
    This function:
    1. Gets all model names from the input folder
    2. Adds them to the YAML config as dictionaries
    3. Uses add_new_building_to_project_from_list to create the buildings
    4. Copies files to each building's target folder
    
    Args:
        input_folder_path (Union[Path, str]): Path to the folder containing building files
        project_path (Union[Path, str]): Path to the project directory
        target_folder (str): Name of the folder to copy files to (default: "00_original_input_data")
    """
    try:
        # Convert to Path objects if strings are provided
        input_folder_path = Path(input_folder_path) if isinstance(input_folder_path, str) else input_folder_path
        project_path = Path(project_path) if isinstance(project_path, str) else project_path
        
        # Ensure paths are absolute
        input_folder_path = input_folder_path.resolve()
        project_path = project_path.resolve()
        
        if not str(project_path).startswith(str(get_project_root() / "projects")):
            raise ValueError(f"Project path must be inside a project directory under projects/")
            
        project_name = project_path.name
        
        # Get all model names from the input folder
        model_names = []
        for item in input_folder_path.iterdir():
            if item.is_file():
                # Use the filename without extension as the model name
                model_name = item.stem
                model_names.append(model_name)
        
        if not model_names:
            raise ValueError(f"No files found in {input_folder_path}")
            
        # Add each model to the YAML config
        for model_name in model_names:
            _update_workflow_config(project_path, model_name)
            
        # Use the existing function to create buildings from the list
        add_new_building_to_project_from_list(project_name, model_names)
        
        # Copy files to each building's target folder
        for model_name in model_names:
            building_path = project_path / "buildings" / model_name
            target_path = building_path / target_folder
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            source_file = input_folder_path / f"{model_name}{item.suffix}"
            if source_file.exists():
                import shutil
                shutil.copy2(source_file, target_path / source_file.name)
                print(f"Copied {source_file.name} to {target_path}")
        
        print(f"\nCreated {len(model_names)} buildings in project '{project_name}'")
        print(f"Models processed: {', '.join(model_names)}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise

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