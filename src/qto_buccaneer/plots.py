"""Module for creating all types of plots from a configuration."""

from pathlib import Path
import yaml

from qto_buccaneer.plots_utils.floorplan import create_floorplan_per_storey
from qto_buccaneer.plots_utils.three_d import create_3d_visualization

def create_all_plots(
    geometry_dir: str,
    properties_path: str,
    config_path: str,
    output_dir: str,
    plot_names: list[str] = None
) -> dict[str, str]:
    """Create all specified plots from the configuration.
    
    Args:
        geometry_dir: Directory containing geometry JSON files (expected one Json per IfcEntity)
        properties_path: Path to properties JSON file
        config_path: Path to plot configuration YAML file
        output_dir: Output directory for the visualizations
        plot_names: Optional list of specific plot names to create. If None, creates all plots.
        
    Returns:
        Dictionary mapping plot names to their output file paths
    """
    # Load plot configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get all plots if none specified
    if plot_names is None:
        plot_names = list(config.get('plots', {}).keys())
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Dictionary to store output paths
    output_paths = {}
    
    # Create each plot
    for plot_name in plot_names:
        plot_config = config['plots'].get(plot_name)
        if not plot_config:
            print(f"Warning: Plot configuration not found for '{plot_name}'")
            continue
            
        print(f"\nCreating {plot_config.get('title', plot_name)} visualization...")
        print(f"Description: {plot_config.get('description', 'No description available')}")
        
        # Determine which visualization function to use based on mode
        mode = plot_config.get('mode', 'floor_plan')
        if mode.startswith('3d'):
            output_path = create_3d_visualization(
                geometry_dir=geometry_dir,
                properties_path=properties_path,
                config_path=config_path,
                output_dir=str(output_dir),
                plot_name=plot_name
            )
            output_paths[plot_name] = output_path
        else:
            # Floor plan returns a dict of storey names to paths
            storey_paths = create_floorplan_per_storey(
                geometry_dir=geometry_dir,
                properties_path=properties_path,
                config_path=config_path,
                output_dir=str(output_dir),
                plot_name=plot_name
            )
            # Add all storey paths to the output paths
            for storey_name, path in storey_paths.items():
                output_paths[f"{plot_name}_{storey_name}"] = path
    
    return output_paths 