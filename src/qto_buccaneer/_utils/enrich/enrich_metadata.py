import pandas as pd
from pathlib import Path
import os
import shutil
import ifcopenshell
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer._utils._result_bundle import ResultBundle
from typing import Union, Dict, Any
from qto_buccaneer._utils._general_tool_utils import validate_config, validate_df
import logging

logger = logging.getLogger(__name__)

def enrich_metadata(
    enrichment_df: pd.DataFrame,
    metadata_json: Union[dict, ResultBundle],
    config: Dict[str, Any],
    ) -> ResultBundle:
    
    print(config)

    validate_config(config)

    TOOL_NAME = config['description']

    logger.info(f"Starting {TOOL_NAME}")

    if isinstance(metadata_json, ResultBundle):
        metadata_json = metadata_json.to_dict()
    else:
        metadata_json = metadata_json
    

    # 2. Extract required columns
    required_columns = config['config']['keys']['df']

    # 3. Validate DataFrame
    validate_df(enrichment_df, required_columns=required_columns, df_name="Enrichment DataFrame")

    # 4. Process DataFrame
    
    dict_with_enriched_metadata, summary_data, list_enriched_guids = (
        _process_enrich_metadata_logic(
            enrichment_df=enrichment_df, 
            metadata_json=metadata_json, 
            key_ifc=config['config']['keys']['ifc'], 
            key_df=config['config']['keys']['df'], 
            pset_name=config['config']['pset_name'])
    )

    # 5. Package results
    result_bundle = ResultBundle(
        dataframe=enrichmnt_df,

        json=summary_data,
    )

    # 6. Return results
    logger.info(f"Finished {TOOL_NAME}")
    return result_bundle

def _process_enrich_metadata_logic(
    enrichment_df: pd.DataFrame,
    metadata_json: dict,
    key_ifc: str,
    key_df: str,
    pset_name: str,
    ) -> Tuple[dict, dict, list]:
    
    print("enrich_metadata_logic")


enrichment_df = pd.read_excel(
    "testdata/Raumprogramm Seefeld AKTUELL.xlsx",
    sheet_name="Raumprogramm Rohdaten",
    header=0,
    index_col=0,
)

print


#enrich_metadata(
#    enrichment_df=enrichment_df,
#    metadata_json=metadata_json,
#    config=config,
#)