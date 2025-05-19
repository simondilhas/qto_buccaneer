import ifcopenshell
from pathlib import Path

TEST_DIR = Path(__file__).parent.absolute()
TEST_IFC_PATH = str(TEST_DIR / "test_model_1.ifc")

def main():
    # Open the IFC file
    ifc_file = ifcopenshell.open(TEST_IFC_PATH)
    
    # Get all spaces
    spaces = ifc_file.by_type("IfcSpace")
    print(f"\nFound {len(spaces)} spaces:")
    for space in spaces:
        print(f"\nSpace: {space.Name}")
        print(f"GlobalId: {space.GlobalId}")
        print(f"LongName: {space.LongName if hasattr(space, 'LongName') else 'No LongName'}")
        
        # Get windows associated with this space through space boundaries
        windows = []
        for rel in ifc_file.get_inverse(space):
            if rel.is_a("IfcRelSpaceBoundary"):
                if rel.RelatedBuildingElement is not None:
                    for element in rel.RelatedBuildingElement:
                        if element.is_a("IfcWindow"):
                            windows.append(element)
        
        # Also check for windows through containment relationships
        for rel in ifc_file.get_inverse(space):
            if rel.is_a("IfcRelContainedInSpatialStructure"):
                for element in rel.RelatedElements:
                    if element.is_a("IfcWindow"):
                        windows.append(element)
        
        print(f"Associated windows: {len(windows)}")
        for window in windows:
            print(f"  - Window: {window.Name}")
            print(f"    GlobalId: {window.GlobalId}")
            if hasattr(window, 'OverallHeight') and hasattr(window, 'OverallWidth'):
                area = window.OverallHeight * window.OverallWidth
                print(f"    Area: {area}")
            else:
                # Try to get area from properties
                for pset in window.IsDefinedBy:
                    if hasattr(pset, 'RelatingPropertyDefinition'):
                        if pset.RelatingPropertyDefinition.is_a('IfcPropertySet'):
                            for prop in pset.RelatingPropertyDefinition.HasProperties:
                                if prop.Name == 'Area':
                                    print(f"    Area: {prop.NominalValue.wrappedValue}")
                                    break

if __name__ == "__main__":
    main() 