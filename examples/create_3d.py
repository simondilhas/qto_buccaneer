from qto_buccaneer.visualize_3d import create_3d_visualization
import yaml
from pathlib import Path

PLOT_NAME = 'exterior_view'

def main():
    # Load plot configuration to get plot details
    config_path = 'src/qto_buccaneer/configs/plot_config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get the exterior_elements plot configuration
    plot_config = config.get('plots', {}).get('exterior_elements', {})
    
    print(f"\nCreating {plot_config.get('title', PLOT_NAME)} visualization...")
    print(f"Description: {plot_config.get('description', '3D view showing external facade elements')}")
    
    output_path = create_3d_visualization(
        geometry_dir='examples/ifc_json_data/geometry',
        properties_path='examples/ifc_json_data/metadata/test_metadata.json',
        config_path=config_path,
        output_dir='output/visualizations',
        plot_name=PLOT_NAME
    )
    print(f"Saved visualization to {output_path}")

if __name__ == '__main__':
    main() 