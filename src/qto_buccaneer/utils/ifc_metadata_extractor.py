import ifcopenshell
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import os
from pathlib import Path
import json
import numpy as np

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

def _build_hierarchy_index(ifc_file: Any) -> Tuple[Dict[int, Any], Dict[str, List[int]], Dict[str, int]]:
    """
    Build a normalized hierarchy index from the IFC file with robust parent-child handling.
    
    This implements a two-pass approach:
    1. First pass: Create all elements with tentative parent relationships
    2. Second pass: Validate and fix parent relationships
    
    Args:
        ifc_file (Any): The opened IFC file object
        
    Returns:
        Tuple containing elements dictionary, type index, and GlobalId mapping
    """
    elements = {}
    type_index = {}
    global_id_to_id = {}  # Map GlobalId to our integer ID
    id_counter = 1  # Start with 1
    
    # First pass: create all elements with tentative parent relationships
    for product in ifc_file.by_type('IfcProduct'):
        #element, id_counter = _create_element_dict(product, id_counter, global_id_to_id)
        element, id_counter = _create_element_dict(product, id_counter, global_id_to_id, ifc_file)

        elements[element["id"]] = element
        global_id_to_id[product.GlobalId] = element["id"]
        
        # Build type index using ifc_type from metadata
        ifc_type = element.get("IfcEntity", "")
        if ifc_type:
            if ifc_type not in type_index:
                type_index[ifc_type] = []
            type_index[ifc_type].append(element["id"])
    
    # Second pass: validate and fix parent relationships
    _validate_hierarchy(elements)
    
    return elements, type_index, global_id_to_id

def _validate_hierarchy(elements: Dict[int, Any]) -> None:
    """
    Validate the element hierarchy and fix any issues:
    1. Detect and resolve cycles
    2. Set missing parent_ids to None
    3. Ensure all parent_ids reference existing elements
    
    Args:
        elements: Dictionary of elements indexed by internal ID
    """
    # Check for missing parents
    for elem_id, element in elements.items():
        if element["parent_id"] is not None and element["parent_id"] not in elements:
            logger.warning(f"Element {elem_id} references non-existent parent {element['parent_id']}, setting to None")
            element["parent_id"] = None
    
    # Check for cycles
    for start_id in elements:
        _detect_and_fix_cycle(elements, start_id)

def _detect_and_fix_cycle(elements: Dict[int, Any], start_id: int) -> bool:
    """
    Detect and fix any cycles in the parent-child relationships.
    
    Args:
        elements: Dictionary of elements indexed by internal ID
        start_id: Element ID to start checking from
        
    Returns:
        bool: True if a cycle was detected and fixed, False otherwise
    """
    visited = set()
    current_path = []
    
    def _dfs(node_id):
        if node_id in visited:
            return False
        
        if node_id in current_path:
            # Cycle detected
            cycle_start = current_path.index(node_id)
            cycle = current_path[cycle_start:] + [node_id]
            logger.warning(f"Detected cycle in parent-child relationships: {cycle}")
            
            # Fix cycle by breaking the link at the current node
            elements[current_path[-1]]["parent_id"] = None
            logger.info(f"Fixed cycle by removing parent_id from element {current_path[-1]}")
            return True
        
        if node_id not in elements or elements[node_id]["parent_id"] is None:
            return False
        
        current_path.append(node_id)
        parent_id = elements[node_id]["parent_id"]
        
        cycle_detected = _dfs(parent_id)
        
        current_path.pop()
        visited.add(node_id)
        
        return cycle_detected
    
    return _dfs(start_id)

def _get_parent_id(product: Any, global_id_to_id: Dict[str, int], ifc_file: Any) -> Optional[int]:

    """
    Get the parent ID for any IFC product by systematically checking all possible relationships.
    """
    if not hasattr(product, 'GlobalId'):
        logger.warning(f"Product has no GlobalId, cannot determine parent")
        return None

    try:
        parent_candidates = []

        # 1. Check filling/voiding relationships (Host: Window, Door to Wall)
        for fills_rel in ifc_file.by_type('IfcRelFillsElement'):
            if fills_rel.RelatedBuildingElement == product and fills_rel.RelatingOpeningElement is not None:
                opening = fills_rel.RelatingOpeningElement
                for voids_rel in ifc_file.by_type('IfcRelVoidsElement'):
                    if voids_rel.RelatedOpeningElement == opening and voids_rel.RelatingBuildingElement is not None:
                        host = voids_rel.RelatingBuildingElement
                        if host.GlobalId in global_id_to_id:
                            parent_candidates.append((global_id_to_id[host.GlobalId], "HostElement", 100))

        # 2. Check direct spatial containment
        container = None
        for rel in ifc_file.by_type('IfcRelContainedInSpatialStructure'):
            if product in rel.RelatedElements and rel.RelatingStructure is not None:
                container = rel.RelatingStructure
                break  # only first found

        if container and hasattr(container, "GlobalId") and container.GlobalId in global_id_to_id:
            parent_candidates.append((global_id_to_id[container.GlobalId], "SpatialContainer", 70))

        # 3. Check aggregation
        for rel in ifc_file.by_type('IfcRelAggregates'):
            if product in rel.RelatedObjects and rel.RelatingObject is not None:
                aggregate = rel.RelatingObject
                if aggregate.GlobalId in global_id_to_id:
                    parent_candidates.append((global_id_to_id[aggregate.GlobalId], "Aggregate", 90))

        # 4. Check nesting
        for rel in ifc_file.by_type('IfcRelNests'):
            if product in rel.RelatedObjects and rel.RelatingObject is not None:
                nest = rel.RelatingObject
                if nest.GlobalId in global_id_to_id:
                    parent_candidates.append((global_id_to_id[nest.GlobalId], "Nests", 85))

        # 5. Placement hierarchy fallback (placement hierarchy is very weak fallback)
        if hasattr(product, 'ObjectPlacement') and product.ObjectPlacement is not None:
            placement = product.ObjectPlacement
            if hasattr(placement, 'PlacementRelTo') and placement.PlacementRelTo is not None:
                for rel_product in ifc_file.by_type('IfcProduct'):
                    if rel_product != product and hasattr(rel_product, 'ObjectPlacement') and rel_product.ObjectPlacement == placement.PlacementRelTo:
                        if rel_product.GlobalId in global_id_to_id:
                            parent_candidates.append((global_id_to_id[rel_product.GlobalId], "PlacementHierarchy", 65))

        # ✅ Always take the best available parent
        if parent_candidates:
            parent_candidates.sort(key=lambda x: x[2], reverse=True)
            parent_id, relationship_type, _ = parent_candidates[0]
            logger.debug(f"Found parent for {product.GlobalId} through {relationship_type}")
            return parent_id

        # 🛑 If still no parent → fallback manually to first available Building or Site
        # Look for a containing spatial structure
        for rel in ifc_file.by_type('IfcRelContainedInSpatialStructure'):
            if product in rel.RelatedElements:
                fallback_container = rel.RelatingStructure
                if fallback_container and hasattr(fallback_container, 'GlobalId') and fallback_container.GlobalId in global_id_to_id:
                    logger.debug(f"Fallback spatial container for {product.GlobalId}: {fallback_container.is_a()}")
                    return global_id_to_id[fallback_container.GlobalId]

        # 🔥 ABSOLUTE last fallback: find any IfcBuilding or IfcSite
        for obj in ifc_file.by_type(('IfcBuilding', 'IfcSite')):
            if hasattr(obj, "GlobalId") and obj.GlobalId in global_id_to_id:
                logger.debug(f"Hard fallback to Building/Site for {product.GlobalId}")
                return global_id_to_id[obj.GlobalId]

        logger.debug(f"No parent relationship found for {product.GlobalId} ({product.is_a()})")
        return None

    except Exception as e:
        logger.warning(f"Error getting parent ID for {product.GlobalId}: {str(e)}")
        return None


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

def _extract_properties(product: Any) -> Dict[str, Any]:
    """
    Extract property sets and quantities from an IFC product.
    
    Args:
        product (Any): The IFC product entity
        
    Returns:
        Dict[str, Any]: Dictionary of properties and quantities
    """
    metadata = {}
    
    if not hasattr(product, 'IsDefinedBy'):
        return metadata
        
    for definition in product.IsDefinedBy:
        try:
            if not hasattr(definition, 'RelatingPropertyDefinition'):
                continue
                
            prop_def = definition.RelatingPropertyDefinition
            
            # Handle property sets
            if prop_def.is_a('IfcPropertySet'):
                for prop in prop_def.HasProperties:
                    key, value = _extract_property_value(prop, prop_def.Name)
                    if key and value is not None:
                        metadata[key] = value
                        
            # Handle quantities
            elif prop_def.is_a('IfcElementQuantity'):
                for quantity in prop_def.Quantities:
                    key = f"{prop_def.Name}.{quantity.Name}"
                    if hasattr(quantity, 'LengthValue'):
                        metadata[key] = quantity.LengthValue
                    elif hasattr(quantity, 'AreaValue'):
                        metadata[key] = quantity.AreaValue
                    elif hasattr(quantity, 'VolumeValue'):
                        metadata[key] = quantity.VolumeValue
                        
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

def _create_element_dict(product: Any, id_counter: int, global_id_to_id: Dict[str, int], ifc_file: Any) -> Tuple[Dict[str, Any], int]:
    """
    Create a normalized element dictionary with metadata and hierarchy information.
    
    Args:
        product (Any): The IFC product entity
        id_counter (int): Current ID counter
        global_id_to_id (Dict[str, int]): GlobalId to internal ID mapping
        ifc_file (Any): The IFC file object
        
    Returns:
        Tuple[Dict[str, Any], int]: Element dictionary and next ID counter
    """
    # Get parent ID
    parent_id = _get_parent_id(product, global_id_to_id, ifc_file)
    
    # Extract all metadata
    element = _extract_metadata(product)
    
    # Add hierarchy info
    element["id"] = id_counter
    element["parent_id"] = parent_id if parent_id is not None else None
    
    return element, id_counter + 1

def _build_hierarchy_index(ifc_file: Any) -> Tuple[Dict[int, Any], Dict[str, List[int]], Dict[str, int]]:
    """
    Build a normalized hierarchy index from the IFC file.
    
    This function processes all IFC products in the file and creates:
    1. A dictionary of elements with their metadata
    2. A type-based index for quick lookups
    3. A mapping from IFC GlobalIds to internal IDs
    
    Args:
        ifc_file (Any): The opened IFC file object
        
    Returns:
        Tuple[Dict[int, Any], Dict[str, List[int]], Dict[str, int]]: A tuple containing:
            - Dictionary of elements indexed by internal ID
            - Type index mapping entity types to element IDs
            - GlobalId to internal ID mapping
            
    Example:
        >>> ifc_file = ifcopenshell.open('model.ifc')
        >>> elements, type_index, global_id_map = _build_hierarchy_index(ifc_file)
        >>> print(f"Found {len(elements)} elements")
    """
    elements = {}
    type_index = {}
    global_id_to_id = {}  # Map GlobalId to our integer ID
    id_counter = 1  # Start with 1
    
    # First pass: create all elements
    for product in ifc_file.by_type('IfcProduct'):
        element, id_counter = _create_element_dict(product, id_counter, global_id_to_id, ifc_file)
        elements[element["id"]] = element
        global_id_to_id[product.GlobalId] = element["id"]
        
        # Build type index using ifc_type from metadata
        ifc_type = element.get("IfcEntity", "")
        if ifc_type:
            if ifc_type not in type_index:
                type_index[ifc_type] = []
            type_index[ifc_type].append(element["id"])
    
    return elements, type_index, global_id_to_id


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
    df = extract_ifc_metadata(ifc_file_path)

    # Prepare return values
    return_values = []

    # Handle requested formats in order
    if "dataframe" in output_formats:
        return_values.append(df)
    
    def convert_element(element):
        """Convert element fields to appropriate types.
        - id: integer
        - parent_id: integer or None
        - booleans: preserved as bool
        - NaN values: converted to None
        - null values: preserved as None
        - empty strings: preserved as empty strings
        - arrays: preserved as arrays
        - entity instances: converted to GlobalId or string representation
        - file objects: converted to string representation
        - All other fields: preserve original type
        """
        # Convert id to integer
        element['id'] = int(element['id'])
        
        # Convert parent_id to integer if not None and not NaN
        if element['parent_id'] is not None and not pd.isna(element['parent_id']):
            element['parent_id'] = int(element['parent_id'])
        else:
            element['parent_id'] = None
        
        # Handle all other fields
        for key, value in element.items():
            if isinstance(value, (list, np.ndarray)):
                # Handle lists of values
                if value and hasattr(value[0], 'is_a'):  # List of entities
                    element[key] = [v.GlobalId if hasattr(v, 'GlobalId') else str(v) for v in value]
                else:
                    # Preserve other arrays as is
                    continue
            elif pd.isna(value):
                element[key] = None
            elif isinstance(value, bool):
                # Preserve boolean values
                element[key] = bool(value)
            elif isinstance(value, str):
                # Preserve empty strings and $ values
                element[key] = str(value)
            elif hasattr(value, 'is_a'):  # Single entity
                if hasattr(value, 'GlobalId'):
                    element[key] = value.GlobalId
                else:
                    element[key] = str(value)
            elif hasattr(value, 'read'):  # File object
                element[key] = str(value)
            elif isinstance(value, float):
                # Convert float values to appropriate type
                if value.is_integer():
                    element[key] = int(value)
                else:
                    element[key] = float(value)
            elif isinstance(value, int):
                # Preserve integer values
                element[key] = int(value)
            else:
                # Convert any other non-serializable type to string
                element[key] = str(value)
            
        return element
    
    def create_elements_dict(df):
        """Create a dictionary of elements with string keys (required by JSON)
        but integer values for id and parent_id fields."""
        elements_dict = {}
        for _, row in df.iterrows():
            element = convert_element(row.to_dict())
            # JSON requires string keys, but we keep id and parent_id as integers in the values
            elements_dict[str(element['id'])] = element
        return elements_dict
    
    if "json" in output_formats:
        elements_dict = create_elements_dict(df)
        json_data = {"elements": elements_dict}
        return_values.append(json_data)
    
    if "json_file" in output_formats:
        json_path = output_dir / f"{project_name}_metadata.json"
        elements_dict = create_elements_dict(df)
        json_data = {"elements": elements_dict}
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Metadata saved to {json_path}")
        return_values.append(str(json_path))

    # Return only the requested values
    return tuple(return_values)


def extract_ifc_metadata(ifc_file_path, output_json_path=None):
    logger.info(f"Opening IFC file for metadata extraction: {ifc_file_path}")
    ifc_file = ifcopenshell.open(ifc_file_path)

    elements_data = []
    classification_id_map = {}  # Map IFC entity to our internal classification ID
    system_id_map = {}  # Map IFC entity to our internal system ID

    # Build GlobalId to ID map
    globalid_to_id = {}
    all_elements = []

    # First get the project
    project = ifc_file.by_type("IfcProject")[0]  # There should be exactly one project
    all_elements.append(project)

    # Then get all products
    for el in ifc_file.by_type("IfcProduct"):
        if el.is_a("IfcOpeningElement"):
            continue  # Skip openings
        all_elements.append(el)

    logger.debug(f"Found {len(all_elements)} elements (including project, excluding openings)")

    # First pass: gather basic info and collect classifications
    for idx, el in enumerate(all_elements, start=1):
        globalid_to_id[el.GlobalId] = idx

    # Build parent-child mapping from Aggregates and Containment relations
    child_to_parent = {}

    # Project is the root, so all sites should point to it
    for site in ifc_file.by_type("IfcSite"):
        child_to_parent[site.GlobalId] = project.GlobalId

    for rel in ifc_file.by_type("IfcRelAggregates"):
        if rel.RelatedObjects:
            parent = rel.RelatingObject
            for child in rel.RelatedObjects:
                child_to_parent[child.GlobalId] = parent.GlobalId

    for rel in ifc_file.by_type("IfcRelContainedInSpatialStructure"):
        if rel.RelatedElements:
            parent = rel.RelatingStructure
            for child in rel.RelatedElements:
                # Only set parent if not already set by Aggregates (prefer Aggregates)
                if child.GlobalId not in child_to_parent:
                    child_to_parent[child.GlobalId] = parent.GlobalId

    # First collect all unique classifications and systems
    counter = len(all_elements) + 1  # Start after regular elements
    
    # Collect classifications
    for el in all_elements:
        if hasattr(el, "HasAssociations"):
            for association in el.HasAssociations:
                if association.is_a("IfcRelAssociatesClassification"):
                    classification = association.RelatingClassification
                    classification_key = str(classification)
                    if classification_key not in classification_id_map:
                        if classification.is_a("IfcClassificationReference"):
                            classification_data = {
                                "id": counter,
                                "parent_id": None,
                                "GlobalId": getattr(classification, "GlobalId", None),
                                "IfcEntity": "IfcClassificationReference",
                                "Name": str(getattr(classification, "Name", "")),
                                "Description": str(getattr(classification, "Description", "")),
                                "Location": str(getattr(classification, "Location", "")),
                                "ItemReference": str(getattr(classification, "ItemReference", "")),
                                "ReferencedSource": str(getattr(classification, "ReferencedSource", ""))
                            }
                        elif classification.is_a("IfcClassification"):
                            classification_data = {
                                "id": counter,
                                "parent_id": None,
                                "GlobalId": getattr(classification, "GlobalId", None),
                                "IfcEntity": "IfcClassification",
                                "Name": str(getattr(classification, "Name", "")),
                                "Description": str(getattr(classification, "Description", "")),
                                "Location": str(getattr(classification, "Location", "")),
                                "Edition": str(getattr(classification, "Edition", "")),
                                "EditionDate": str(getattr(classification, "EditionDate", ""))
                            }
                        elements_data.append(classification_data)
                        classification_id_map[classification_key] = counter
                        counter += 1
                elif association.is_a("IfcRelAssociatesLibrary"):
                    library = association.RelatingLibrary
                    library_key = str(library)
                    if library_key not in classification_id_map:
                        library_data = {
                            "id": counter,
                            "parent_id": None,
                            "GlobalId": getattr(library, "GlobalId", None),
                            "IfcEntity": "IfcLibraryReference",
                            "Name": str(getattr(library, "Name", "")),
                            "Description": str(getattr(library, "Description", "")),
                            "Version": str(getattr(library, "Version", "")),
                            "VersionDate": str(getattr(library, "VersionDate", ""))
                        }
                        elements_data.append(library_data)
                        classification_id_map[library_key] = counter
                        counter += 1

    # Collect systems
    for el in all_elements:
        if hasattr(el, "HasAssignments"):
            for assignment in el.HasAssignments:
                if assignment.is_a("IfcRelAssignsToGroup"):
                    group = assignment.RelatingGroup
                    if group.is_a("IfcSystem"):
                        system_key = str(group)
                        if system_key not in system_id_map:
                            system_data = {
                                "id": counter,
                                "parent_id": None,
                                "GlobalId": getattr(group, "GlobalId", None),
                                "IfcEntity": "IfcSystem",
                                "Name": str(getattr(group, "Name", "")),
                                "Description": str(getattr(group, "Description", "")),
                                "ObjectType": str(getattr(group, "ObjectType", "")),
                                "Type": "System"
                            }
                            elements_data.append(system_data)
                            system_id_map[system_key] = counter
                            counter += 1
                elif assignment.is_a("IfcRelAssignsToProcess"):
                    process = assignment.RelatingProcess
                    system_key = str(process)
                    if system_key not in system_id_map:
                        system_data = {
                            "id": counter,
                            "parent_id": None,
                            "GlobalId": getattr(process, "GlobalId", None),
                            "IfcEntity": "IfcProcess",
                            "Name": str(getattr(process, "Name", "")),
                            "Description": str(getattr(process, "Description", "")),
                            "ObjectType": str(getattr(process, "ObjectType", "")),
                            "Type": "Process"
                        }
                        elements_data.append(system_data)
                        system_id_map[system_key] = counter
                        counter += 1
                elif assignment.is_a("IfcRelAssignsToResource"):
                    resource = assignment.RelatingResource
                    system_key = str(resource)
                    if system_key not in system_id_map:
                        system_data = {
                            "id": counter,
                            "parent_id": None,
                            "GlobalId": getattr(resource, "GlobalId", None),
                            "IfcEntity": "IfcResource",
                            "Name": str(getattr(resource, "Name", "")),
                            "Description": str(getattr(resource, "Description", "")),
                            "ObjectType": str(getattr(resource, "ObjectType", "")),
                            "Type": "Resource"
                        }
                        elements_data.append(system_data)
                        system_id_map[system_key] = counter
                        counter += 1

    # Now build full record for each element
    for idx, el in enumerate(all_elements, start=1):
        record = {
            "id": idx,
            "parent_id": None,
            "GlobalId": el.GlobalId,
            "IfcEntity": el.is_a(),
            "Classifications": [],  # List of classification IDs
            "Systems": []  # List of system IDs
        }

        parent_gid = child_to_parent.get(el.GlobalId)
        if parent_gid:
            record["parent_id"] = globalid_to_id.get(parent_gid)

        # Get all attributes from the element
        for attr in dir(el):
            if (not attr.startswith('_') and 
                not callable(getattr(el, attr)) and
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
                value = getattr(el, attr, None)
                # Handle entity instances
                if hasattr(value, 'is_a'):  # This is an IFC entity
                    if hasattr(value, 'GlobalId'):
                        record[attr] = value.GlobalId
                    else:
                        record[attr] = str(value)
                # Handle lists of entities
                elif isinstance(value, (list, tuple)) and value and hasattr(value[0], 'is_a'):
                    record[attr] = [v.GlobalId if hasattr(v, 'GlobalId') else str(v) for v in value]
                # Handle other values
                else:
                    record[attr] = value

        # Property Sets (Psets)
        if hasattr(el, "IsDefinedBy"):
            for rel_def in el.IsDefinedBy:
                if rel_def.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel_def.RelatingPropertyDefinition
                    if prop_set.is_a("IfcPropertySet"):
                        pset_name = prop_set.Name
                        for prop in prop_set.HasProperties:
                            prop_name = f"{pset_name}.{prop.Name}"
                            prop_value = getattr(prop, "NominalValue", None)
                            if prop_value:
                                try:
                                    value = prop_value.wrappedValue
                                    # Handle boolean values
                                    if isinstance(value, bool):
                                        record[prop_name] = value
                                    else:
                                        record[prop_name] = str(value)
                                except AttributeError:
                                    record[prop_name] = str(prop_value)

        # Add classification references
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

        # Add system references
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

    # Create DataFrame with explicit dtype mapping to preserve boolean values
    df = pd.DataFrame(elements_data)
    
    # Convert boolean columns back to boolean type
    for col in df.columns:
        if df[col].dtype == 'object':
            # Check if column contains boolean values
            if df[col].isin([True, False]).any():
                df[col] = df[col].astype('boolean')

    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        # Create the final JSON structure with all elements
        json_data = {
            "elements": {str(elem["id"]): elem for elem in elements_data}
        }
        with open(output_json_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Metadata saved to {output_json_path}")

    return df


# Example usage:
# df = extract_ifc_metadata("path/to/your.ifc", "output.json")
