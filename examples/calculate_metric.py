import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.metrics import calculate_single_metric
from qto_buccaneer.utils.config import load_config
from qto_buccaneer.utils.ifc_loader import IfcLoader

#Specify the metric you want to calculate, if None, all metrics will be calculated
#METRIC_NAME = "gross_floor_area" 
#METRIC_NAME = "gross_volume"
#METRIC_NAME = "space_interior_floor_area"
#METRIC_NAME = "space_exterior_area"
#METRIC_NAME = "space_interior_volume"
#METRIC_NAME = "windows_exterior_area"
#METRIC_NAME = "windows_interior_area"
METRIC_NAME = "gross_volume"
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
#METRIC_NAME = "walls_interior_non_loadbearing_net_side_area"



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
    
    # Calculate single metric with loaded config
    df = calculate_single_metric(ifc_path, config, metric_name, file_info)
    print(df)

if __name__ == "__main__":
    main() 