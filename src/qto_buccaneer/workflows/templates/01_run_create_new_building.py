#!/usr/bin/env python3
"""
This script is used to create a new building in a project.

It will create a new building in the buildings directory of the current project.
The project is determined by the current directory path.
"""

from pathlib import Path
from qto_buccaneer.workflows.scripts.create_new_building import create_buildings_from_list
from qto_buccaneer.workflows.scripts.utils.project_utils import load_workflow

config = load_workflow("00_workflow_config.yaml")

create_buildings_from_list(config)

