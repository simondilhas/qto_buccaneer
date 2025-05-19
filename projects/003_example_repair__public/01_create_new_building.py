# This script is used to create a new building in the project.
# It will create a new building in the buildings directory of the current project.
# The project is determined by the current directory path.

import sys
from pathlib import Path
from qto_buccaneer.scripts.add_new_building_to_project import add_new_building_to_project_from_list
from qto_buccaneer.utils._config_loader import load_config


SCRIPT_DIR = Path(__file__).parent

# Load configuration
config = load_config(SCRIPT_DIR / "00_workflow_config.yaml")
project_name = config["project_name"]
buildings = config["buildings"]  # List of building dictionaries with 'name' and 'repairs' fields

# Extract just the building names for creation
building_names = [building['name'] for building in buildings]

add_new_building_to_project_from_list(
    project_name=project_name,
    buildings=building_names)

