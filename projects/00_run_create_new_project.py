#!/usr/bin/env python3
"""
This script is used to create a new project. A project is a collection of
buildings that will be processed in the same way.

It will create a new project in the projects directory.

It will also create a new workflow folder in the workflows directory, 
with a standard beginner workflow to add buildings to the project.

"""

import sys
from pathlib import Path
from qto_buccaneer.scripts.create_new_project import create_new_project


# List of projects to create
PROJECTS_TO_CREATE = [
    "003_test_project",
]

# Create all projects in the list
create_new_project(PROJECTS_TO_CREATE, is_private=False)

