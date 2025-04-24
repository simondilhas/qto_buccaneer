from qto_buccaneer.visualize_floorplan import create_floorplan_per_storey
from qto_buccaneer.visualize_3d import create_3d_visualization
import os
import yaml
import json
from pathlib import Path

def create_all_plots():
    # Define input and output paths
    geometry_dir = Path('projects/001_example_project__public/output/04_json_geometry')
    properties_path = geometry_dir / 'metadata.json'
    config_path = Path('src/qto_buccaneer/configs/plot_config.yaml')
    output_dir = Path('projects/001_example_project__public/output/05_plots')
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load plot configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get all plot names from the configuration
    plot_names = list(config['plots'].keys())
    
    # Generate each plot
    for plot_name in plot_names:
        print(f"\nCreating plot: {plot_name}")
        try:
            # Check if this is a 3D plot
            plot_config = config['plots'][plot_name]
            if plot_config.get('mode', '').startswith('3d'):
                print(f"Creating 3D visualization for {plot_name}")
                output_path = create_3d_visualization(
                    geometry_dir=str(geometry_dir),
                    properties_path=str(properties_path),
                    config_path=str(config_path),
                    output_dir=str(output_dir),
                    plot_name=plot_name
                )
            else:
                print(f"Creating floor plan for {plot_name}")
                output_path = create_floorplan_per_storey(
                    geometry_dir=str(geometry_dir),
                    properties_path=str(properties_path),
                    config_path=str(config_path),
                    output_dir=str(output_dir),
                    plot_name=plot_name
                )
            print(f"Successfully created {plot_name} and saved to {output_path}")
        except Exception as e:
            print(f"Error creating {plot_name}: {str(e)}")

if __name__ == "__main__":
    create_all_plots() 