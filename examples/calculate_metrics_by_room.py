import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.metrics_by_room import calculate_room_metrics, calculate_single_room_metric
from qto_buccaneer.utils.config import load_config
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator

# Specify the room-based metric you want to calculate
METRIC_NAME = "windows_by_room"  # Example room-based metric

def main():
    # Example usage
    ifc_path = "examples/Mustermodell V1_abstractBIM.ifc"
    config_path = "src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml"
    
    # Load the configuration file
    config = load_config(config_path)
    
    # Add metric name parameter (you can specify which metric to calculate)
    metric_name = METRIC_NAME
    if len(sys.argv) > 1:
        metric_name = sys.argv[1]

    # Create loader instance
    loader = IfcLoader(ifc_path)
    
    # Create file info dictionary using loader attributes
    file_info = {
        "file_path": loader.file_path,
        "file_name": Path(loader.file_path).name,
        "file_type": "IFC",
        "file_schema": loader.model.schema,
    }
    
    # Calculate single room metric with loaded config
    df= calculate_single_room_metric(ifc_path, config, metric_name, file_info)
    print(df)
    #
    ## Print formatted results with room details
    #if df is not None:
    #    format_console_output(df)
    #else:
    #    print("No results to display")
#
    #print(df)

if __name__ == "__main__":
    main() 