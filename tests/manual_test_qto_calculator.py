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

external_coverings = qto.calculate_coverings_exterior_area()
print(f"External Coverings: {external_coverings} m2")

internal_coverings = qto.calculate_coverings_interior_area()
print(f"Internal Coverings: {internal_coverings} m2")

windows_exterior = qto.calculate_windows_exterior_area()
print(f"Exterior Windows: {windows_exterior}")

windows_interior = qto.calculate_windows_interior_area()
print(f"Interior Windows: {windows_interior}")

doors_exterior = qto.calculate_doors_exterior_area()
print(f"Exterior Doors: {doors_exterior}")

doors_interior = qto.calculate_doors_interior_area()
print(f"Interior Doors: {doors_interior}")

walls_exterior = qto.calculate_walls_exterior_net_side_area()
print(f"Exterior Walls: {walls_exterior}")

walls_interior = qto.calculate_walls_interior_net_side_area()
print(f"Interior Walls: {walls_interior}")

space_floor_area = qto.calculate_space_interior_floor_area()
print(f"Space Floor Area: {space_floor_area}")

space_volume = qto.calculate_space_interior_volume()
print(f"Space Volume: {space_volume}")

space_exterior_area = qto.calculate_space_exterior_area()
print(f"Space Exterior Area: {space_exterior_area}")

slab_exterior_area = qto.calculate_slab_balcony_area()
print(f"Slab Exterior Area: {slab_exterior_area}")

slab_interior_area = qto.calculate_slab_interior_area()
print(f"Slab Interior Area: {slab_interior_area}")

roof_area = qto.calculate_roof_area()
print(f"Roof Area: {roof_area}")

base_slab_area = qto.calculate_base_slab_area()
print(f"Base Slab Area: {base_slab_area}")




