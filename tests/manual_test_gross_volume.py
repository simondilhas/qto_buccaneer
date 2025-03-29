import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ifc_loader import IfcLoader
from qto_calculator import QtoCalculator

# Load IFC
loader = IfcLoader("tests/Mustermodell V1_abstractBIM.ifc")
qto = QtoCalculator(loader)

gfa_area = qto.calculate_gross_floor_volume()
print(gfa_area)