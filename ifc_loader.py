import ifcopenshell
from typing import List, Optional, Any
from ifcopenshell.entity_instance import entity_instance

IfcElement = Any 

class IfcLoader:
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

        return None

    def get_elements(
        self,
        filters: dict[str, Any],
        ifc_entity: Optional[str] = None
    ) -> List[entity_instance]:
        """
        Retrieve IFC elements matching multiple filter criteria.

        Args:
            filters: Dictionary of {attribute/property: value} pairs to match
            ifc_entity: IFC entity type to filter (e.g., "IfcWall")

        Returns:
            List[entity_instance]: Matching IFC elements
        """
        elements = self.model.by_type(ifc_entity) if ifc_entity else self.model.by_type("IfcProduct")
        
        if not filters:
            return elements

        results = []
        for element in elements:
            matches_all = True
            
            for key, value in filters.items():
                # Check direct attribute
                if hasattr(element, key):
                    if getattr(element, key) != value:
                        matches_all = False
                        break
                    continue

                # Check property sets
                prop_value = self.get_property_value(element, "Pset_Common", key)
                if prop_value != value:
                    matches_all = False
                    break

            if matches_all:
                results.append(element)

        return results

    def get_gfa_elements(
        self,
        ifc_entity: str = "IfcSpace",
        key: str = "Name",
        value: str = "GFA"
    ) -> List[entity_instance]:
            """Extract elements Gross Floor Area Spaces, defaulting to abstractBIM Standard.
            
            Args:
                ifc_entity (str, optional): The IFC entity type to search for. Defaults to "IfcSpace"
                key (str): Attribute or property name to match. e.g. "Name", "Description", "GrossFloorArea"
                value (str, optional): The value to match. Defaults to "GFA"

            Returns:
                List[entity_instance]: List of IFC elements matching the criteria

            Examples:
                >>> gfa_spaces = project.get_gfa_elements()
                >>> print(gfa_spaces)
            """
            return self.get_elements(
                ifc_entity=ifc_entity,
                key=key,
                value=value
            )


