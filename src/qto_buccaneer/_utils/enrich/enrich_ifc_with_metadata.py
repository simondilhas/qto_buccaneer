import pandas as pd
from pathlib import Path
import os
import shutil
import ifcopenshell
from qto_buccaneer.utils.ifc_loader import IfcLoader
from typing import Union, List, Optional, Tuple, Dict, Any

from typing import Union, Dict, Any, Optional
import pandas as pd
from pathlib import Path
import logging
from qto_buccaneer._utils._result_bundle import IFCResultBundle, BaseResultBundle
from qto_buccaneer._utils._general_tool_utils import unpack_dataframe, validate_df, validate_config


logger = logging.getLogger(__name__)

def enrich_ifc_with_metadata_internal(
    enrichment_df: pd.DataFrame,
    ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
    config: Dict[str, Any],
    ) -> IFCResultBundle:
    """
    Template for a data processing tool.

    Pattern:
    1. Unpack the DataFrame (handles both DataFrame or BaseResultBundle).
    2. Extract required configuration.
    3. Validate the DataFrame using `validate_df`.
    4. Process the DataFrame.
    5. Package and return results as a BaseResultBundle.

    Args:
        enrichment_df: Input data as DataFrame.
        ifc_file: Path to IFC file, IfcLoader instance, or ifcopenshell model.
        config: Configuration dictionary.

    Returns:
        IFCResultBundle with processed data and summary.
    """
    print(config)

    validate_config(config)

    TOOL_NAME = config['description']

    logger.info(f"Starting {TOOL_NAME}")

    # 1. Unpack ifc_file
    if isinstance(ifc_file, (str, ifcopenshell.file)):
        loader = IfcLoader(ifc_file)
    else:
        loader = ifc_file
    

    # 2. Extract required columns
    required_columns = config['config']['keys']['df']

    # 3. Validate DataFrame
    validate_df(enrichment_df, required_columns=required_columns, df_name="Enrichment DataFrame")

    # 4. Process DataFrame
    
    ifc, summary_data = _process_enrich_ifc_with_df_logic(
        ifc_file=loader, 
        df_for_ifc_enrichment=enrichment_df, 
        key_ifc=config['config']['keys']['ifc'], 
        key_df=config['config']['keys']['df'], 
        pset_name=config['config']['pset_name'])

    # 5. Package results
    result_bundle = IFCResultBundle(
        dataframe=enrichment_df,
        ifc_model=ifc,
        json=summary_data,
    )

    # 6. Return results
    logger.info(f"Finished {TOOL_NAME}")
    return result_bundle

def enrich_metadata_json(
    enrichment_df: pd.DataFrame,
    ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
    config: Dict[str, Any],
    ) -> BaseResultBundle:
    pass

def _process_enrich_ifc_with_df_logic(
                       ifc_file: Union[str, IfcLoader, 'ifcopenshell.file'],
                       df_for_ifc_enrichment: pd.DataFrame,
                       key_ifc: str = "LongName",
                       key_df: str = "LongName",
                       pset_name: str = "Pset_Enrichment",
                       ) -> Tuple['ifcopenshell.file', Dict[str, Any]]:
    """
    Enrich IFC elements with data from a DataFrame.

    Args:
        ifc_file: Either a file path, IfcLoader instance, or ifcopenshell model
        df_for_ifc_enrichment: DataFrame containing enrichment data
        key_ifc: Attribute name to match IFC elements (e.g. "LongName", "GlobalId")
        key_df: Column name in DataFrame to match against
        pset_name: Name for the property set storing enriched data

    Returns:
        Tuple containing:
        - ifcopenshell.file: The enriched IFC model
        - Dict[str, Any]: Summary data about the enrichment process
    """
    # Create loader if needed
    if isinstance(ifc_file, (str, ifcopenshell.file)):
        loader = IfcLoader(ifc_file)
    else:
        loader = ifc_file

    # Initialize summary data
    summary_data = {
        "total_elements": 0,
        "enriched_elements": 0,
        "missing_mappings": [],
        "errors": []
    }

    # If GlobalId is not in the DataFrame, create the mapping
    if 'GlobalId' not in df_for_ifc_enrichment.columns:
        logger.info(f"Creating GlobalId mapping using {key_ifc}")
        # Get space information from IFC
        df_space_info = loader.get_space_information()
        
        # Check if the key column exists in the space information
        if key_ifc not in df_space_info.columns:
            available_columns = list(df_space_info.columns)
            error_msg = (
                f"Key column '{key_ifc}' not found in space information. "
                f"Available columns: {', '.join(available_columns)}\n"
                f"Please check your configuration. Common alternatives are: 'LongName', 'Name', 'GlobalId'"
            )
            logger.error(error_msg)
            summary_data["errors"].append(error_msg)
            return loader.model, summary_data
        
        # Create mapping dictionary from IFC model to GlobalId
        ifc_to_globalid = dict(zip(df_space_info[key_ifc], df_space_info['GlobalId']))
        
        # Add GlobalId to enrichment DataFrame
        df_for_ifc_enrichment = df_for_ifc_enrichment.copy()
        
        # Check if the DataFrame column exists
        if key_df not in df_for_ifc_enrichment.columns:
            error_msg = f"Column '{key_df}' not found in enrichment DataFrame. Available columns: {', '.join(df_for_ifc_enrichment.columns)}"
            logger.error(error_msg)
            summary_data["errors"].append(error_msg)
            return loader.model, summary_data
        
        # Create a reverse mapping from GlobalId to IFC model value
        globalid_to_ifc = dict(zip(df_space_info['GlobalId'], df_space_info[key_ifc]))
        
        # Create a mapping from DataFrame values to IFC model values
        df_to_ifc = {}
        
        # Count unique values for each key
        unique_counts = df_for_ifc_enrichment[key_df].value_counts().to_dict()
        
        for guid, ifc_value in globalid_to_ifc.items():
            # Find matching DataFrame value
            matching_df_rows = df_for_ifc_enrichment[df_for_ifc_enrichment[key_df] == ifc_value]
            if not matching_df_rows.empty:
                if ifc_value not in df_to_ifc:
                    df_to_ifc[ifc_value] = []
                df_to_ifc[ifc_value].append(guid)
        
        # Map the values from the DataFrame to GlobalIds
        df_for_ifc_enrichment['GlobalIds'] = df_for_ifc_enrichment[key_df].map(lambda x: df_to_ifc.get(x, []))
        
        # Add the count of unique values to the DataFrame
        df_for_ifc_enrichment['Anzahl_Identische_Raeume'] = df_for_ifc_enrichment[key_df].map(unique_counts)
        
        # Check for missing mappings
        missing_keys = df_for_ifc_enrichment[df_for_ifc_enrichment['GlobalIds'].apply(len) == 0][key_df].unique()
        if len(missing_keys) > 0:
            summary_data["missing_mappings"] = list(missing_keys)
            logger.warning(f"Could not find GlobalIds for these {key_df}s: {missing_keys}")

    # Create a copy of the model for modification
    new_ifc = ifcopenshell.file()
    new_ifc.header = loader.model.header
    for entity in loader.model:
        new_ifc.add(entity)
    
    # Process each element in our enrichment data
    summary_data["total_elements"] = len(df_for_ifc_enrichment)
    
    for _, element_data in df_for_ifc_enrichment.iterrows():
        try:
            # Get all GlobalIds for this element
            global_ids = element_data['GlobalIds'] if 'GlobalIds' in element_data else [element_data['GlobalId']]
            
            for guid in global_ids:
                element = new_ifc.by_guid(guid)
                
                if element is not None:
                    summary_data["enriched_elements"] += 1
                    
                    # Create or update property set
                    existing_pset = None
                    for rel in element.IsDefinedBy:
                        if hasattr(rel, 'RelatingPropertyDefinition'):
                            pdef = rel.RelatingPropertyDefinition
                            if pdef.is_a('IfcPropertySet') and pdef.Name == pset_name:
                                existing_pset = pdef
                                break
                    
                    if not existing_pset:
                        existing_pset = new_ifc.create_entity(
                            "IfcPropertySet",
                            GlobalId=ifcopenshell.guid.new(),
                            Name=pset_name,
                            Description="Enriched properties",
                            HasProperties=[]
                        )
                        new_ifc.create_entity(
                            "IfcRelDefinesByProperties",
                            GlobalId=ifcopenshell.guid.new(),
                            RelatedObjects=[element],
                            RelatingPropertyDefinition=existing_pset
                        )
                    
                    # Add new properties
                    columns_to_add = [col for col in df_for_ifc_enrichment.columns 
                                    if col not in ['GlobalId', 'GlobalIds', key_df]]
                    
                    for column in columns_to_add:
                        value = element_data[column]
                        if pd.notna(value):
                            # Create a more descriptive property name for the count
                            prop_name = column
                            if column == 'Anzahl_Identische_Raeume':
                                prop_name = f"Anzahl_Identische_{key_df}"
                            
                            if isinstance(value, bool):
                                ifc_value = new_ifc.create_entity("IfcBoolean", value)
                            elif isinstance(value, str):
                                # Store string directly without escape sequences
                                ifc_value = new_ifc.create_entity("IfcText", value)
                            elif isinstance(value, (int, float)):
                                ifc_value = new_ifc.create_entity("IfcReal", float(value))
                            else:
                                ifc_value = new_ifc.create_entity("IfcText", str(value))
                            
                            prop = new_ifc.create_entity(
                                "IfcPropertySingleValue",
                                Name=prop_name,
                                NominalValue=ifc_value
                            )
                            existing_pset.HasProperties = list(existing_pset.HasProperties) + [prop]
                else:
                    summary_data["errors"].append(f"Element with GlobalId {guid} not found")
        except Exception as e:
            summary_data["errors"].append(f"Error processing element {element_data.get('GlobalId', 'unknown')}: {str(e)}")
    
    return new_ifc, summary_data

#enrichment_df = pd.read_excel(
#    "src/qto_buccaneer/_utils/enrich/testdata/Raumprogramm Seefeld AKTUELL.xlsx",
#    sheet_name="Raumprogramm Rohdaten",
#    header=0,
#    index_col=0,
#)
#
#print(enrichment_df)
#
#enrich_ifc_with_metadata(
#    enrichment_df=enrichment_df,
#    ifc_file="src/qto_buccaneer/_utils/enrich/testdata/001_test_building_abstractBIM.ifc",
#    config=config,
#)