import sys
import argparse
from pathlib import Path
from typing import List, Union
from datetime import datetime

# Get the absolute path to the project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

TEMPLATE = [
    "input",
    "output/00_abstractBIM",
    "output/01_enriched",
    "output/02_above_below_ground",
    "output/03_quantities",
    "output/04_json_geometry (optional)",
    "output/05_plots (optional)",
    "output/06_reports"
]

from .project_utils import save_project_data

def get_project_base(name: str, is_private: bool) -> Path:
    """Get the base directory for projects based on privacy setting.
    
    Args:
        name: Name of the project
        is_private: Whether the project should be private
        
    Returns:
        Path: Base directory for the project
    """
    # Remove any existing privacy postfix if present
    name = name.replace("__private", "").replace("__public", "")
    # Add the correct privacy postfix
    privacy_postfix = "__private" if is_private else "__public"
    return PROJECT_ROOT / "projects" / f"{name}{privacy_postfix}"

def create_project(name: str, is_private: bool = False) -> bool:
    """Create a new project with the given name.
    
    Args:
        name: Name of the project to create
        is_private: Whether the project should be private In gitignore everything with projects/*__private wont be uploaded to github
        
    Returns:
        bool: True if project was created successfully, False otherwise
    """
    base = get_project_base(name, is_private)
    if base.exists():
        print(f"[!] Project '{name}' already exists at {base}")
        return False
    
    for path in TEMPLATE:
        dir_path = base / path
        dir_path.mkdir(parents=True, exist_ok=True)

    # Create project_data.yaml
    project_data = {
        "metadata": {
            "name": name,
            "description": "",  # To be filled in by user
            "created_at": datetime.now().isoformat(),
            "is_private": is_private
        },
        "settings": {
            "address": "",  # To be filled in by user
            "ifc_file": ""  # To be filled in by user
        }
    }
    
    save_project_data(base, project_data)

    # Create notes.md
    notes_content = [
        f"# {name}\n",
        f"\nVisibility: {'Private' if is_private else 'Public'}\n",
        "\n## Project Notes\n\nProject notes go here.\n"
    ]
    
    (base / "notes.md").write_text("".join(notes_content))
    
    # Create run_qto.py
    (base / "run_qto.py").write_text(
        f"""# Starter script for {name}
from pathlib import Path
from scripts.project_utils import load_project_data

project_dir = Path(__file__).parent

# Load project data
project_data = load_project_data(project_dir)

ifc_path = project_dir / "input" / project_data["settings"]["ifc_file"]

# TODO: replace with actual logic
if ifc_path.exists():
    print("Processing", ifc_path)
"""
    )
    print(f"[✓] Created {'private' if is_private else 'public'} project folder structure at: {base}")
    return True

def create_projects_from_list(projects: List[str], is_private: bool = False) -> None:
    """Create multiple projects from a list of names.
    
    Args:
        projects: List of project names to create
        is_private: Whether the projects should be private
    """
    successful = 0
    failed = 0
    
    for project in projects:
        # Skip empty strings or whitespace-only strings
        if not project or not project.strip():
            print(f"[!] Skipping empty project name")
            failed += 1
            continue
            
        project = project.strip()
        if create_project(project, is_private):
            successful += 1
        else:
            failed += 1
    
    print(f"\nSummary: Created {successful} projects, {failed} failed")

def create_projects_from_text(file_path: Union[str, Path], is_private: bool = False) -> None:
    """Create projects from a text file (one project name per line).
    
    Args:
        file_path: Path to the text file
        is_private: Whether the projects should be private
    """
    try:
        with open(file_path) as f:
            projects = [line.strip() for line in f if line.strip()]
        create_projects_from_list(projects, is_private)
    except FileNotFoundError:
        print(f"[!] File not found: {file_path}")
    except Exception as e:
        print(f"[!] Error reading file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Create new QTO project(s)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-n", "--name", help="Name of a single project to create")
    group.add_argument("-l", "--list", nargs="+", help="List of project names to create")
    group.add_argument("-f", "--file", help="Path to text file containing project names (one per line)")
    parser.add_argument("-p", "--private", action="store_true", help="Create project(s) as private (default: public)")
    
    args = parser.parse_args()
    
    if args.name:
        create_project(args.name, args.private)
    elif args.list:
        create_projects_from_list(args.list, args.private)
    elif args.file:
        create_projects_from_text(args.file, args.private)

if __name__ == "__main__":
    main()
