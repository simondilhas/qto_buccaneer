from pathlib import Path
from qto_buccaneer.utils.config_loader import load_config
from qto_buccaneer.preprocess_ifc import add_spatial_data_to_ifc
from qto_buccaneer.enrich import enrich_ifc_with_df
from qto_buccaneer.metrics import calculate_all_metrics
from qto_buccaneer.reports import export_to_excel
from qto_buccaneer.geometry import calculate_geometry_json_via_api
from qto_buccaneer.plots import create_all_plots
from qto_buccaneer.reports import generate_metrics_report
import pandas as pd

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

# Load configuration
config = load_config(SCRIPT_DIR / "00_workflow_config.yaml")
project_name = config["project_name"]
buildings = config["buildings"]  # List of building dictionaries with 'name' and 'repairs' fields

# Define relative paths
BUILDINGS_DIR = SCRIPT_DIR / "buildings"
CONFIG_DIR = SCRIPT_DIR / "config"


def process_building(building: dict) -> None:
    """
    Process a single building through the workflow steps.
    
    Args:
        building: Building configuration dictionary with 'name' and 'repairs' fields
    """
    building_name = building['name']
    # Set up building-specific paths
    building_dir = BUILDINGS_DIR / building_name

    abstract_bim_ifc = building_dir / "01_abstractbim_model" / f"{building_name}_abstractBIM.ifc"

    #--------------------------------
    # Step 01: set up the buildings directoories
    #--------------------------------

    #--------------------------------
    # Step 02: Add spatial data to IFC
    #--------------------------------

    spatial_data_path = add_spatial_data_to_ifc(
        ifc_file=str(abstract_bim_ifc),
        output_dir=str(building_dir / "02_enriched_spatial_data")
    )
    print(f"✓ Spatial data added: {spatial_data_path}")
    
    
    #--------------------------------
    # Step 03: Enrich IFC with additional data
    #--------------------------------

    enrichment_data_path = CONFIG_DIR / "enrichment_space_table.xlsx"
    print(f"Enrichment data path: {enrichment_data_path}")

    # Read the enrichment data
    df_for_enrichment = pd.read_excel(enrichment_data_path)

    enriched_ifc_path = enrich_ifc_with_df(
        ifc_file=str(spatial_data_path),
        output_dir=str(building_dir / "03_enriched_ifc"),
        df_for_ifc_enrichment=df_for_enrichment
    )

    print(f"✓ IFC enriched: {enriched_ifc_path}")

    #--------------------------------
    # Step 04: Create metrics
    #--------------------------------

    # Load the metrics configuration
    metrics_config_path = CONFIG_DIR / "abstractBIM_metrics_config.yaml"
    metrics_config = load_config(metrics_config_path)

    # Calculate all metrics
    metrics_df = calculate_all_metrics(
        config=metrics_config, 
        ifc_path=enriched_ifc_path)
    
    excel_dir = export_to_excel(
        df=metrics_df, 
        output_dir=str(building_dir / "04_metrics"),
        building_name=building_name)

    print(f"✓ Metrics exported to: {excel_dir}")

    #--------------------------------
    # Step 05: Calculate geometry json for graph visualization
    #--------------------------------

    geometry_json_dir = calculate_geometry_json_via_api(
        ifc_path=enriched_ifc_path,
        output_dir=str(building_dir / "05_geometry_json")
    )

    print(f"✓ Geometry JSON calculated: {geometry_json_dir}")
    
    #-------------------------------- 
    # Step 06: Create Plots
    #--------------------------------

    plots_path = create_all_plots(
        geometry_dir=str(building_dir / "05_geometry_json"),
        properties_path=str(building_dir / "05_geometry_json/metadata.json"),
        config_path=str(CONFIG_DIR / "abstractBIM_plots_config.yaml"),
        output_dir=str(building_dir / "06_plots")
    )

    print(f"✓ Plots created: {plots_path}")

    #--------------------------------
    # Step 07: Create PDF report
    #--------------------------------

    generate_metrics_report(
        metrics_df=metrics_df,
        building_name=building_name,
        plots_dir=str(building_dir / "06_plots"),
        output_dir=str(building_dir / "07_pdf_report"),
        template_path=str(CONFIG_DIR / "abstractBIM_report_template.html"),
    )
    ## Future steps (commented out for now)
    ## create_metrics(enriched_ifc_path)
    ## create_geometry_json(enriched_ifc_path)
    ## create_visualizations(enriched_ifc_path)
    ## create_pdf_report(enriched_ifc_path)

def main():
    """Main workflow execution function."""
    print(f"Starting workflow for project: {project_name}")
    
    # Ensure required directories exist
    BUILDINGS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    for building in buildings:
        process_building(building)
    
    print("\nWorkflow completed!")

if __name__ == "__main__":
    main()
#