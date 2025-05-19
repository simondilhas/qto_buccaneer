import ifcopenshell
from pathlib import Path

TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")

print(f"Attempting to read IFC file at: {TEST_IFC_PATH}")
try:
    ifc_file = ifcopenshell.open(TEST_IFC_PATH)
    print("Successfully opened IFC file!")
    print(f"File contains {len(ifc_file.by_type('IfcSpace'))} spaces")
except Exception as e:
    print(f"Error opening file: {e}") 