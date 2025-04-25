import shutil
from pathlib import Path

def setup_test_data():
    """Copy geometry files for testing."""
    # Source and destination directories
    src_dir = Path("examples/ifc_json_data/geometry")
    dest_dir = Path("tests/test_data/geometry")
    
    # Create destination directory if it doesn't exist
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # List of files to copy
    files_to_copy = [
        "IfcCovering_geometry.json",
        "IfcWindow_geometry.json",
        "IfcWallStandardCase_geometry.json",
        "IfcSlab_geometry.json",
        "IfcDoor_geometry.json",
        "IfcOpeningElement_geometry.json",
        "IfcSpace_geometry.json"
    ]
    
    # Copy files
    for file_name in files_to_copy:
        src_path = src_dir / file_name
        dest_path = dest_dir / file_name
        shutil.copy2(src_path, dest_path)
        print(f"Copied {file_name}")

if __name__ == "__main__":
    setup_test_data() 