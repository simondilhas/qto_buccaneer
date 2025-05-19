import pandas as pd
from pathlib import Path
import os
import shutil
import ifcopenshell
from .utils.ifc_loader import IfcLoader
from ._utils._result_bundle import BaseResultBundle
from typing import Union, List, Optional, Dict, Any, Tuple
import yaml
from pathlib import Path
import pandas as pd
import sys
import os
import ifcopenshell
from typing import Optional, Union
from qto_buccaneer._utils.enrich.enrich_ifc_with_metadata import enrich_ifc_with_metadata_internal
from qto_buccaneer._utils.enrich.enrich_ifc_with_spatial_data import enrich_ifc_with_spatial_data_internal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer._utils.enrich.enrich_ifc_with_metadata import enrich_ifc_with_metadata_internal
from qto_buccaneer._utils.enrich.enrich_ifc_with_spatial_data import enrich_ifc_with_spatial_data_internal


def enrich_df(df_model_data: pd.DataFrame, 
              df_enrichment_data: pd.DataFrame, 
              key: str) -> pd.DataFrame:
    """
    Enrich a DataFrame with data from another DataFrame on a given key. 
    The key is the column name that is used to merge the two DataFrames.

    Args:
        df_model_data: DataFrame with model data
        df_enrichment_data: DataFrame with enrichment data
        key: str, key LongName, Name, GlobalId, Description, Pset_SpaceCommon.IsExternal
    """
    return pd.merge(
        df_model_data,
        df_enrichment_data,
        on=key,
        how='left'
    )

def enrich_ifc_with_metadata(
    enrichment_df: pd.DataFrame,
    ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
    config: Dict[str, Any],
    ) -> BaseResultBundle:

    result = enrich_ifc_with_metadata_internal(
        enrichment_df=enrichment_df,
        ifc_file=ifc_file,
        config=config
    )   

    return result


def enrich_ifc_with_spatial_data(
    ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
    config: Dict[str, Any],
) -> BaseResultBundle:

    result = enrich_ifc_with_spatial_data_internal(
        ifc_file=ifc_file,
        config=config
    )

    return result
