import sys
from pathlib import Path
import yaml

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.metrics import calculate_single_value
from qto_buccaneer.reports import format_console_output, export_to_excel
from qto_buccaneer.utils.config import load_config

# Debug the config loading
config_path = "src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml"
abs_config_path = Path(config_path).absolute()
print(f"\nConfig file path: {abs_config_path}")
print(f"Config file exists: {abs_config_path.exists()}")

# Read the raw file
print("\nRaw config file contents:")
with open(abs_config_path, 'r') as f:
    raw_config = yaml.safe_load(f)
    print("\nMetrics in raw config:")
    for metric in sorted(raw_config['metrics'].keys()):
        print(f"- {metric}")

# Compare with loaded config
loaded_config = load_config(config_path)
print("\nMetrics in loaded config:")
for metric in sorted(loaded_config['metrics'].keys()):
    print(f"- {metric}")

#Specify the metric you want to calculate, if None, all metrics will be calculated
#METRIC_NAME = "gross_floor_area" 
#METRIC_NAME = "space_interior_floor_area"
#METRIC_NAME = "space_exterior_area"
#METRIC_NAME = "space_interior_volume"
#METRIC_NAME = "windows_exterior_area"
#METRIC_NAME = "windows_interior_area"
#METRIC_NAME = "space_gross_volume"
#METRIC_NAME = "windows_exterior_area"
#METRIC_NAME = "windows_interior_area"
#METRIC_NAME = "interior_walls_side_area"
#METRIC_NAME = "exterior_walls_side_area"
#METRIC_NAME = "facade_net_area"
#METRIC_NAME = "facade_gross_area"
#METRIC_NAME = "wall_surface_interior_net_area"
#METRIC_NAME = "slab_balcony_net_area"
#METRIC_NAME = "slab_interior_net_area"
#METRIC_NAME = "roof_net_area"
#METRIC_NAME = "base_slab_area"
#METRIC_NAME = "doors_exterior_area"
#METRIC_NAME = "doors_interior_area"
#METRIC_NAME = "walls_interior_loadbearing_net_side_area"
METRIC_NAME = "walls_interior_non_loadbearing_net_side_area"
#METRIC_NAME = "wall_surface_interior_net_area"

def print_available_metrics():
    config_path = "src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml"
    config = load_config(config_path)
    print("\nAvailable metrics:")
    for metric in sorted(config['metrics'].keys()):
        print(f"- {metric}")
    print("\n")

def main():
    # Example usage
    ifc_path = "examples/Mustermodell V1_abstractBIM.ifc"
    config_path = "src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml"
    
    # Debug the config path
    print(f"\nAttempting to load config from: {Path(config_path).absolute()}")
    
    # Load and verify the raw config content
    with open(config_path, 'r') as f:
        raw_config = f.read()
    print("\nRaw config contains the metric name:", 
          "walls_interior_non_loadbearing_net_side_area" in raw_config)
    
    # Print available metrics first
    
    
    # Add metric name parameter (you can specify which metric to calculate)
    metric_name = METRIC_NAME
    if len(sys.argv) > 1:
        metric_name = sys.argv[1]

    print(f"Attempting to calculate metric: {metric_name}")

    # Modified function call to include metric_name
    df, room_results = calculate_single_value(ifc_path, config_path, metric_name)
    
    # Print formatted results
    format_console_output(df, room_results)


if __name__ == "__main__":
    print_available_metrics()
    #main() 