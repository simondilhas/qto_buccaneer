import ifcopenshell
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import os
from pathlib import Path
import json
import numpy as np
import concurrent.futures

# Configure logging
logger = logging.getLogger(__name__)

def safe_instances_by_type(ifc_file, query):
    """
    Safe wrapper around ifc_file.instances_by_type().
    
    Accepts either:
    - an entity_instance (like an IfcWall object),
    - a string (like "IfcWall"),
    - or a class (like IfcWall class).

    Args:
        ifc_file: an opened ifcopenshell file.
        query: entity instance, class, or string.

    Returns:
        List of matching instances, or empty list if not found or invalid input.
    """
    import ifcopenshell

    try:
        if isinstance(query, ifcopenshell.entity_instance):
            # it's an object like IfcWall(...)
            return ifc_file.safe_instances_by_type(query.is_a())
        
        elif isinstance(query, str):
            # it's already a string like "IfcWall"
            return ifc_file.safe_instances_by_type(query)
        
        elif hasattr(query, "__name__"):
            # it's a class (like IfcWall)
            return ifc_file.safe_instances_by_type(query.__name__)
        
        else:
            raise TypeError(f"Unsupported query type: {type(query)}")

    except Exception as e:
        print(f"[safe_instances_by_type] Error handling query '{query}': {e}")
        return []




def _flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """
    Flatten a nested dictionary into a single-level dictionary using dot notation.
    
    This function recursively traverses a nested dictionary structure and creates
    flattened keys by concatenating parent keys with child keys using a separator.
    
    Args:
        d (Dict): The nested dictionary to flatten
        parent_key (str, optional): The parent key prefix. Defaults to empty string.
        sep (str, optional): The separator to use between keys. Defaults to '.'.
        
    Returns:
        Dict: A flattened dictionary with dot-notation keys
        
    Example:
        >>> nested = {'a': {'b': 1, 'c': {'d': 2}}}
        >>> _flatten_dict(nested)
        {'a.b': 1, 'a.c.d': 2}
    """
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, new_key, sep))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.update(_flatten_dict(item, f"{new_key}{sep}{i}", sep))
                else:
                    items[f"{new_key}{sep}{i}"] = item
        else:
            items[new_key] = v
    return items


def _extract_constructor_attributes(product: Any) -> Dict[str, Any]:
    """
    Extract all attributes from an IFC product.
    
    Args:
        product (Any): The IFC product entity to extract attributes from
        
    Returns:
        Dict[str, Any]: Dictionary of all attribute names and values
    """
    metadata = {}
    try:
        # Get all attributes that the product has
        for attr in dir(product):
            # Skip private attributes (starting with _), methods, and specific IFC references
            if (not attr.startswith('_') and 
                not callable(getattr(product, attr)) and
                attr not in [
                    'ObjectPlacement', 
                    'OwnerHistory', 
                    'Representation',
                    'RepresentationContexts',
                    'UnitsInContext',
                    'file',
                    'IsDefinedBy',
                    'HasAssociations',
                    'IsDecomposedBy',
                    'Decomposes'
                ]):
                value = getattr(product, attr, None)
                
                # Handle entity instances
                if hasattr(value, 'is_a'):  # This is an IFC entity
                    if hasattr(value, 'GlobalId'):
                        metadata[attr] = value.GlobalId
                    else:
                        metadata[attr] = str(value)
                # Handle lists of entities
                elif isinstance(value, (list, tuple)) and value and hasattr(value[0], 'is_a'):
                    metadata[attr] = [v.GlobalId if hasattr(v, 'GlobalId') else str(v) for v in value]
                # Handle other values
                else:
                    metadata[attr] = value
                
    except Exception as e:
        logger.warning(f"Failed to extract constructor attributes: {e}")
    
    return metadata

def _extract_property_value(prop: Any, pset_name: str) -> Tuple[str, Any]:
    """
    Extract a single property value from an IFC property.
    
    Args:
        prop (Any): The IFC property
        pset_name (str): Name of the property set
        
    Returns:
        Tuple[str, Any]: Property key and value
    """
    if not hasattr(prop, 'NominalValue'):
        return None, None
        
    try:
        # Get the raw value
        if hasattr(prop.NominalValue, 'wrappedValue'):
            value = prop.NominalValue.wrappedValue
        else:
            value = prop.NominalValue
            
        # Handle special cases
        if prop.Name == 'SpacesLongName' and pset_name == 'ePset_abstractBIM':
            return 'LongName', value
            
        # Format the property key
        key = f"{pset_name}.{prop.Name}"
        
        # Handle value types
        if isinstance(value, bool):
            return key, value
        elif isinstance(value, str):
            return key, value
        else:
            return key, str(value)
            
    except Exception as e:
        logger.warning(f"Error extracting property value: {e}")
        return None, None

def _extract_properties(product):
    metadata = {}
    
    # Check both IsDefinedBy and Defines relationships
    relationships = []
    if hasattr(product, 'IsDefinedBy'):
        relationships.extend(product.IsDefinedBy)
    if hasattr(product, 'Defines'):
        relationships.extend(product.Defines)
    
    for definition in relationships:
        try:
            if not hasattr(definition, 'RelatingPropertyDefinition'):
                continue
                
            prop_def = definition.RelatingPropertyDefinition
            logger.debug(f"Processing property definition of type: {prop_def.is_a()}")
            
            # Handle property sets
            if prop_def.is_a('IfcPropertySet'):
                logger.debug(f"Found property set: {prop_def.Name}")
                for prop in prop_def.HasProperties:
                    key, value = _extract_property_value(prop, prop_def.Name)
                    if key and value is not None:
                        metadata[key] = value
                        logger.debug(f"Added property: {key} = {value}")
                        
            # Handle quantities
            elif prop_def.is_a('IfcElementQuantity'):
                logger.debug(f"Found quantity set: {prop_def.Name}")
                for quantity in prop_def.Quantities:
                    key = f"{prop_def.Name}.{quantity.Name}"
                    if hasattr(quantity, 'LengthValue'):
                        metadata[key] = quantity.LengthValue
                        logger.debug(f"Added length quantity: {key} = {quantity.LengthValue}")
                    elif hasattr(quantity, 'AreaValue'):
                        metadata[key] = quantity.AreaValue
                        logger.debug(f"Added area quantity: {key} = {quantity.AreaValue}")
                    elif hasattr(quantity, 'VolumeValue'):
                        metadata[key] = quantity.VolumeValue
                        logger.debug(f"Added volume quantity: {key} = {quantity.VolumeValue}")
                    elif hasattr(quantity, 'CountValue'):
                        metadata[key] = quantity.CountValue
                        logger.debug(f"Added count quantity: {key} = {quantity.CountValue}")
                    elif hasattr(quantity, 'WeightValue'):
                        metadata[key] = quantity.WeightValue
                        logger.debug(f"Added weight quantity: {key} = {quantity.WeightValue}")
                    elif hasattr(quantity, 'TimeValue'):
                        metadata[key] = quantity.TimeValue
                        logger.debug(f"Added time quantity: {key} = {quantity.TimeValue}")
                    elif hasattr(quantity, 'NominalValue'):
                        metadata[key] = quantity.NominalValue
                        logger.debug(f"Added nominal quantity: {key} = {quantity.NominalValue}")
                        
        except Exception as e:
            logger.warning(f"Error processing property definition: {e}")
    
    return metadata

def _extract_materials(product: Any) -> Dict[str, Any]:
    """
    Extract material associations from an IFC product.
    
    Args:
        product (Any): The IFC product entity
        
    Returns:
        Dict[str, Any]: Dictionary containing material information
    """
    if not hasattr(product, 'HasAssociations'):
        return {}
        
    materials = []
    for association in product.HasAssociations:
        if not association.is_a('IfcRelAssociatesMaterial'):
            continue
            
        material = association.RelatingMaterial
        if material.is_a('IfcMaterial'):
            materials.append(material.Name)
        elif material.is_a('IfcMaterialList'):
            materials.extend(mat.Name for mat in material.Materials)
    
    return {"Materials": materials} if materials else {}

def _extract_metadata(product: Any) -> Dict[str, Any]:
    """
    Extract all metadata from an IFC product entity.
    
    Args:
        product (Any): The IFC product entity
        
    Returns:
        Dict[str, Any]: Dictionary containing all extracted metadata
    """
    # Extract different types of metadata
    attributes = _extract_constructor_attributes(product)
    properties = _extract_properties(product)
    materials = _extract_materials(product)
    
    # Combine all metadata
    metadata = {}
    metadata.update(attributes)
    metadata.update(properties)
    metadata.update(materials)
    
    return _flatten_dict(metadata)


def extract_metadata(ifc_file_path, output_formats=["json", "json_file", "dataframe"], output_dir=None, project_name=None):
    """
    Extracts IFC metadata and saves it to the specified output formats.
    
    Args:
        ifc_file_path: Path to the IFC file
        output_formats: List of desired output formats. Can include "json", "json_file", "dataframe"
        output_dir: Directory to save output files (required if json_file is in output_formats)
        project_name: Name of the project (used for output filenames)
        
    Returns:
        Tuple containing only the requested outputs in order: (dataframe, json_data, json_path)
        Only returns the values that were requested in output_formats
    """
    if "json_file" in output_formats and not output_dir:
        raise ValueError("output_dir must be specified when json_file is requested")
        
    if not project_name:
        project_name = Path(ifc_file_path).stem

    # Create output directory if needed
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Extract metadata
    elements_data = extract_ifc_metadata(ifc_file_path)

    # Prepare return values
    return_values = []

    # Create elements dictionary for JSON
    elements_dict = {str(elem["id"]): elem for elem in elements_data}
    json_data = {"elements": elements_dict}

    # Handle requested formats in order
    if "dataframe" in output_formats:
        # Convert to DataFrame only if requested
        df = pd.DataFrame(elements_data)
        return_values.append(df)
    
    if "json" in output_formats:
        return_values.append(json_data)
    
    if "json_file" in output_formats:
        json_path = output_dir / f"{project_name}_metadata.json"
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Metadata saved to {json_path}")
        return_values.append(str(json_path))

    # Return only the requested values
    return tuple(return_values)


def _build_element_id_mapping(ifc_file):
    """Build a mapping of GlobalId to sequential IDs for all elements."""
    globalid_to_id = {}
    all_elements = []

    # Get project and products
    project = ifc_file.by_type("IfcProject")[0]
    all_elements.append(project)

    for el in ifc_file.by_type("IfcProduct"):
        if not el.is_a("IfcOpeningElement"):  # Skip openings
            all_elements.append(el)

    # Assign sequential IDs
    for idx, el in enumerate(all_elements, start=1):
        globalid_to_id[el.GlobalId] = idx

    return globalid_to_id, all_elements

def _build_parent_child_mapping(ifc_file, project, globalid_to_id):
    """Build a mapping of child GlobalIds to their parent GlobalIds."""
    child_to_parent = {}

    # Project is root, sites point to it
    for site in ifc_file.by_type("IfcSite"):
        child_to_parent[site.GlobalId] = project.GlobalId

    # Handle aggregation relationships
    for rel in ifc_file.by_type("IfcRelAggregates"):
        if rel.RelatedObjects:
            parent = rel.RelatingObject
            for child in rel.RelatedObjects:
                child_to_parent[child.GlobalId] = parent.GlobalId

    # Handle spatial containment relationships
    for rel in ifc_file.by_type("IfcRelContainedInSpatialStructure"):
        if rel.RelatedElements:
            parent = rel.RelatingStructure
            for child in rel.RelatedElements:
                if child.GlobalId not in child_to_parent:  # Prefer aggregation relationships
                    child_to_parent[child.GlobalId] = parent.GlobalId

    return child_to_parent

def _extract_classification_data(ifc_file, all_elements, start_id):
    """Extract classification data and build ID mappings."""
    classification_id_map = {}
    elements_data = []
    counter = start_id

    for el in all_elements:
        if hasattr(el, "HasAssociations"):
            for association in el.HasAssociations:
                if association.is_a("IfcRelAssociatesClassification"):
                    classification = association.RelatingClassification
                    classification_key = str(classification)
                    if classification_key not in classification_id_map:
                        classification_data = _create_classification_record(classification, counter)
                        elements_data.append(classification_data)
                        classification_id_map[classification_key] = counter
                        counter += 1
                elif association.is_a("IfcRelAssociatesLibrary"):
                    library = association.RelatingLibrary
                    library_key = str(library)
                    if library_key not in classification_id_map:
                        library_data = _create_library_record(library, counter)
                        elements_data.append(library_data)
                        classification_id_map[library_key] = counter
                        counter += 1

    return classification_id_map, elements_data, counter

def _create_classification_record(classification, id):
    """Create a record for a classification entity."""
    if classification.is_a("IfcClassificationReference"):
        return {
            "id": id,
            "parent_id": None,
            "GlobalId": getattr(classification, "GlobalId", None),
            "IfcEntity": "IfcClassificationReference",
            "Name": str(getattr(classification, "Name", "")),
            "Description": str(getattr(classification, "Description", "")),
            "Location": str(getattr(classification, "Location", "")),
            "ItemReference": str(getattr(classification, "ItemReference", "")),
            "ReferencedSource": str(getattr(classification, "ReferencedSource", ""))
        }
    else:
        return {
            "id": id,
            "parent_id": None,
            "GlobalId": getattr(classification, "GlobalId", None),
            "IfcEntity": "IfcClassification",
            "Name": str(getattr(classification, "Name", "")),
            "Description": str(getattr(classification, "Description", "")),
            "Location": str(getattr(classification, "Location", "")),
            "Edition": str(getattr(classification, "Edition", "")),
            "EditionDate": str(getattr(classification, "EditionDate", ""))
        }

def _create_library_record(library, id):
    """Create a record for a library reference entity."""
    return {
        "id": id,
        "parent_id": None,
        "GlobalId": getattr(library, "GlobalId", None),
        "IfcEntity": "IfcLibraryReference",
        "Name": str(getattr(library, "Name", "")),
        "Description": str(getattr(library, "Description", "")),
        "Version": str(getattr(library, "Version", "")),
        "VersionDate": str(getattr(library, "VersionDate", ""))
    }

def _extract_system_data(ifc_file, all_elements, start_id):
    """Extract system data and build ID mappings."""
    system_id_map = {}
    elements_data = []
    counter = start_id

    for el in all_elements:
        if hasattr(el, "HasAssignments"):
            for assignment in el.HasAssignments:
                if assignment.is_a("IfcRelAssignsToGroup"):
                    group = assignment.RelatingGroup
                    if group.is_a("IfcSystem"):
                        system_key = str(group)
                        if system_key not in system_id_map:
                            system_data = _create_system_record(group, counter, "System")
                            elements_data.append(system_data)
                            system_id_map[system_key] = counter
                            counter += 1
                elif assignment.is_a("IfcRelAssignsToProcess"):
                    process = assignment.RelatingProcess
                    system_key = str(process)
                    if system_key not in system_id_map:
                        system_data = _create_system_record(process, counter, "Process")
                        elements_data.append(system_data)
                        system_id_map[system_key] = counter
                        counter += 1
                elif assignment.is_a("IfcRelAssignsToResource"):
                    resource = assignment.RelatingResource
                    system_key = str(resource)
                    if system_key not in system_id_map:
                        system_data = _create_system_record(resource, counter, "Resource")
                        elements_data.append(system_data)
                        system_id_map[system_key] = counter
                        counter += 1

    return system_id_map, elements_data

def _create_system_record(entity, id, type):
    """Create a record for a system entity."""
    return {
        "id": id,
        "parent_id": None,
        "GlobalId": getattr(entity, "GlobalId", None),
        "IfcEntity": entity.is_a(),
        "Name": str(getattr(entity, "Name", "")),
        "Description": str(getattr(entity, "Description", "")),
        "ObjectType": str(getattr(entity, "ObjectType", "")),
        "Type": type
    }

def _extract_quantities(el):
    """Extract quantities from an IFC element."""
    quantities = {}
    if hasattr(el, "IsDefinedBy"):
        for rel_def in el.IsDefinedBy:
            if rel_def.is_a("IfcRelDefinesByProperties"):
                prop_def = rel_def.RelatingPropertyDefinition
                if prop_def.is_a("IfcElementQuantity"):
                    qset_name = prop_def.Name
                    for quantity in prop_def.Quantities:
                        if hasattr(quantity, "LengthValue"):
                            quantities[f"{qset_name}.{quantity.Name}"] = quantity.LengthValue
                        elif hasattr(quantity, "AreaValue"):
                            quantities[f"{qset_name}.{quantity.Name}"] = quantity.AreaValue
                        elif hasattr(quantity, "VolumeValue"):
                            quantities[f"{qset_name}.{quantity.Name}"] = quantity.VolumeValue
                        elif hasattr(quantity, "CountValue"):
                            quantities[f"{qset_name}.{quantity.Name}"] = quantity.CountValue
                        elif hasattr(quantity, "WeightValue"):
                            quantities[f"{qset_name}.{quantity.Name}"] = quantity.WeightValue
                        elif hasattr(quantity, "TimeValue"):
                            quantities[f"{qset_name}.{quantity.Name}"] = quantity.TimeValue
    return quantities

def _create_element_record(el, idx, globalid_to_id, child_to_parent):
    """Create a record for an IFC element."""
    record = {
        "id": idx,
        "parent_id": None,
        "GlobalId": el.GlobalId,
        "IfcEntity": el.is_a(),
        "Classifications": [],
        "Systems": []
    }

    # Set parent ID if exists
    parent_gid = child_to_parent.get(el.GlobalId)
    if parent_gid:
        record["parent_id"] = globalid_to_id.get(parent_gid)

    # Extract attributes
    record.update(_extract_attributes(el))
    
    # Extract property sets
    record.update(_extract_property_sets(el))
    
    # Extract quantities
    record.update(_extract_quantities(el))
    
    return record

def _extract_attributes(el):
    """Extract attributes from an IFC element using defined IFC relationships."""
    attributes = {}
    
    # List of relationship attributes to exclude
    excluded_relationships = [
        # Basic IFC relationships
        'IsDeclaredBy',
        'IsNestedBy',
        'IsTypedBy',
        'BoundedBy',
        'HasAssignments',
        'HasAssociations',
        'IsDefinedBy',
        'IsDecomposedBy',
        'Decomposes',
        'Nests',
        'Declares',
        'HasContext',
        'HasCoverings',
        'ReferencedBy',
        'ReferencesElements',
        
        # IFC technical attributes
        'ObjectPlacement',
        'OwnerHistory',
        'Representation',
        'RepresentationContexts',
        'UnitsInContext',
        'file'
    ]
    
    # Dynamically extract all available attributes
    for attr in dir(el):
        # Skip private attributes, methods, and excluded relationships
        if (not attr.startswith('_') and 
            not callable(getattr(el, attr)) and
            attr not in excluded_relationships):
            value = getattr(el, attr, None)
            
            # Handle IFC entity instances
            if hasattr(value, 'is_a'):  # This is an IFC entity
                if hasattr(value, 'GlobalId'):
                    attributes[attr] = value.GlobalId
                else:
                    attributes[attr] = str(value)
            # Handle lists of entities
            elif isinstance(value, (list, tuple)) and value and hasattr(value[0], 'is_a'):
                # Only include non-empty lists
                if value:
                    attributes[attr] = [v.GlobalId if hasattr(v, 'GlobalId') else str(v) for v in value]
            # Handle other values
            elif value is not None:  # Only include non-None values
                attributes[attr] = value

    # Extract properties through IfcRelDefinesByProperties
    if hasattr(el, 'IsDefinedBy'):
        for rel in el.IsDefinedBy:
            if rel.is_a('IfcRelDefinesByProperties'):
                prop_set = rel.RelatingPropertyDefinition
                if prop_set.is_a('IfcPropertySet'):
                    # Only process if this element is actually in the RelatedObjects list
                    if not hasattr(rel, 'RelatedObjects') or el not in rel.RelatedObjects:
                        continue
                        
                    for prop in prop_set.HasProperties:
                        if hasattr(prop, 'NominalValue'):
                            prop_name = f"{prop_set.Name}.{prop.Name}"
                            try:
                                value = prop.NominalValue.wrappedValue
                                if value is not None:  # Only include non-None values
                                    attributes[prop_name] = value if isinstance(value, bool) else str(value)
                            except AttributeError:
                                value = str(prop.NominalValue)
                                if value != 'None':  # Only include non-None values
                                    attributes[prop_name] = value

    # Extract material information through IfcRelAssociatesMaterial
    if hasattr(el, 'HasAssociations'):
        materials = []
        for rel in el.HasAssociations:
            if rel.is_a('IfcRelAssociatesMaterial'):
                material = rel.RelatingMaterial
                if material.is_a('IfcMaterial'):
                    materials.append(material.Name)
                elif material.is_a('IfcMaterialList'):
                    materials.extend(mat.Name for mat in material.Materials)
        if materials:  # Only include if there are materials
            attributes['Materials'] = materials

    # Extract type information through IfcRelDefinesByType
    if hasattr(el, 'IsTypedBy'):
        for rel in el.IsTypedBy:
            if rel.is_a('IfcRelDefinesByType'):
                type_obj = rel.RelatingType
                if hasattr(type_obj, 'Name') and type_obj.Name:
                    attributes['TypeName'] = type_obj.Name
                if hasattr(type_obj, 'PredefinedType') and type_obj.PredefinedType:
                    attributes['PredefinedType'] = str(type_obj.PredefinedType)

    return attributes

def _is_relevant_property_set(pset_name, element_type):
    """Determine if a property set is relevant for a given element type."""
    # Map of element types to their relevant property sets
    element_to_psets = {
        'IfcCovering': ['Pset_CoveringCommon', 'Qto_CoveringBaseQuantities'],
        'IfcDoor': ['Pset_DoorCommon', 'Qto_DoorBaseQuantities'],
        'IfcWindow': ['Pset_WindowCommon', 'Qto_WindowBaseQuantities'],
        'IfcWall': ['Pset_WallCommon', 'Qto_WallBaseQuantities'],
        'IfcSlab': ['Pset_SlabCommon', 'Qto_SlabBaseQuantities'],
        'IfcSpace': ['Qto_SpaceBaseQuantities'],
        'IfcProject': ['ePset_abstractBIM']  # Project-specific properties
    }
    
    # Get relevant property sets for this element type
    relevant_psets = element_to_psets.get(element_type, [])
    
    # Check if the property set is relevant
    return pset_name in relevant_psets

def _extract_property_sets(el):
    """Extract property sets from an IFC element."""
    properties = {}
    if hasattr(el, "IsDefinedBy"):
        for rel_def in el.IsDefinedBy:
            # Only process IfcRelDefinesByProperties relationships
            if not rel_def.is_a("IfcRelDefinesByProperties"):
                continue
                
            # Verify that this element is actually in the RelatedObjects list
            if not hasattr(rel_def, "RelatedObjects") or el not in rel_def.RelatedObjects:
                continue
                
            prop_set = rel_def.RelatingPropertyDefinition
            if prop_set.is_a("IfcPropertySet"):
                pset_name = prop_set.Name
                for prop in prop_set.HasProperties:
                    prop_name = f"{pset_name}.{prop.Name}"
                    prop_value = getattr(prop, "NominalValue", None)
                    if prop_value:
                        try:
                            value = prop_value.wrappedValue
                            properties[prop_name] = value if isinstance(value, bool) else str(value)
                        except AttributeError:
                            properties[prop_name] = str(prop_value)
                    else:
                        # Include property even if it has no value
                        properties[prop_name] = None

    # Special handling for LongName in ePset_abstractBIM
    if "ePset_abstractBIM.SpacesLongName" in properties:
        properties["ePset_abstractBIM.LongName"] = properties.pop("ePset_abstractBIM.SpacesLongName")

    return properties

def _save_to_json(elements_data, output_json_path):
    """Save elements data to a JSON file."""
    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        json_data = {
            "elements": {str(elem["id"]): elem for elem in elements_data}
        }
        with open(output_json_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Metadata saved to {output_json_path}")

def extract_ifc_metadata(ifc_file_path, output_json_path=None):
    """Extract metadata from an IFC file and optionally save to JSON."""
    ifc_file = ifcopenshell.open(ifc_file_path)
    logger.info(f"Opening IFC file for metadata extraction: {ifc_file_path}")

    # Build basic mappings
    globalid_to_id, all_elements = _build_element_id_mapping(ifc_file)
    project = all_elements[0]  # First element is the project
    child_to_parent = _build_parent_child_mapping(ifc_file, project, globalid_to_id)

    # Extract classification and system data
    classification_id_map, classification_data, next_id = _extract_classification_data(
        ifc_file, all_elements, len(all_elements) + 1
    )
    system_id_map, system_data = _extract_system_data(ifc_file, all_elements, next_id)

    # Build element records
    elements_data = classification_data + system_data
    for idx, el in enumerate(all_elements, start=1):
        record = _create_element_record(el, idx, globalid_to_id, child_to_parent)
        
        # Add classification and system references
        if hasattr(el, "HasAssociations"):
            for association in el.HasAssociations:
                if association.is_a("IfcRelAssociatesClassification"):
                    classification = association.RelatingClassification
                    classification_key = str(classification)
                    if classification_key in classification_id_map:
                        record["Classifications"].append(classification_id_map[classification_key])
                elif association.is_a("IfcRelAssociatesLibrary"):
                    library = association.RelatingLibrary
                    library_key = str(library)
                    if library_key in classification_id_map:
                        record["Classifications"].append(classification_id_map[library_key])

        if hasattr(el, "HasAssignments"):
            for assignment in el.HasAssignments:
                if assignment.is_a("IfcRelAssignsToGroup"):
                    group = assignment.RelatingGroup
                    if group.is_a("IfcSystem"):
                        system_key = str(group)
                        if system_key in system_id_map:
                            record["Systems"].append(system_id_map[system_key])
                elif assignment.is_a("IfcRelAssignsToProcess"):
                    process = assignment.RelatingProcess
                    system_key = str(process)
                    if system_key in system_id_map:
                        record["Systems"].append(system_id_map[system_key])
                elif assignment.is_a("IfcRelAssignsToResource"):
                    resource = assignment.RelatingResource
                    system_key = str(resource)
                    if system_key in system_id_map:
                        record["Systems"].append(system_id_map[system_key])

        elements_data.append(record)

    # Save to JSON if requested
    if output_json_path:
        elements_dict = {str(elem["id"]): elem for elem in elements_data}
        json_data = {"elements": elements_dict}
        with open(output_json_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Metadata saved to {output_json_path}")

    return elements_data


# Example usage:
# df = extract_ifc_metadata("path/to/your.ifc", "output.json")
