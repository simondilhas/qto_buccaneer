from pathlib import Path
import ifcopenshell
from qto_buccaneer.utils.ifc_loader import IfcLoader

# Get the IFC file path
TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")

# Load the file
loader = IfcLoader(TEST_IFC_PATH)

# Get door information
print("\nDoor Information:")
print("----------------")
doors = loader.model.by_type("IfcDoor")
total_exterior_area = 0.0

for door in doors:
    name = door.Name or "Unnamed"
    area = loader.get_property_value(door, "Qto_DoorBaseQuantities", "Area")
    is_external = loader.get_property_value(door, "Pset_DoorCommon", "IsExternal")
    print(f"Door: {name}")
    print(f"  Area: {area}")
    print(f"  Is External: {is_external}")
    
    if is_external:
        total_exterior_area += area if area is not None else 0.0

print(f"\nTotal exterior door area: {total_exterior_area}") 