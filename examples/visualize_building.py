import json
from pathlib import Path
from datetime import datetime

from qto_buccaneer.visualization import (
    load_plot_config,
    create_single_plot,
    create_all_plots
)

def main():
    # Paths to data files
    data_dir = Path("examples/ifc_json_data")
    geometry_path = data_dir / "geometry/IfcCovering_geometry.json"
    properties_path = data_dir / "metadata/test_metadata.json"
    config_path = Path("src/qto_buccaneer/configs/plot_config.yaml")

    # Load data
    print("Loading data...")
    with open(geometry_path, 'r') as f:
        geometry_data = json.load(f)
    with open(properties_path, 'r') as f:
        properties_data = json.load(f)

    # Load plot configuration
    print("Loading plot configuration...")
    config = load_plot_config(config_path)

    # Create file info
    file_info = {
        "file_name": properties_path.stem,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Example 1: Create a single plot
    print("\nCreating covering visualization...")
    covering_plot = create_single_plot(
        geometry_json=geometry_data,
        properties_json=properties_data,
        config=config,
        plot_name="covering_visualization",
        file_info=file_info
    )
    
    # Save the plot
    output_dir = Path("output/visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)
    covering_plot.write_html(str(output_dir / "covering_visualization.html"))

    # Example 2: Create all plots
    print("\nCreating all plots...")
    all_plots = create_all_plots(
        geometry_json=geometry_data,
        properties_json=properties_data,
        config=config,
        file_info=file_info
    )

    # Save all plots
    for plot_name, plot in all_plots.items():
        plot.write_html(str(output_dir / f"{plot_name}.html"))
        print(f"Saved {plot_name}")

    print("\nVisualization complete! Check the output directory for the HTML files.")

if __name__ == "__main__":
    main() 