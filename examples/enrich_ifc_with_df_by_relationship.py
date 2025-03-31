import pandas as pd
import ifcopenshell
import os
import shutil
from pathlib import Path
from typing import Union, List
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.qto_buccaneer.utils.ifc_loader import IfcLoader
from src.qto_buccaneer.enriche import enrich_ifc, enrich_df

ifc_loader = IfcLoader("examples/Mustermodell V1_abstractBIM.ifc")

#I have a relationship property set showing to which space a element (wall, window, door, covering.) belongs to.
#I want to enrich the ifc file with data. based on this relationship.
# Same there is a direction property, or just a key, value pair
# For this I search for the best way to manage the data for enrichment, I have something similar like in the metrics_config_abstractBIM.yaml or a excel file in mind.
#Help me to do this, first concepts