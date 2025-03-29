import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ifc_loader import IfcLoader
from qto_calculator import QtoCalculator

# Load IFC
loader = IfcLoader("tests/Mustermodell V1_abstractBIM.ifc")
qto = QtoCalculator(loader)



gfa_area_total = qto.calculate_gross_floor_area()
print(f"Area without substraction: {gfa_area_total}")

gfa_area_with_substraction = qto.calculate_gross_floor_area(subtract_filter={"LongName" : "LUF"})
print(f"Area with substraction: {gfa_area_with_substraction}")

volume = qto.calculate_gross_floor_volume()
print(f"Building Volume: {volume}")

volume_with_substraction = qto.calculate_gross_floor_volume(subtract_filter={"LongName" : "LUF"})
print(f"Building Volume: {volume_with_substraction}")

external_coverings = qto.calculate_exterior_coverings_area({"PredefinedType": "CLADDING"})
print(f"External Coverings: {external_coverings} m2")

external_coverings = qto.calculate_exterior_coverings_area({"Pset_CoveringCommon.IsExternal": True})
print(f"External Coverings: {external_coverings} m2")

#coverings = loader.get_elements({"PredefinedType": "CLADDING"}, ifc_entity="IfcCovering")
#
#for c in coverings:
#    psets = loader.get_property_sets(c)
#    print(f"\n{c.GlobalId} Properties:")
#    for pset_name, props in psets.items():
#        print(f"  {pset_name}")
#        for key, val in props.items():
#            print(f"    {key}: {val}")

windows_exterior = qto.calculate_exterior_windows_area()
print(f"Exterior Windows: {windows_exterior}")

windows_interior = qto.calculate_interior_windows_area()
print(f"Interior Windows: {windows_interior}")

doors_exterior = qto.calculate_exterior_doors_area()
print(f"Exterior Doors: {doors_exterior}")

doors_interior = qto.calculate_interior_doors_area()
print(f"Interior Doors: {doors_interior}")