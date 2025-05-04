from pathlib import Path
from qto_buccaneer.utils._config_loader import load_config

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

    ifc_path = building_dir / "00_original_input_data" / f"{building_name}.ifc"

    #--------------------------------
    # Step 01: Repair the Model - Change Value
    #--------------------------------
    if building.get('repairs'):
        from qto_buccaneer.repair import apply_repairs
        repaired_ifc_path = apply_repairs(
            ifc_path_or_model=str(ifc_path),
            config=config,
            building_name=building_name,
            output_dir=str(building_dir / "01_model_repaired")
        )
        print(f"✓ Repairs applied: {repaired_ifc_path}")

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