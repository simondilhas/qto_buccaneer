"""Example script showing how to create a 3D visualization."""

from qto_buccaneer.visualization import create_3d_visualization
import yaml
from pathlib import Path
import os

PLOT_NAME = 'exterior_view'

def main():
    # Get the absolute path of the project root
    project_root = Path(__file__).parent.parent.absolute()
    
    # Define input and output paths
    geometry_dir = project_root / 'projects/001_example_project__public/output/04_json_geometry (optional)'
    properties_path = geometry_dir / 'metadata.json'
    config_path = project_root / 'src/qto_buccaneer/configs/plot_config.yaml'
    output_dir = project_root / 'projects/001_example_project__public/output/05_plots (optional)'
    
    # Verify paths exist
    if not geometry_dir.exists():
        raise FileNotFoundError(f"Geometry directory not found: {geometry_dir}")
    if not properties_path.exists():
        raise FileNotFoundError(f"Properties file not found: {properties_path}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load plot configuration to get plot details
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get the exterior_elements plot configuration
    plot_config = config.get('plots', {}).get(PLOT_NAME, {})
    
    print(f"\nCreating {plot_config.get('title', PLOT_NAME)} visualization...")
    print(f"Description: {plot_config.get('description', '3D view showing external facade elements')}")
    
    output_path = create_3d_visualization(
        geometry_dir=str(geometry_dir),
        properties_path=str(properties_path),
        config_path=str(config_path),
        output_dir=str(output_dir),
        plot_name=PLOT_NAME
    )
    print(f"Saved visualization to {output_path}")

if __name__ == '__main__':
    main() 