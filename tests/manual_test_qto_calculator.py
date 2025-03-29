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