import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from scripts.create_new_project import create_projects_from_list

create_projects_from_list([
    "002_test",
], is_private=False)
