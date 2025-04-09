from pathlib import Path
import ifcopenshell
from qto_buccaneer.utils.ifc_loader import IfcLoader

# Get the IFC file path
TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")

# Load the file
loader = IfcLoader(TEST_IFC_PATH)

# Get wall information
print("\nWall Information:")
print("----------------")
walls = loader.model.by_type("IfcWallStandardCase")
total_interior_non_loadbearing_area = 0.0

for wall in walls:
    name = wall.Name or "Unnamed"
    area = loader.get_property_value(wall, "Qto_WallBaseQuantities", "NetSideArea")
    width = loader.get_property_value(wall, "Qto_WallBaseQuantities", "Width")
    is_external = loader.get_property_value(wall, "Pset_WallCommon", "IsExternal")
    
    print(f"Wall: {name}")
    print(f"  Area: {area}")
    print(f"  Width: {width}")
    print(f"  Is External: {is_external}")
    
    if not is_external and width is not None and width <= 0.15 and area is not None:
        total_interior_non_loadbearing_area += area

print(f"\nTotal interior non-load bearing wall area: {total_interior_non_loadbearing_area}") 