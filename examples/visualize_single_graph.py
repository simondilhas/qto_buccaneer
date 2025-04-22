import json
from pathlib import Path
from datetime import datetime
import argparse

from qto_buccaneer.visualization import (
    load_plot_config,
    create_single_plot
)

# Specify which visualization to create
visualization = "floor_layout_by_name"

def main():
    # Set up argument parser for optional arguments only
    parser = argparse.ArgumentParser(description='Visualize a single graph from the plot configuration')
    parser.add_argument('--geometry', default='examples/ifc_json_data/geometry/IfcSpace_geometry.json',
                      help='Path to geometry JSON file')
    parser.add_argument('--properties', default='examples/ifc_json_data/metadata/test_metadata.json',
                      help='Path to properties JSON file')
    parser.add_argument('--config', default='src/qto_buccaneer/configs/plot_config.yaml',
                      help='Path to plot configuration YAML file')
    parser.add_argument('--output', default='output/visualizations',
                      help='Output directory for the visualization')
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.geometry} and {args.properties}...")
    with open(args.geometry, 'r') as f:
        geometry_data = json.load(f)
    with open(args.properties, 'r') as f:
        properties_data = json.load(f)

    # Load plot configuration
    print(f"Loading plot configuration from {args.config}...")
    config = load_plot_config(args.config)

    # Create file info
    file_info = {
        "file_name": Path(args.properties).stem,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Create the specified plot
    print(f"\nCreating {visualization} visualization...")
    plots = create_single_plot(
        geometry_json=geometry_data,
        properties_json=properties_data,
        config=config,
        plot_name=visualization,
        file_info=file_info
    )
    
    # Save the plot(s)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # For floor plans, we get multiple plots (one per storey)
    if len(plots) > 1:
        for storey_name, plot in plots.items():
            output_path = output_dir / f"{visualization}_{storey_name}.html"
            plot.write_html(str(output_path))
            print(f"Saved {storey_name} plot to {output_path}")
    else:
        # For other plots, we get a single plot
        output_path = output_dir / f"{visualization}.html"
        plots['default'].write_html(str(output_path))
        print(f"Saved plot to {output_path}")

    print("\nVisualization complete!")

if __name__ == "__main__":
    main() 