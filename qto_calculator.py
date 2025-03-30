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
        include_filter_logic: Literal["AND", "OR"] = "OR",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: Optional[str] = None
    ) -> float:
        """
        Generic method to calculate quantities (area or volume) with filters and filter logic.

        Args:
            quantity_type: Type of quantity to calculate ("area" or "volume")
            include_filter: Optional filter for elements to include
            include_filter_logic: Logic to apply for include filters ("AND" or "OR", default: "OR")
            subtract_filter: Optional filter for elements to subtract
            subtract_filter_logic: Logic to apply for subtract filters ("AND" or "OR", default: "OR")
            ifc_entity: IFC class to extract quantities from
            pset_name: Property set name containing the quantity
            prop_name: Name of the quantity property

        Returns:
            float: The calculated quantity (area in m² or volume in m³)
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

        # Get elements using the current IfcLoader interface with filter logic
        include_elements = self.loader.get_elements(
            filters=include_filter,
            filter_logic=include_filter_logic,
            ifc_entity=ifc_entity
        )
        
        subtract_elements = []
        if subtract_filter:
            subtract_elements = self.loader.get_elements(
                filters=subtract_filter,
                filter_logic=subtract_filter_logic,
                ifc_entity=ifc_entity
            )

        included_total = self.sum_quantity(include_elements, pset_name, prop_name)
        subtracted_total = self.sum_quantity(subtract_elements, pset_name, prop_name)

        return included_total - subtracted_total

    def calculate_gross_floor_area(
        self,
        include_filter: Optional[dict] = None,
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: Optional[str] = None,
    ) -> float:
        """
        Calculates the gross floor area.
        
        Args:
            include_filter: Optional override for default gross area filter
            subtract_filter: Optional filter for areas to subtract
            ifc_entity: IFC class to extract areas from (default: "IfcSpace")
            pset_name: Property set name (default: "Qto_SpaceBaseQuantities")
            prop_name: Quantity name in the property set (default: "NetFloorArea")
        
        Returns:
            float: The gross floor area in m²
        """
        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )


    def calculate_gross_floor_volume(
        self,
        include_filter: Optional[dict] = None,
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: Optional[str] = None,
    ) -> float:
        """
        Calculates the gross floor volume.

        In the abstractBIM IFC standard, Gross Volume is calculated based on
        the volume enclosed by the exterior face of exterior walls, including all interior spaces.

        Args:
            include_filter: Optional override for default gross volume filter
            subtract_filter: Optional filter for volumes to subtract
            ifc_entity: IFC class to extract volumes from (default: "IfcSpace")
            pset_name: Property set name (default: "Qto_SpaceBaseQuantities")
            prop_name: Quantity name in the property set (default: "NetVolume")

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
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_coverings_exterior_area(
        self,
        include_filter: Optional[dict] = {"PredefinedType": "CLADDING",
                                          "Pset_CoveringCommon.IsExternal": True,},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcCovering",
        pset_name: str = "Qto_CoveringBaseQuantities",
        prop_name: str = "NetArea",
    ) -> float:
        """
        Calculates the total area of exterior coverings.

        In the abstractBIM IFC standard, exterior coverings are defined as coverings
        where the 'IsExternal' attribute is True.

        Args:
            include_filter: Optional override for the default filter (IsExternal: True)
            subtract_filter: Optional filter for coverings to subtract (e.g., temporary insulation)
            ifc_entity: IFC class to extract areas from (default: "IfcCovering")
            pset_name: Property set name (default: "Qto_CoveringBaseQuantities")
            prop_name: Quantity name in the property set (default: "NetArea")

        Returns:
            float: Total area of exterior coverings in m²

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_exterior_coverings_area()
            >>> print(f"Exterior Coverings Area: {area:.2f} m²")
        """

        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_coverings_interior_area(
        self,
        include_filter: Optional[dict] = {"Pset_CoveringCommon.IsExternal": False},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcCovering",
        pset_name: str = "Qto_CoveringBaseQuantities",  
        prop_name: str = "NetArea",
    ) -> float:
        """
        Calculates the total area of interior coverings.
        """
        return self.calculate_quantity( 
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_windows_exterior_area(
        self,
        include_filter: Optional[dict] = {"Pset_WindowCommon.IsExternal": True},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcWindow",
        pset_name: str = "Qto_WindowBaseQuantities",
        prop_name: str = "Area",
    ) -> float:
        """
        Calculates the total area of exterior windows.

        Windows are considered exterior if the 'IsExternal' property in Pset_WindowCommon is True.

        Args:
            include_filter: Optional filter for exterior windows (default: IsExternal = True)
            subtract_filter: Optional filter to subtract some windows (e.g., temporary or construction openings)
            ifc_entity: IFC class to extract areas from (default: "IfcWindow")
            pset_name: Quantity set name (default: "Qto_WindowBaseQuantities")
            prop_name: Quantity name (default: "NetArea")

        Returns:
            float: Total exterior window area in m²

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_exterior_windows_area()
            >>> print(f"Exterior Windows Area: {area:.2f} m²")
        """
        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )
    
    def calculate_windows_interior_area(
        self,
        include_filter: Optional[dict] = {"Pset_WindowCommon.IsExternal": False},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcWindow",
        pset_name: str = "Qto_WindowBaseQuantities",
        prop_name: str = "Area",
    ) -> float:
        """
        Calculates the total area of exterior windows.

        Windows are considered exterior if the 'IsExternal' property in Pset_WindowCommon is True.

        Args:
            include_filter: Optional filter for exterior windows (default: IsExternal = True)
            subtract_filter: Optional filter to subtract some windows (e.g., temporary or construction openings)
            ifc_entity: IFC class to extract areas from (default: "IfcWindow")
            pset_name: Quantity set name (default: "Qto_WindowBaseQuantities")
            prop_name: Quantity name (default: "NetArea")

        Returns:
            float: Total exterior window area in m²

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_exterior_windows_area()
            >>> print(f"Exterior Windows Area: {area:.2f} m²")
        """
        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_doors_exterior_area(
        self,
        include_filter: Optional[dict] = {"Pset_DoorCommon.IsExternal": True},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcDoor",
        pset_name: str = "Qto_DoorBaseQuantities",
        prop_name: str = "Area",
    ) -> float:
        """
        Calculates the total area of exterior doors.

        Doors are considered exterior if the 'IsExternal' property in Pset_DoorCommon is True.

        Args:
            include_filter: Optional filter for exterior doors (default: IsExternal = True)
            subtract_filter: Optional filter to exclude certain doors (e.g., temporary construction openings)
            ifc_entity: IFC class to extract areas from (default: "IfcDoor")
            pset_name: Quantity set name (default: "Qto_DoorBaseQuantities")
            prop_name: Quantity name (default: "NetArea")

        Returns:
            float: Total exterior door area in m²

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_exterior_doors_area()
            >>> print(f"Exterior Doors Area: {area:.2f} m²")
        """
        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_doors_interior_area(
        self,
        include_filter: Optional[dict] = {"Pset_DoorCommon.IsExternal": False},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcDoor",
        pset_name: str = "Qto_DoorBaseQuantities",
        prop_name: str = "Area",
    ) -> float:
        """
        Calculates the total area of interior doors.

        Doors are considered interior if the 'IsExternal' property in Pset_DoorCommon is False.

        Args:
            include_filter: Optional filter for interior doors (default: IsExternal = False)
            subtract_filter: Optional filter to exclude certain doors
            ifc_entity: IFC class to extract areas from (default: "IfcDoor")
            pset_name: Quantity set name (default: "Qto_DoorBaseQuantities")
            prop_name: Quantity name (default: "Area")

        Returns:
            float: Total interior door area in m²

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_interior_doors_area()
            >>> print(f"Interior Doors Area: {area:.2f} m²")
        """
        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_walls_exterior_net_side_area(
        self,
        include_filter: Optional[dict] = {"Pset_WallCommon.IsExternal": True},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcWallStandardCase",
        pset_name: str = "Qto_WallBaseQuantities",
        prop_name: str = "NetSideArea",
    ) -> float:
        """
        Calculates the total net side area of exterior walls.

        Walls are considered exterior if the 'IsExternal' property in Pset_WallCommon is True.
        The net side area excludes openings like windows and doors.

        Args:
            include_filter: Optional filter for exterior walls (default: IsExternal = True)
            subtract_filter: Optional filter to exclude certain walls
            ifc_entity: IFC class to extract areas from (default: "IfcWallStandardCase")
            pset_name: Quantity set name (default: "Qto_WallBaseQuantities")
            prop_name: Quantity name (default: "NetSideArea")

        Returns:
            float: Total exterior wall net side area in m²

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_exterior_walls_net_side_area()
            >>> print(f"Exterior Walls Net Side Area: {area:.2f} m²")
        """
        return self.calculate_quantity(
            quantity_type="area",   
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_walls_interior_net_side_area( 
        self,
        include_filter: Optional[dict] = {"Pset_WallCommon.IsExternal": False},
        subtract_filter: Optional[dict] = None,
        ifc_entity: str = "IfcWallStandardCase",
        pset_name: str = "Qto_WallBaseQuantities",
        prop_name: str = "NetSideArea",
    ) -> float:
        """
        Calculates the total net side area of interior walls.

        Walls are considered interior if the 'IsExternal' property in Pset_WallCommon is False.
        The net side area excludes openings like doors and windows.

        Args:
            include_filter: Optional filter for interior walls (default: IsExternal = False)
            subtract_filter: Optional filter to exclude certain walls
            ifc_entity: IFC class to extract areas from (default: "IfcWallStandardCase")
            pset_name: Quantity set name (default: "Qto_WallBaseQuantities")
            prop_name: Quantity name (default: "NetSideArea")

        Returns:
            float: Total interior wall net side area in m²

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_walls_interior_net_side_area()
            >>> print(f"Interior Walls Net Side Area: {area:.2f} m²")
        """
        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            subtract_filter=subtract_filter,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_space_interior_floor_area(
        self,
        include_filter: Optional[dict] = {"PredefinedType": "INTERNAL"},
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = {
            "Name": ["LUF", "Void"]
        },
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: str = "NetFloorArea",
    ) -> float:
        """
        Calculates the total floor area of interior spaces.

        Args:
            include_filter: Optional filter for spaces to include (default: internal spaces)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for spaces to subtract (e.g., LUF spaces)
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
            ifc_entity: IFC class to extract areas from (default: "IfcSpace")
            pset_name: Property set name (default: "Qto_SpaceBaseQuantities")
            prop_name: Quantity name (default: "NetFloorArea")

        Returns:
            float: Total interior floor area in m²
        """
        return self.calculate_quantity(
            quantity_type="area",
            include_filter=include_filter,
            include_filter_logic=include_filter_logic,
            subtract_filter=subtract_filter,
            subtract_filter_logic=subtract_filter_logic,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )

    def calculate_space_interior_volume(
        self,
        ifc_entity: str = "IfcSpace",
        include_filter: Optional[dict] = {"PredefinedType": "INTERNAL"},
        include_filter_logic: Literal["AND", "OR"] = "OR",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "AND",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: str = "GrossVolume",
    ) -> float:
        """
        Calculates the total volume of spaces.

        Args:
            ifc_entity: IFC class to extract volumes from (default: "IfcSpace")
            include_filter: Optional filter for spaces to include
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "OR")
            subtract_filter: Optional filter for spaces to subtract
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "AND")
            pset_name: Property set name (default: "Qto_SpaceBaseQuantities")
            prop_name: Quantity name (default: "GrossVolume")

        Returns:
            float: Total space volume in m³
        """
        return self.calculate_quantity(
            quantity_type="volume",
            include_filter=include_filter,
            include_filter_logic=include_filter_logic,
            subtract_filter=subtract_filter,
            subtract_filter_logic=subtract_filter_logic,
            ifc_entity=ifc_entity,
            pset_name=pset_name,
            prop_name=prop_name,
        )