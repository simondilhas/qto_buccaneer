import sys
import argparse
import shutil
from pathlib import Path
from typing import List, Union
from datetime import datetime
import yaml

# Get the absolute path to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.absolute()

# Add src directory to path
src_dir = str(PROJECT_ROOT / "src")
sys.path.append(src_dir)

from qto_buccaneer.workflows.scripts.utils.project_utils import save_project_data

def get_project_base(name: str, is_private: bool) -> Path:
    """Get the base directory for projects based on privacy setting."""
    # Remove any existing privacy postfix if present
    name = name.replace("__private", "").replace("__public", "")
    # Add the correct privacy postfix
    privacy_postfix = "__private" if is_private else "__public"
    return PROJECT_ROOT / "projects" / f"{name}{privacy_postfix}"

def copy_workflow_scripts(project_path: Path, project_name: str, is_private: bool) -> None:
    """Copy workflow templates to the project."""
    # Source paths
    workflows_src = PROJECT_ROOT / "src" / "qto_buccaneer" / "workflows" / "templates"
    
    # Destination paths
    workflows_dst = project_path / "workflows"
    workflows_dst.mkdir(parents=True, exist_ok=True)
    
    # List of essential templates to copy
    essential_templates = [
        "00_workflow_config.yaml",
        "01_run_create_new_building.py",
        "90_run_all_steps.py",
        "91_iterate_over_buildings.py"
    ]
    
    # Copy essential templates
    for template in essential_templates:
        src_file = workflows_src / template
        if src_file.exists():
            if template == "00_workflow_config.yaml":
                # Read the template content
                with open(src_file, 'r') as f:
                    template_content = f.read()
                
                # Replace the project name value while preserving the key and formatting
                updated_content = template_content.replace(
                    'project_name: "add_your_project_name_here"',
                    f'project_name: "{project_name}{"__private" if is_private else "__public"}"'
                )
                
                # Write the updated content
                with open(workflows_dst / template, 'w') as f:
                    f.write(updated_content)
            else:
                shutil.copy2(src_file, workflows_dst / template)
            print(f"[✓] Copied {template} to project workflows")
        else:
            print(f"[!] Template {template} not found in {workflows_src}")
    
    # Load the workflow config to get step scripts
    with open(workflows_dst / "00_workflow_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Copy step runner scripts
    for step in config["steps"]:
        script_name = step["script"]  # Get the script name from the step dictionary
        src_file = workflows_src / script_name
        if src_file.exists():
            shutil.copy2(src_file, workflows_dst / script_name)
            print(f"[✓] Copied {script_name} to project workflows")
        else:
            print(f"[!] Step script {script_name} not found in {workflows_src}")

def create_project(name: str, is_private: bool = False) -> bool:
    """Create a new project with the given name."""
    base = get_project_base(name, is_private)
    if base.exists():
        print(f"[!] Project '{name}' already exists at {base}")
        return False
    
    # Create project structure
    (base / "buildings").mkdir(parents=True, exist_ok=True)

    # Create project data
    project_data = {
        "metadata": {
            "name": name,
            "description": "",  # To be filled in by user
            "created_at": datetime.now().isoformat(),
            "is_private": is_private
        },
        "settings": {
            "default_workflow": "standard"
        }
    }
    
    save_project_data(base, project_data)

    # Create project notes
    notes_content = [
        f"# {name}\n",
        f"\nVisibility: {'Private' if is_private else 'Public'}\n",
        "\n## Project Notes\n\nProject notes go here.\n",
        "\n## Quick Start\n",
        "\nTo create a new building:\n",
        "```bash\n",
        f"cd {base}\n",
        "python -m qto_buccaneer.workflows.scripts.01_create_new_building <building_name>\n",
        "```\n"
    ]
    
    (base / "notes.md").write_text("".join(notes_content))
    
    # Copy workflow templates with updated project name
    copy_workflow_scripts(base, name, is_private)
    
    print(f"[✓] Created {'private' if is_private else 'public'} project structure at: {base}")
    return True

def create_projects_from_list(projects: List[str], is_private: bool = False) -> None:
    """Create multiple projects from a list of names."""
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
    """Create projects from a text file (one project name per line)."""
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
