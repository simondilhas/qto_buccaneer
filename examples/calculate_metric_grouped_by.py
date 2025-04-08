import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.metrics import calculate_single_grouped_metric
from qto_buccaneer.utils.config import load_config
from qto_buccaneer.utils.ifc_loader import IfcLoader

# Specify the metric you want to calculate
# Examples of grouped metrics:
#METRIC_NAME = "facade_net_area_by_direction"
#METRIC_NAME = "windows_area_by_direction"
#METRIC_NAME = "doors_area_by_direction"
#METRIC_NAME = "facade_net_area_by_direction"
METRIC_NAME = "windows_area_by_direction"

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
        "file_name": Path(loader.file_path).name,
        "file_schema": loader.model.schema,
    }
    
    # Calculate single grouped metric with loaded config
    df = calculate_single_grouped_metric(ifc_path, config, metric_name, file_info)
    print(df)

if __name__ == "__main__":
    main() 