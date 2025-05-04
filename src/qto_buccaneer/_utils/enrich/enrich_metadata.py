import pandas as pd
import ifcopenshell
from typing import Union, Dict, Any, Optional, List
import pandas as pd
from pathlib import Path
import logging
from qto_buccaneer._utils._result_bundle import ResultBundle
from qto_buccaneer._utils._general_tool_utils import unpack_dataframe, validate_df, validate_config


logger = logging.getLogger(__name__)

class MetadataUpdateTracker:
    def __init__(self):
        self.updates = {
            'matched_guids': set(),  # GUIDs that match filter criteria
            'property_updates': {},  # {guid: {property_name: new_value}}
            'pset_updates': {},      # {guid: {pset_name: {property: new_value}}}
            'changes': [],           # For audit trail
            'warnings': []           # Track warnings for missing GUIDs
        }
    
    def add_update(self, guid: str, property_path: str, old_value: Any, new_value: Any):
        """Track a single property update with proper Pset handling"""
        change = {
            'guid': guid,
            'property_path': property_path,
            'old_value': old_value,
            'new_value': new_value,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        if '.' in property_path:
            pset_name, property_name = property_path.split('.')
            if guid not in self.pset_updates:
                self.pset_updates[guid] = {}
            if pset_name not in self.pset_updates[guid]:
                self.pset_updates[guid][pset_name] = {}
            self.pset_updates[guid][pset_name][property_name] = new_value
            change['type'] = 'pset'
            change['pset_name'] = pset_name
            change['property_name'] = property_name
        else:
            if guid not in self.property_updates:
                self.property_updates[guid] = {}
            self.property_updates[guid][property_path] = new_value
            change['type'] = 'property'
            
        self.changes.append(change)
        
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append({
            'message': message,
            'timestamp': pd.Timestamp.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all updates"""
        return {
            'total_updates': len(self.changes),
            'updated_guids': list(self.updates['matched_guids']),
            'failed_guids': [w['message'] for w in self.warnings if 'GUID' in w['message']],
            'property_updates': sum(1 for c in self.changes if c['type'] == 'property'),
            'pset_updates': sum(1 for c in self.changes if c['type'] == 'pset'),
            'warnings': self.warnings
        }

def enrich_ifc_with_metadata(
    enrichment_data: pd.DataFrame,
    metadata_data: Union[pd.DataFrame, ResultBundle],
    config: Dict[str, Any],
) -> ResultBundle:
    """
    Template for a data processing tool.

    Pattern:
    1. Unpack the DataFrame (handles both DataFrame and ResultBundle).
    2. Extract required configuration.
    3. Validate the DataFrame using `validate_df`.
    4. Process the DataFrame.
    5. Package and return results as a ResultBundle.

    Args:
        enrichment_data: Input data as DataFrame or ResultBundle.
        metadata_data: Metadata as DataFrame or ResultBundle.
        config: Configuration dictionary containing:
            - tool_name: Name of the tool
            - ifc_model: The IFC model to update
            - metadata: The metadata dictionary to update
            - actual_columns: Required columns for validation

    Returns:
        ResultBundle with:
            - ifc_model: Updated IFC model
            - json: Summary of updates
    """
    validate_config(config)

    TOOL_NAME = config['tool_name']
    logger.info(f"Starting {TOOL_NAME}")

    # 1. Unpack DataFrames
    df = unpack_dataframe(enrichment_data)
    metadata = unpack_dataframe(metadata_data)

    # 2. Extract required columns
    required_columns = config['actual_columns']

    # 3. Validate DataFrame
    validation = validate_df(df, required_columns=required_columns, df_name="Enrichment DataFrame")
    if not validation['is_valid']:
        raise ValueError(f"Validation failed: {validation['errors']}")

    # 4. Process DataFrame
    updated_ifc_model, summary_data = _process_enrich_ifc_with_metadata_logic(
        df=df,
        metadata=metadata,
        ifc_model=config['ifc_model'],
        tool_name=TOOL_NAME
    )

    # 5. Package results
    result_bundle = ResultBundle(
        ifc_model=updated_ifc_model,
        json=summary_data
    )

    logger.info(f"Finished {TOOL_NAME}")
    return result_bundle

def _process_enrich_ifc_with_metadata_logic(
    df: pd.DataFrame,
    metadata: Dict[str, Any],
    ifc_model: Any,
    tool_name: str
) -> tuple[Any, Dict[str, Any]]:
    """Core data processing logic for the tool
    
    Args:
        df: Enrichment DataFrame with updates
        metadata: Metadata dictionary to update
        ifc_model: IFC model to update
        tool_name: Name of the tool for logging
        
    Returns:
        tuple[Any, Dict[str, Any]]: Updated IFC model and summary data
    """
    try:
        # Initialize update tracker
        update_tracker = MetadataUpdateTracker()
        
        # Process each row in the enrichment data
        for _, row in df.iterrows():
            guid = row['guid']
            update_tracker.updates['matched_guids'].add(guid)
            
            try:
                # Get IFC element
                ifc_element = ifc_model.by_guid(guid)
                if not ifc_element:
                    update_tracker.add_warning(f"GUID {guid} not found in IFC model")
                    continue
                
                # Find element in metadata by GlobalId
                element_id = None
                for id, element in metadata['elements'].items():
                    if element.get('GlobalId') == guid:
                        element_id = id
                        break
                
                if not element_id:
                    update_tracker.add_warning(f"GUID {guid} not found in metadata")
                    continue
                
                # Process each column (except guid)
                for column in df.columns:
                    if column == 'guid':
                        continue
                        
                    new_value = row[column]
                    old_value = metadata['elements'][element_id].get(column)
                    
                    # Skip if value hasn't changed
                    if old_value == new_value:
                        continue
                    
                    # Handle Pset.property format
                    if '.' in column:
                        pset_name, property_name = column.split('.')
                        # Update metadata
                        metadata['elements'][element_id][column] = new_value
                        # Update IFC
                        _update_pset_property(ifc_element, pset_name, property_name, new_value)
                        # Track update
                        update_tracker.add_update(guid, column, old_value, new_value)
                    else:
                        # Direct property update
                        metadata['elements'][element_id][column] = new_value
                        if hasattr(ifc_element, column):
                            setattr(ifc_element, column, new_value)
                            # Track update
                            update_tracker.add_update(guid, column, old_value, new_value)
                    
            except Exception as e:
                update_tracker.add_warning(f"Failed to process GUID {guid}: {str(e)}")
                continue
        
        # Prepare summary data
        summary_data = {
            tool_name: {
                "status": "Success",
                "summary": update_tracker.get_summary()
            }
        }
        
        return ifc_model, summary_data
        
    except Exception as e:
        logger.exception(f"{tool_name}: Processing failed")
        raise RuntimeError(f"Processing failed in {tool_name}: {str(e)}")

def _update_pset_property(ifc_element, pset_name, property_name, new_value):
    """Update a property in a property set"""
    # Get or create property set
    pset = _get_or_create_pset(ifc_element, pset_name)
    
    # Try to find existing property
    for prop in pset.HasProperties:
        if prop.Name == property_name:
            # Update existing property
            prop.NominalValue = new_value
            return
    
    # Create new property if not found
    ifcopenshell.api.run(
        "pset.edit_pset",
        pset.model,
        pset=pset,
        properties={property_name: new_value}
    )

def _get_or_create_pset(ifc_element, pset_name):
    """Get existing property set or create new one"""
    # Try to find existing property set
    for rel in ifc_element.IsDefinedBy:
        if rel.RelatingPropertyDefinition.Name == pset_name:
            return rel.RelatingPropertyDefinition
    
    # Create new property set if not found
    return ifcopenshell.api.run(
        "pset.add_pset",
        ifc_element.model,
        product=ifc_element,
        name=pset_name
    )
    
