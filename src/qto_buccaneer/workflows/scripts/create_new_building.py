import sys
import argparse
from pathlib import Path
from typing import List, Union, Dict
from datetime import datetime

# Get the absolute path to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.absolute()

# Add src directory to path
src_dir = str(PROJECT_ROOT / "src")
sys.path.append(src_dir)

from qto_buccaneer.workflows.scripts.utils.project_utils import save_project_data, load_workflow, save_building_data

def create_building(project_path: Path, building_name: str) -> bool:
    """Create a new building in the project."""
    building_dir = project_path / building_name
    if building_dir.exists():
        print(f"[!] Building '{building_name}' already exists in project")
        return False
    
    # Create building structure
    building_dir.mkdir(parents=True, exist_ok=True)
    
    # Create building data
    building_data = {
        "metadata": {
            "name": building_name,
            "description": "",  # To be filled in by user
            "created_at": datetime.now().isoformat()
        }
    }
    
    save_building_data(building_dir, building_data)
    
    # Create step folders from workflow config
    config = load_workflow("00_workflow_config.yaml")
    for step in config["steps"]:
        # Get the folder name from the step dictionary
        folder_name = step["folder"]
        step_folder = building_dir / folder_name
        step_folder.mkdir(parents=True, exist_ok=True)
        print(f"[✓] Created step folder: {step_folder.name}")
    
    print(f"[✓] Created building '{building_name}' in project")
    return True

def create_building_in_project(project_name: str, building_name: str) -> bool:
    """Create a new building in an existing project."""
    # Find project directory
    project_path = None
    for path in (PROJECT_ROOT / "projects").glob(f"{project_name}__*"):
        if path.is_dir():
            project_path = path
            break
    
    if not project_path:
        print(f"[!] Project '{project_name}' not found")
        return False
    
    # Create building
    return create_building(project_path, building_name)

def create_buildings_from_list(config: Dict) -> None:
    """Create multiple buildings in the project.
    
    Args:
        config: Workflow configuration containing project name and buildings list
    """
    # Get the project path (two levels up from the script)
    project_path = Path(sys.argv[0]).parent.parent
    
    # Create buildings directory if it doesn't exist
    buildings_dir = project_path / "buildings"
    buildings_dir.mkdir(parents=True, exist_ok=True)
    
    buildings = config["buildings"]
    
    successful = 0
    failed = 0
    
    for building in buildings:
        # Skip empty strings or whitespace-only strings
        if not building or not building.strip():
            print(f"[!] Skipping empty building name")
            failed += 1
            continue
            
        building = building.strip()
        if create_building(buildings_dir, building):
            successful += 1
        else:
            failed += 1
    
    print(f"\nSummary: Created {successful} buildings, {failed} failed")

def create_buildings_from_text(file_path: Union[str, Path]) -> None:
    """Create buildings from a text file (one building name per line)."""
    try:
        # Load the workflow config
        config = load_workflow("00_workflow_config.yaml")
        
        # Read buildings from file and update config
        with open(file_path) as f:
            config["buildings"] = [line.strip() for line in f if line.strip()]
            
        create_buildings_from_list(config)
    except FileNotFoundError:
        print(f"[!] File not found: {file_path}")
    except Exception as e:
        print(f"[!] Error reading file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Create building(s) in a QTO project")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-n", "--name", help="Name of a single building to create")
    group.add_argument("-l", "--list", nargs="+", help="List of building names to create")
    group.add_argument("-f", "--file", help="Path to text file containing building names (one per line)")
    
    args = parser.parse_args()
    
    # Load the workflow config
    config = load_workflow("00_workflow_config.yaml")
    
    if args.name:
        # Update config with single building
        config["buildings"] = [args.name]
        create_buildings_from_list(config)
    elif args.list:
        # Update config with list of buildings
        config["buildings"] = args.list
        create_buildings_from_list(config)
    elif args.file:
        create_buildings_from_text(args.file)

if __name__ == "__main__":
    main() 