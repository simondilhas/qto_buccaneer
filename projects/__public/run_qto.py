# Starter script for 
from pathlib import Path
from qto_buccaneer import QtoCalculator

project_dir = Path(__file__).parent
ifc_path = project_dir / "input" / "model.ifc"

# TODO: replace with actual logic
if ifc_path.exists():
    print("Processing", ifc_path)
