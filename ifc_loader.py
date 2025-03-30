import ifcopenshell
import os
from typing import List, Optional, Any, Dict, Union, Literal
from ifcopenshell.entity_instance import entity_instance

IfcElement = Any

class IfcError(Exception):
    """Base exception for IFC-related errors"""
    pass

class IfcFileNotFoundError(IfcError):
    """Raised when the IFC file cannot be found"""
    pass

class IfcInvalidFileError(IfcError):
    """Raised when the file is not a valid IFC file"""
    pass


class IfcLoader:
    def __init__(self, file_path: str):
        """Initialize an IFC project from a file.

        Args:
            file_path (str): Path to the IFC file to be loaded
        
        Raises:
            IfcFileNotFoundError: If the file cannot be found
            IfcInvalidFileError: If the file is not a valid IFC file
        """
        self.file_path = file_path
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise IfcFileNotFoundError(f"IFC file not found: {file_path}")
        
        try:
            self.model = ifcopenshell.open(file_path)
        except Exception as e:
            raise IfcInvalidFileError(f"Could not open {file_path} as an IFC file: {str(e)}")

    def get_property_value(self, element, set_name: str, prop_name: str) -> Optional[Any]:
        """
        Retrieves the value of a property or quantity from a specified Pset or Qset.
        Supports both IfcPropertySet and IfcElementQuantity.

        Args:
            element: The IFC element to extract the property from.
            set_name (str): The name of the property set or quantity set (e.g. "Pset_SpaceCommon", "Qto_SpaceBaseQuantities").
            prop_name (str): The name of the property or quantity (e.g. "IsExternal", "NetFloorArea").

        Returns:
            The unwrapped property value if found, otherwise None.
        """
        if element is None or not hasattr(element, "IsDefinedBy"):
            return None

        for definition in element.IsDefinedBy:
            if not hasattr(definition, "RelatingPropertyDefinition"):
                continue

            prop_def = definition.RelatingPropertyDefinition
            if prop_def is None:
                continue

            # Process property sets
            if prop_def.is_a("IfcPropertySet") and prop_def.Name == set_name:
                for prop in getattr(prop_def, "HasProperties", []):
                    if prop.Name == prop_name:
                        if hasattr(prop, "NominalValue"):
                            val = prop.NominalValue
                            if hasattr(val, "wrappedValue"):
                                return val.wrappedValue
                            return val
                        elif hasattr(prop, "Value"):  # For simple props
                            val = prop.Value
                            if hasattr(val, "wrappedValue"):
                                return val.wrappedValue
                            return val

            # Process quantity sets
            elif prop_def.is_a("IfcElementQuantity") and prop_def.Name == set_name:
                for quantity in getattr(prop_def, "Quantities", []):
                    if quantity.Name == prop_name:
                        if quantity.is_a("IfcQuantityArea"):
                            val = quantity.AreaValue
                        elif quantity.is_a("IfcQuantityVolume"):
                            val = quantity.VolumeValue
                        elif quantity.is_a("IfcQuantityLength"):
                            val = quantity.LengthValue
                        elif quantity.is_a("IfcQuantityCount"):
                            val = quantity.CountValue
                        elif quantity.is_a("IfcQuantityWeight"):
                            val = quantity.WeightValue
                        elif hasattr(quantity, "NominalValue"):
                            val = quantity.NominalValue
                        else:
                            val = None

                        if hasattr(val, "wrappedValue"):
                            return val.wrappedValue
                        return val

        return None


    def get_property_sets(self, element) -> Dict[str, Dict[str, Any]]:
        """
        Get all property sets for an element with their properties.
        
        Args:
            element: The IFC element
            
        Returns:
            Dictionary of property sets with their properties
            
        Example:
            >>> loader = IfcLoader("house.ifc")
            >>> wall = loader.model.by_type("IfcWall")[0]
            >>> property_sets = loader.get_property_sets(wall)
            >>> for pset_name, properties in property_sets.items():
            >>>     print(f"Property Set: {pset_name}")
            >>>     for prop_name, value in properties.items():
            >>>         print(f"  {prop_name}: {value}")
        """
        result = {}
        
        if not hasattr(element, "IsDefinedBy"):
            return result
            
        for definition in element.IsDefinedBy:
            if not hasattr(definition, "RelatingPropertyDefinition"):
                continue
                
            prop_def = definition.RelatingPropertyDefinition
            if prop_def is None:
                continue
                
            # Process property sets
            if prop_def.is_a("IfcPropertySet"):
                pset_name = prop_def.Name
                properties = {}
                
                for prop in getattr(prop_def, "HasProperties", []):
                    if hasattr(prop, "NominalValue"):
                        properties[prop.Name] = prop.NominalValue
                    elif hasattr(prop, "Value"):
                        properties[prop.Name] = prop.Value
                        
                result[pset_name] = properties
                
            # Process quantity sets
            elif prop_def.is_a("IfcElementQuantity"):
                qset_name = prop_def.Name
                quantities = {}
                
                for quantity in getattr(prop_def, "Quantities", []):
                    if quantity.is_a("IfcQuantityArea"):
                        quantities[quantity.Name] = quantity.AreaValue
                    elif quantity.is_a("IfcQuantityVolume"):
                        quantities[quantity.Name] = quantity.VolumeValue
                    elif quantity.is_a("IfcQuantityLength"):
                        quantities[quantity.Name] = quantity.LengthValue
                    elif quantity.is_a("IfcQuantityCount"):
                        quantities[quantity.Name] = quantity.CountValue
                    elif quantity.is_a("IfcQuantityWeight"):
                        quantities[quantity.Name] = quantity.WeightValue
                        
                result[qset_name] = quantities
                
        return result

    def get_elements(
        self,
        filters: Optional[dict] = None,
        filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSpace"
    ) -> List[IfcElement]:
        elements = self.model.by_type(ifc_entity)
        
        def compare_values(actual_value: Any, filter_value: Any) -> bool:
            if isinstance(filter_value, tuple) and len(filter_value) == 2:
                operator, value = filter_value
                try:
                    actual_value = float(actual_value)
                    value = float(value)
                    return {
                        ">": actual_value > value,
                        "<": actual_value < value,
                        "=": actual_value == value,
                        "!=": actual_value != value,
                        "<=": actual_value <= value,
                        ">=": actual_value >= value
                    }[operator]
                except (TypeError, ValueError):
                    return False
            elif isinstance(filter_value, list):
                return actual_value in filter_value
            
            return actual_value == filter_value

        filtered_elements = []
        for element in elements:
            matches = []
            
            for key, filter_value in filters.items():
                # Check direct attributes
                if hasattr(element, key):
                    val = getattr(element, key)
                    matches.append(compare_values(val, filter_value))
                    continue

                # Check property sets and quantity sets
                match_found = False
                for rel in getattr(element, "IsDefinedBy", []):
                    if not hasattr(rel, "RelatingPropertyDefinition"):
                        continue
                        
                    definition = rel.RelatingPropertyDefinition

                    # Handle property/quantity paths
                    if "." in key:
                        set_name, prop_name = key.split(".")
                        if definition.Name != set_name:
                            continue
                        
                        if definition.is_a("IfcPropertySet"):
                            for prop in definition.HasProperties:
                                if prop.Name == prop_name:
                                    val = prop.NominalValue.wrappedValue if hasattr(prop, "NominalValue") else None
                                    matches.append(compare_values(val, filter_value))
                                    match_found = True
                                    break
                        elif definition.is_a("IfcElementQuantity"):
                            for quantity in definition.Quantities:
                                if quantity.Name == prop_name:
                                    val = None
                                    if quantity.is_a("IfcQuantityLength"):
                                        val = quantity.LengthValue
                                    elif quantity.is_a("IfcQuantityArea"):
                                        val = quantity.AreaValue
                                    elif quantity.is_a("IfcQuantityVolume"):
                                        val = quantity.VolumeValue
                                    elif quantity.is_a("IfcQuantityCount"):
                                        val = quantity.CountValue
                                    if val is not None:
                                        matches.append(compare_values(val, filter_value))
                                        match_found = True
                                    break
                    else:
                        # Direct quantity name
                        if definition.is_a("IfcElementQuantity"):
                            for quantity in definition.Quantities:
                                if quantity.Name == key:
                                    val = None
                                    if quantity.is_a("IfcQuantityLength"):
                                        val = quantity.LengthValue
                                    elif quantity.is_a("IfcQuantityArea"):
                                        val = quantity.AreaValue
                                    elif quantity.is_a("IfcQuantityVolume"):
                                        val = quantity.VolumeValue
                                    elif quantity.is_a("IfcQuantityCount"):
                                        val = quantity.CountValue
                                    if val is not None:
                                        matches.append(compare_values(val, filter_value))
                                        match_found = True
                                    break
                
                    if match_found:
                        break

                if not match_found:
                    matches.append(False)

            if filter_logic == "AND" and all(matches):
                filtered_elements.append(element)
            elif filter_logic == "OR" and any(matches):
                filtered_elements.append(element)

        return filtered_elements


    def get_gfa_elements(
        self,
        ifc_entity: str = "IfcSpace",
        name_filter: str = "GFA"
    ) -> List[entity_instance]:
        """Extract elements for Gross Floor Area Spaces.
        
        Args:
            ifc_entity (str, optional): The IFC entity type to search for. Defaults to "IfcSpace"
            name_filter (str, optional): The value to match in Name field. Defaults to "GFA"

        Returns:
            List[entity_instance]: List of IFC elements matching the criteria

        Examples:
            >>> loader = IfcLoader("building.ifc")
            >>> gfa_spaces = loader.get_gfa_elements()
            >>> print(f"Found {len(gfa_spaces)} GFA spaces")
        """
        filters = {"Name": name_filter}
        return self.get_elements(
            filters=filters,
            ifc_entity=ifc_entity
        )
        
    def summary(self) -> Dict[str, Any]:
        """
        Get a summary of the IFC model.
        
        Returns:
            Dictionary with model summary information
            
        Example:
            >>> loader = IfcLoader("hospital.ifc")
            >>> info = loader.summary()
            >>> for key, value in info.items():
            >>>     print(f"{key}: {value}")
        """
        # Count elements by type
        element_counts = {}
        for entity_type in ["IfcWall", "IfcWindow", "IfcDoor", "IfcSpace", "IfcSlab"]:
            count = len(self.model.by_type(entity_type))
            if count > 0:
                element_counts[entity_type] = count
                
        # Try to get project information
        project_info = {}
        for project in self.model.by_type("IfcProject"):
            project_info["Name"] = getattr(project, "Name", "Unnamed")
            project_info["Description"] = getattr(project, "Description", "")
            break
            
        return {
            "File": os.path.basename(self.file_path),
            "Project": project_info,
            "Elements": element_counts,
            "Total Elements": len(self.model.by_type("IfcProduct"))
        }