import sys
from pathlib import Path
import pandas as pd

# Add src directory to path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.metrics import calculate_all_metrics
from qto_buccaneer.utils.config import load_config
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.reports import export_to_excel

def main():
    # Project configuration
    projects_dir = Path(__file__).parent
    project_name = "001_example_project__public"
    
    # Get the enriched IFC file from step 02
    enriched_dir = projects_dir / project_name / "output" / "02_above_below_ground"
    if not enriched_dir.exists():
        raise FileNotFoundError(f"Enriched directory not found at: {enriched_dir}")
    
    # List all IFC files in the directory for debugging
    print(f"\nAvailable files in {enriched_dir}:")
    for file in enriched_dir.glob("*"):
        print(f"  - {file.name}")
    
    # Find the enriched IFC file - try different patterns
    enriched_files = list(enriched_dir.glob("*.ifc"))
    if not enriched_files:
        raise FileNotFoundError(f"No IFC files found in: {enriched_dir}")
    
    ifc_file = enriched_files[0]  # Use the first matching file
    print(f"\nFound IFC file: {ifc_file}")
    
    # Verify input file exists
    ifc_file_str = str(ifc_file)
    if not ifc_file.exists():
        raise FileNotFoundError(f"IFC file not found at: {ifc_file_str}")
    
    print(f"Processing IFC file: {ifc_file_str}")
    
    # Create output directory
    output_dir = projects_dir / project_name / "output" / "03_quantities"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load configuration
    config = load_config("src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml")
    
    # Get file information
    loader = IfcLoader(ifc_file_str)
    file_info = {
        "file_name": Path(loader.file_path).name,
        "file_schema": loader.model.schema,
    }
    
    # Calculate all metrics
    print("\nCalculating metrics...")
    all_metrics = calculate_all_metrics(config, ifc_file_str, file_info)
    print("\nCalculated metrics:")
    print(all_metrics)
    
    # Export to Excel
    ifc_filename = Path(ifc_file).stem  # Get filename without extension
    excel_path = output_dir / f"{ifc_filename}_metrics.xlsx"
    export_to_excel(all_metrics, str(excel_path))
    print(f"\nExported metrics to: {excel_path}")

if __name__ == "__main__":
    main()