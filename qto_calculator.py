from typing import List, Optional, Any
from ifcopenshell.entity_instance import entity_instance as IfcElement


class QtoCalculator:
    def __init__(self, loader):
        self.loader = loader

    def sum_quantity(self, elements, qset: str, quantity_name: str) -> float:
        """
        Sums up a quantity value from a quantity set for a list of IFC elements.

        Args:
            elements: List of IFC elements (e.g. spaces).
            qset (str): Name of the quantity set (e.g. "Qto_SpaceBaseQuantities").
            quantity_name (str): Name of the quantity to sum (e.g. "NetFloorArea").

        Returns:
            float: The total sum of the found quantities.
        """
        total = 0.0

        for el in elements:
            for rel in getattr(el, "IsDefinedBy", []):
                qto = getattr(rel, "RelatingPropertyDefinition", None)
                if not qto or not qto.is_a("IfcElementQuantity") or qto.Name != qset:
                    continue
                for quantity in getattr(qto, "Quantities", []):
                    if quantity.Name == quantity_name:
                        try:
                            if quantity.is_a("IfcQuantityArea"):
                                value = quantity.AreaValue
                            elif quantity.is_a("IfcQuantityVolume"):
                                value = quantity.VolumeValue
                            elif quantity.is_a("IfcQuantityLength"):
                                value = quantity.LengthValue
                            else:
                                value = None

                            if value is not None:
                                total += value

                        except AttributeError:
                            # Log or skip if quantity is malformed
                            pass
        return total
    

    def calculate_gross_floor_area(
        self,
        include_filter: dict = {"Name": "GrossArea"},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: str = "NetFloorArea"
    ) -> Optional[float]:
        
        """
        Calculates the gross floor area by summing a quantity from matching IFC elements,
        and subtracting quantities from elements matching optional exclusion filters.

        This method supports filtering both included and subtracted elements based on
        IFC attributes or property set values. It is flexible and aligned with abstractBIM
        conventions, suitable for calculating GFA, NNF, HNF, or other area/volume types.

        In the abstractBIM IFC standard, **Gross Floor Area** is defined as the area measured 
        to the **exterior face of exterior walls**, including **all interior spaces**.

        Args:
            include_filter (dict): Key-value pairs used to filter the main elements
                                   to include (e.g. {"Name": "GrossArea"}).
            subtract_filter (dict, optional): Key-value pairs to filter elements whose
                                              quantity should be subtracted (e.g. {"Function": "Circulation"}).
            ifc_entity (str): The IFC entity type to search for (default: "IfcSpace").
            pset_name (str): The quantity set name (default: "Qto_SpaceBaseQuantities").
            prop_name (str): The specific quantity name to sum (default: "NetFloorArea").
        Returns:
            float: The resulting area after subtraction (0.0 if no matches are found).
        Example:
            >>> qto = QtoCalculator(loader)
            >>> gfa_area = qto.calculate_gross_floor_area(
            ...     subtract_filter={"LongName": "LUF"}
            ... )
            >>> print(f"Area with subtraction: {gfa_area:.2f} m²")
        """

        include_elements = self._get_elements_from_filter(include_filter, ifc_entity)

        subtract_elements = []
        if subtract_filter:
            subtract_elements = self._get_elements_from_filter(subtract_filter, ifc_entity)

        included_total = self.sum_quantity(include_elements, pset_name, prop_name)
        subtracted_total = self.sum_quantity(subtract_elements, pset_name, prop_name) if subtract_elements else 0.0

        return included_total - subtracted_total

    def calculate_gross_floor_volume(
        self,
        include_filter: dict = {"Name": "GrossVolume"},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: str = "NetVolume"
    ) -> Optional[float]:
        
        """
        Calculates the gross floor volume by summing a quantity from matching IFC elements,
        and subtracting quantities from elements matching optional exclusion filters.

        This method supports filtering both included and subtracted elements based on
        IFC attributes or property set values. It is flexible and aligned with abstractBIM
        conventions, suitable for calculating GFA, NNF, HNF, or other area/volume types.

        Args:
            include_filter (dict): Key-value pairs used to filter the main elements
                                   to include (e.g. {"Name": "GrossArea"}).
            subtract_filter (dict, optional): Key-value pairs to filter elements whose
                                              quantity should be subtracted (e.g. {"Function": "Circulation"}).
            ifc_entity (str): The IFC entity type to search for (default: "IfcSpace").
            pset_name (str): The quantity set name (default: "Qto_SpaceBaseQuantities").
            prop_name (str): The specific quantity name to sum (default: "NetFloorArea").
        Returns:
            float: The resulting area after subtraction (0.0 if no matches are found).
        Example:
            >>> qto = QtoCalculator(loader)
            >>> gfa_area = qto.calculate_gross_floor_area(
            ...     subtract_filter={"LongName": "LUF"}
            ... )
            >>> print(f"Area with subtraction: {gfa_area:.2f} m²")
        """
        include_elements = self._get_elements_from_filter(include_filter, ifc_entity)

        subtract_elements = []
        if subtract_filter:
            subtract_elements = self._get_elements_from_filter(subtract_filter, ifc_entity)

        included_total = self.sum_quantity(include_elements, pset_name, prop_name)
        subtracted_total = self.sum_quantity(subtract_elements, pset_name, prop_name) if subtract_elements else 0.0

        return included_total - subtracted_total
    
    def calculate_gross_floor_volume(
        self,
        include_filter: dict = {"Name": "GrossVolume"},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: str = "NetVolume"
    ) -> Optional[float]:
        """
        Calculates the gross floor volume by summing a quantity from matching IFC elements,
        and subtracting quantities from elements matching optional exclusion filters.

        This method supports filtering both included and subtracted elements based on
        IFC attributes or property set values. It is flexible and aligned with abstractBIM
        conventions, suitable for calculating gross volume or other custom volumetric types
        such as NNF, HNF, or function-specific subvolumes.

        In the abstractBIM IFC standard, **Gross Volume** is calculated based on
        the **volume enclosed by the exterior face of exterior walls**, including **all interior spaces**.

        Args:
            include_filter (dict): Key-value pairs used to filter the main elements
                                   to include (e.g. {"Name": "GrossVolume"}).
            subtract_filter (dict, optional): Key-value pairs to filter elements whose
                                              quantity should be subtracted (e.g. {"Function": "Circulation"}).
            ifc_entity (str): The IFC entity type to search for (default: "IfcSpace").
            pset_name (str): The quantity set name (default: "Qto_SpaceBaseQuantities").
            prop_name (str): The specific quantity name to sum (default: "NetVolume").

        Returns:
            float: The resulting volume after subtraction (0.0 if no matches are found).

        Example:
            >>> qto = QtoCalculator(loader)
            >>> gross_volume = qto.calculate_gross_floor_volume(
            ...     subtract_filter={"LongName": "Technical"}
            ... )
            >>> print(f"Volume with subtraction: {gross_volume:.2f} m³")
        """
        include_elements = self._get_elements_from_filter(include_filter, ifc_entity)

        subtract_elements = []
        if subtract_filter:
            subtract_elements = self._get_elements_from_filter(subtract_filter, ifc_entity)

        included_total = self.sum_quantity(include_elements, pset_name, prop_name)
        subtracted_total = self.sum_quantity(subtract_elements, pset_name, prop_name) if subtract_elements else 0.0

        return included_total - subtracted_total



    def _get_elements_from_filter(self, filters: dict, ifc_entity: str) -> List[Any]:
        elements = []

        for key, raw_value in filters.items():
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            for value in values:
                matches = self.loader.get_elements(key=key, value=value, ifc_entity=ifc_entity)
                elements.extend(matches)

        return elements
