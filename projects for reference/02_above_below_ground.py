import sys
from pathlib import Path
import pandas as pd

# Add src directory to path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.preprocess_ifc import add_spatial_data_to_ifc
from qto_buccaneer.utils.ifc_loader import IfcLoader

def main():
    # Project configuration
    projects_dir = Path(__file__).parent
    project_name = "001_example_project__public"
    
    # Get the enriched IFC file from step 02
    enriched_dir = projects_dir / project_name / "output" / "01_enriched"
    if not enriched_dir.exists():
        raise FileNotFoundError(f"Enriched directory not found at: {enriched_dir}")
    
    # Find the enriched IFC file
    enriched_files = list(enriched_dir.glob("*_enriched.ifc"))
    if not enriched_files:
        raise FileNotFoundError(f"No enriched IFC files found in: {enriched_dir}")
    
    ifc_file = enriched_files[0]  # Use the first matching file
    print(f"Found enriched IFC file: {ifc_file}")
    
    # Verify input file exists
    ifc_file_str = str(ifc_file)
    if not ifc_file.exists():
        raise FileNotFoundError(f"IFC file not found at: {ifc_file_str}")
    
    print(f"Processing IFC file: {ifc_file_str}")
    
    # Create output directory
    output_dir = projects_dir / project_name / "output" / "02_above_below_ground"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Add spatial data to IFC
    print("\nAdding spatial data...")
    final_enriched_path = add_spatial_data_to_ifc(
        ifc_file=ifc_file_str,
        pset_name="Pset_SpatialData",
        ifc_entity="IfcSpace",
        output_dir=str(output_dir)
    )
    
    print(f"\nCreated enriched IFC file with spatial data: {final_enriched_path}")

if __name__ == "__main__":
    main() 