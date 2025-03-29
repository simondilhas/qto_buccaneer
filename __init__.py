from .ifc_loader import IfcLoader
from .qto_calculator import QtoCalculator
from typing import List, Dict, Any

class QtoCalculator:
    def __init__(self, loader):
        """
        Initialize the QtoCalculator with an IFC loader instance.

        Args:
            loader: An instance of IfcLoader, already loaded with an IFC file.
        """
        self.loader = loader

    def calculate_area(
        self,
        ifc_entity: str,
        key: str,
        value: str,
        pset_name: str,
        prop_name: str
    ) -> List[Dict[str, Any]]:
        """
        General-purpose area calculator for IFC elements based on filtering and quantity set.

        Args:
            ifc_entity (str): The IFC entity type to search for (e.g., "IfcSpace", "IfcWall").
            key (str): The attribute or property name used to filter elements (e.g., "Name").
            value (str): The value to match for the filtering key (e.g., "NNF", "GFA").
            pset_name (str): The name of the property or quantity set (e.g., "Qto_SpaceBaseQuantities").
            prop_name (str): The specific quantity/property name to extract (e.g., "NetFloorArea").

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing 'id', 'name', and 'area'.

        Example:
            >>> qto = QtoCalculator(loader)
            >>> areas = qto.calculate_area(
            ...     ifc_entity="IfcSpace",
            ...     key="Name",
            ...     value="NNF",
            ...     pset_name="Qto_SpaceBaseQuantities",
            ...     prop_name="NetFloorArea"
            ... )
        """
        elements = self.loader.get_elements(key=key, value=value, ifc_entity=ifc_entity)
        results = []

        for element in elements:
            quantity = self.loader.get_property_value(element, pset_name, prop_name)
            results.append({
                "id": element.GlobalId,
                "name": getattr(element, "Name", None),
                "area": quantity.wrappedValue if quantity else None
            })

        return results

    def calculate_gfa_area(self) -> List[Dict[str, Any]]:
        """
        Calculates the Gross Floor Area (GFA) for all spaces labeled "GFA".

        Uses abstractBIM default:
            - Entity: IfcSpace
            - Filter: Name == "GFA"
            - Quantity: Qto_SpaceBaseQuantities.NetFloorArea

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing 'id', 'name', and 'area'.

        Example:
            >>> qto = QtoCalculator(loader)
            >>> gfa_areas = qto.calculate_gfa_area()
        """
        return self.calculate_area(
            ifc_entity="IfcSpace",
            key="Name",
            value="GFA",
            pset_name="Qto_SpaceBaseQuantities",
            prop_name="NetFloorArea"
        )
