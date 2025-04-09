import pytest
import yaml
import os
import sys

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator

# Constants for test data
TEST_IFC_PATH = "test_model_1.ifc"
TEST_DATA_PATH = "tests/test_data.yaml"

