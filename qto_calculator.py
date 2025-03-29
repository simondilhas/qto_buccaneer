from typing import List, Optional, Any, Literal
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
    

    def calculate_quantity(
        self,
        quantity_type: Literal["area", "volume"],
        include_filter: Optional[dict] = None,
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: Optional[str] = None
    ) -> float:
        """
        Generic method to calculate quantities (area or volume) with filters.
        """
        # Default filters and property names based on quantity type
        defaults = {
            "area": {
                "include_filter": {"Name": "GrossArea"},
                "prop_name": "NetFloorArea"
            },
            "volume": {
                "include_filter": {"Name": "GrossVolume"},
                "prop_name": "NetVolume"
            }
        }

        # Use provided values or defaults
        include_filter = include_filter or defaults[quantity_type]["include_filter"]
        prop_name = prop_name or defaults[quantity_type]["prop_name"]

        # Get elements using the current IfcLoader interface
        include_elements = self.loader.get_elements(
            filters=include_filter,
            ifc_entity=ifc_entity
        )
        
        subtract_elements = []
        if subtract_filter:
            subtract_elements = self.loader.get_elements(
                filters=subtract_filter,
                ifc_entity=ifc_entity
            )

        included_total = self.sum_quantity(include_elements, pset_name, prop_name)
        subtracted_total = self.sum_quantity(subtract_elements, pset_name, prop_name)

        return included_total - subtracted_total

    def calculate_gross_floor_area(
        self,
        include_filter: Optional[dict] = None,
        subtract_filter: Optional[dict] = None,
        **kwargs
    ) -> float:
        """
        Calculates the gross floor area.
        
        In the abstractBIM IFC standard, Gross Floor Area is defined as the area measured 
        to the exterior face of exterior walls, including all interior spaces.
        
        Args:
            include_filter: Optional override for default gross area filter
            subtract_filter: Optional filter for areas to subtract
            **kwargs: Additional arguments passed to calculate_quantity
            
        Returns:
            float: The gross floor area in m²
        
        Example:
            >>> qto = QtoCalculator(loader)
            >>> gfa = qto.calculate_gross_floor_area(
            ...     subtract_filter={"LongName": "Technical"}
            ... )
            >>> print(f"Gross Floor Area: {gfa:.2f} m²")
        """
        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            **kwargs
        )

    def calculate_gross_floor_volume(
        self,
        include_filter: Optional[dict] = None,
        subtract_filter: Optional[dict] = None,
        **kwargs
    ) -> float:
        """
        Calculates the gross floor volume.
        
        In the abstractBIM IFC standard, Gross Volume is calculated based on
        the volume enclosed by the exterior face of exterior walls, including all interior spaces.
        
        Args:
            include_filter: Optional override for default gross volume filter
            subtract_filter: Optional filter for volumes to subtract
            **kwargs: Additional arguments passed to calculate_quantity
            
        Returns:
            float: The gross floor volume in m³
        
        Example:
            >>> qto = QtoCalculator(loader)
            >>> volume = qto.calculate_gross_floor_volume(
            ...     subtract_filter={"LongName": "Technical"}
            ... )
            >>> print(f"Gross Volume: {volume:.2f} m³")
        """
        return self.calculate_quantity(
            quantity_type="volume",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            **kwargs
        )
