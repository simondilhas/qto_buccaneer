import pandas as pd
import ifcopenshell
import os
import shutil
from pathlib import Path
from typing import Union, List
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.qto_buccaneer.utils.ifc_loader import IfcLoader
from src.qto_buccaneer.preprocess_ifc import add_spatial_data_to_ifc
from src.qto_buccaneer.utils.config import load_config


input_file = "examples/Mustermodell V1_abstractBIM_sp_enriched.ifc"
ifc_loader = IfcLoader(input_file)

config_path = "src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml"
config = load_config(config_path)

# TODO


