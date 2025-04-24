"""Example script showing how to create a floor plan visualization."""

from qto_buccaneer.visualization import create_floorplan_per_storey
from pathlib import Path

def main():
    # Get the absolute path of the project root
    project_root = Path(__file__).parent.parent.absolute()
    
    # Define input and output paths
    geometry_dir = project_root / 'projects/001_example_project__public/output/04_json_geometry (optional)'
    properties_path = geometry_dir / 'metadata.json'
    config_path = project_root / 'src/qto_buccaneer/configs/plot_config.yaml'
    output_dir = project_root / 'projects/001_example_project__public/output/05_plots (optional)'
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    create_floorplan_per_storey(
        geometry_dir=str(geometry_dir),
        properties_path=str(properties_path),
        config_path=str(config_path),
        output_dir=str(output_dir),
        plot_name='floor_layout_by_name'
    )

if __name__ == "__main__":
    main() 