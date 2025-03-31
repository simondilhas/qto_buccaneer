import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.preprocess_ifc import add_spatial_data_to_ifc
from qto_buccaneer.utils.ifc_loader import IfcLoader


def main():
    # Input IFC file
    ifc_file = "Mustermodell V1_abstractBIM.ifc"
    
    # Add spatial data
    enriched_file = add_spatial_data_to_ifc(ifc_file)
    print(f"Spatial data added to {enriched_file}")

if __name__ == "__main__":
    main() 