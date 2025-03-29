import ifcopenshell
import os
from typing import List, Optional, Any, Dict, Union
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
            The property's NominalValue if found, otherwise None.
            
        Example:
            >>> loader = IfcLoader("office.ifc")
            >>> wall = loader.model.by_type("IfcWall")[0]  # Get the first wall
            >>> is_external = loader.get_property_value(wall, "Pset_WallCommon", "IsExternal")
            >>> print(f"Is external wall: {is_external}")
        """
        # Safety check for invalid element
        if element is None:
            return None
            
        if not hasattr(element, "IsDefinedBy"):
            return None

        for definition in element.IsDefinedBy:
            # Check if definition has RelatingPropertyDefinition
            if not hasattr(definition, "RelatingPropertyDefinition"):
                continue
                
            prop_def = definition.RelatingPropertyDefinition
            if prop_def is None:
                continue

            # Process property sets
            if prop_def.is_a("IfcPropertySet") and prop_def.Name == set_name:
                if not hasattr(prop_def, "HasProperties"):
                    continue
                    
                for prop in prop_def.HasProperties:
                    if prop.Name == prop_name:
                        if hasattr(prop, "NominalValue"):
                            return prop.NominalValue
                        else:
                            # Handle direct values based on property type
                            if hasattr(prop, "Name") and hasattr(prop, "Value"):
                                return prop.Value  # For simple property types
                            return None

            # Process quantity sets
            elif prop_def.is_a("IfcElementQuantity") and prop_def.Name == set_name:
                if not hasattr(prop_def, "Quantities"):
                    continue
                    
                for quantity in prop_def.Quantities:
                    if quantity.Name == prop_name:
                        # Try to extract the appropriate value based on quantity type
                        if quantity.is_a("IfcQuantityArea"):
                            return quantity.AreaValue
                        elif quantity.is_a("IfcQuantityVolume"):
                            return quantity.VolumeValue
                        elif quantity.is_a("IfcQuantityLength"):
                            return quantity.LengthValue
                        elif quantity.is_a("IfcQuantityCount"):
                            return quantity.CountValue
                        elif quantity.is_a("IfcQuantityWeight"):
                            return quantity.WeightValue
                        elif hasattr(quantity, "NominalValue"):
                            return quantity.NominalValue
                        
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
        filters: Optional[Dict[str, Any]] = None,
        ifc_entity: Optional[str] = None
    ) -> List[entity_instance]:
        """
        Retrieve IFC elements matching multiple filter criteria.

        Args:
            filters: Dictionary of {attribute/property: value} pairs to match
            ifc_entity: IFC entity type to filter (e.g., "IfcWall")

        Returns:
            List[entity_instance]: Matching IFC elements
            
        Example:
            >>> loader = IfcLoader("office.ifc")
            >>> # Get all external walls
            >>> external_walls = loader.get_elements(
            ...     filters={"IsExternal": True},
            ...     ifc_entity="IfcWall"
            ... )
            >>> print(f"Found {len(external_walls)} external walls")
        """
        elements = self.model.by_type(ifc_entity) if ifc_entity else self.model.by_type("IfcProduct")
        
        if not filters:
            return elements
            
        # Normalize filters to handle various input types
        normalized_filters = {}
        for key, value in filters.items():
            if isinstance(value, list) and len(value) == 1:
                normalized_filters[key] = value[0]
            else:
                normalized_filters[key] = value

        results = []
        for element in elements:
            matches_all = True
            
            for key, value in normalized_filters.items():
                # Check direct attribute
                if hasattr(element, key):
                    attr_value = getattr(element, key)
                    if attr_value != value:
                        # Special case for string comparison - allow partial matches
                        if isinstance(attr_value, str) and isinstance(value, str):
                            if value.lower() not in attr_value.lower():
                                matches_all = False
                                break
                        else:
                            matches_all = False
                            break
                    continue

                # Check property sets
                # First try in Pset_Common
                prop_value = self.get_property_value(element, "Pset_Common", key)
                if prop_value is None:
                    # If not found, try type-specific property sets
                    if element.is_a("IfcWall"):
                        prop_value = self.get_property_value(element, "Pset_WallCommon", key)
                    elif element.is_a("IfcSpace"):
                        prop_value = self.get_property_value(element, "Pset_SpaceCommon", key)
                    # Add more element types as needed
                    
                if prop_value != value:
                    # Special case for string comparison - allow partial matches
                    if isinstance(prop_value, str) and isinstance(value, str):
                        if value.lower() not in prop_value.lower():
                            matches_all = False
                            break
                    else:
                        matches_all = False
                        break

            if matches_all:
                results.append(element)

        return results

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