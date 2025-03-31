import sys
import os
from pprint import pprint


# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.qto_buccaneer.utils.ifc_loader import IfcLoader
from src.qto_buccaneer.qto_calculator import QtoCalculator

# Load IFC
loader = IfcLoader("examples/Mustermodell V1_abstractBIM.ifc")
qto = QtoCalculator(loader)

# Calculate all standard metrics
print("\n=== Standard Metrics ===")
for metric_name in qto.config["metrics"]:
    try:
        value = qto.calculate_metric(metric_name)
        # Get unit from quantity type
        unit = "m³" if qto.config["metrics"][metric_name].get("quantity_type") == "volume" else "m²"
        print(f"{metric_name}: {value:.2f} {unit}")
    except Exception as e:
        print(f"Error calculating {metric_name}: {e}")

# Calculate all room-based metrics
print("\n=== Room-Based Metrics ===")
for metric_name in qto.config["room_based_metrics"]:
    try:
        values = qto.create_elements_by_room(metric_name)
        print(f"\n{metric_name}:")
        for room, area in values.items():
            print(f"  {room}: {area:.2f} m²")
    except Exception as e:
        print(f"Error calculating {metric_name}: {e}")

# Example with filter override
print("\n=== Examples with Filters ===")
print("Gross Floor Area:")
print(f"  Without subtraction: {qto.calculate_metric('gross_floor_area'):.2f} m²")
print(f"  With LUF subtraction: {qto.calculate_metric('gross_floor_area', subtract_filter={'LongName': 'LUF'}):.2f} m²")

# Example with structural walls of different thicknesses
print("\nStructural Walls:")
print(f"  >15cm (default): {qto.calculate_metric('walls_interior_structural_area'):.2f} m²")
print(f"  >25cm: {qto.calculate_metric('walls_interior_structural_area', include_filter={'Pset_WallCommon.IsExternal': False, 'Width': ['>', 0.25]}):.2f} m²")

