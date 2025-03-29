import ifcopenshell
from typing import List, Optional, Any
from ifcopenshell.entity_instance import entity_instance


class IfcProject:
    def __init__(self, file_path: str):
        """Initialize an IFC project from a file.

        Args:
            file_path (str): Path to the IFC file to be loaded
        
        Raises:
            OSError: If the file cannot be found or opened
            RuntimeError: If the file is not a valid IFC file
        """
        self.file_path = file_path
        self.model = ifcopenshell.open(file_path)

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
        """
        if not hasattr(element, "IsDefinedBy"):
            return None

        for definition in element.IsDefinedBy:
            prop_def = getattr(definition, "RelatingPropertyDefinition", None)
            if not prop_def:
                continue

            if prop_def.is_a("IfcPropertySet") and prop_def.Name == set_name:
                for prop in getattr(prop_def, "HasProperties", []):
                    if prop.Name == prop_name:
                        return getattr(prop, "NominalValue", None)

            elif prop_def.is_a("IfcElementQuantity") and prop_def.Name == set_name:
                for quantity in getattr(prop_def, "Quantities", []):
                    if quantity.Name == prop_name:
                        return getattr(quantity, "NominalValue", None)

        return NoneNominalValue

    def get_ifc_elements(
        self,
        ifc_entity: str,
        attribute: Optional[str] = None,
        value: Optional[str] = None
    ) -> List[entity_instance]:
        """Get IFC elements of a specific type with optional attribute filter.
        
        Retrieves elements from the IFC model based on their type and optionally
        filters them by a specific attribute value.

        Args:
            ifc_entity (str): The IFC entity type to search for (e.g., "IfcSpace", "IfcWall")
            attribute (str, optional): The attribute name to filter by (e.g., "Name", "Description")
            value (str, optional): The value to filter for. Only elements where
                                 attribute == value will be returned
            
        Returns:
            List[entity_instance]: List of IFC elements matching the criteria
        
        Examples:
            >>> # Get all walls in the model
            >>> walls = project.get_ifc_elements("IfcWall")
            >>> # Get all spaces named "Office"
            >>> offices = project.get_ifc_elements("IfcSpace", "Name", "Office")
        """
        elements = self.model.by_type(ifc_entity)
        
        if attribute and value:
            elements = [e for e in elements if getattr(e, attribute) == value]
        
        return elements

    def get_gfa_elements(
        self,
        ifc_entity: str = "IfcSpace",
        attribute: str = "Name",
        value: str = "GFA"
    ) -> List[entity_instance]:
            """Extract elements based on specified criteria, defaulting to GFA spaces.
            
            Args:
                ifc_entity (str, optional): The IFC entity type to search for. Defaults to "IfcSpace"
                attribute (str, optional): The attribute to filter by. Defaults to "Name"
                value (str, optional): The value to match. Defaults to "GFA"

            Returns:
                List[entity_instance]: List of IFC elements matching the criteria

            Examples:
                >>> # Get default GFA spaces
                >>> gfa_spaces = project.get_gfa_elements()
                >>> # Get spaces with custom name
                >>> custom_spaces = project.get_gfa_elements(value="CustomArea")
                >>> # Get walls with specific attribute
                >>> walls = project.get_gfa_elements(ifc_entity="IfcWall", attribute="Description", value="External")
            """
            return self.get_ifc_elements(
                ifc_entity=ifc_entity,
                attribute=attribute,
                value=value
            )
