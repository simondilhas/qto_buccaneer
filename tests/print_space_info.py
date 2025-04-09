from pathlib import Path
import ifcopenshell
from qto_buccaneer.utils.ifc_loader import IfcLoader

# Get the IFC file path
TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")

# Load the file
loader = IfcLoader(TEST_IFC_PATH)

# Get space information
print("\nSpace Information:")
print("-----------------")
spaces = loader.model.by_type("IfcSpace")
for space in spaces:
    name = space.Name or space.LongName or "Unnamed"
    area = loader.get_property_value(space, "Qto_SpaceBaseQuantities", "NetFloorArea")
    print(f"Space: {name}, Area: {area}") 