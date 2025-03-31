import pandas as pd
import ifcopenshell
import os
import shutil
from pathlib import Path
from typing import Union, List
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.qto_buccaneer.utils.ifc_loader import IfcLoader
from src.qto_buccaneer.enriche import enrich_ifc_with_df, enrich_df

file = "src/qto_buccaneer/configs/enrichment_space_table.xlsx"
df_enrichment = pd.read_excel(file)#
print(df_enrichment)#
df_enrichment_columns = df_enrichment.columns

ifc_loader = IfcLoader("examples/Mustermodell V1_abstractBIM.ifc")

# Get space information
df_space_info = ifc_loader.get_space_information()
print("Space Information DataFrame:")
print(df_space_info)

# Create a mapping dictionary from LongName to GlobalId
longname_to_globalid = dict(zip(df_space_info['LongName'], df_space_info['GlobalId']))

# Add GlobalId to enrichment DataFrame by mapping LongNames
df_for_ifc_enrichment = df_enrichment.copy()
df_for_ifc_enrichment['GlobalId'] = df_for_ifc_enrichment['LongName'].map(longname_to_globalid)

print("\nFinal DataFrame for IFC enrichment:")
print(df_for_ifc_enrichment)

# Verify we have all necessary data
print("\nRows with missing GlobalIds:")
print(df_for_ifc_enrichment[df_for_ifc_enrichment['GlobalId'].isna()])

enriched_ifc_path = enrich_ifc_with_df(ifc_file="examples/Mustermodell V1_abstractBIM.ifc", 
                               df_for_ifc_enrichment=df_for_ifc_enrichment,
                               key="LongName")

print(enriched_ifc_path)