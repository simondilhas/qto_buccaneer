import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.preprocess_ifc import add_spatial_data_to_ifc
from qto_buccaneer.utils.ifc_loader import IfcLoader


def main():
    # Get the absolute path to the data directory relative to this script
    script_dir = Path(__file__).parent
    data_dir = script_dir
    ifc_file = data_dir / "Mustermodell V1_abstractBIM.ifc"
    
    # Convert to string and ensure the path exists
    ifc_file_str = str(ifc_file)
    if not ifc_file.exists():
        raise FileNotFoundError(f"IFC file not found at: {ifc_file_str}")
        
    print(f"Processing IFC file: {ifc_file_str}")
    enriched_file = add_spatial_data_to_ifc(ifc_file_str)
    print(f"Created enriched file: {enriched_file}")

if __name__ == "__main__":
    main() 