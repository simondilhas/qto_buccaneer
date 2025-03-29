import sys
import os
import pytest
import ifcopenshell

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ifc_loader import IfcLoader

gfa_elements = IfcLoader("tests/Mustermodell V2_abstractBIM.ifc").get_gfa_elements()

print(gfa_elements)