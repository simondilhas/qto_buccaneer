from typing import List, Optional, Any, Literal
from ifcopenshell.entity_instance import entity_instance as IfcElement


class QtoCalculator:
    """
    Calculator for quantity takeoffs from IFC models.

    Common Filter Examples:
    ----------------------
    1. Filter by properties:
       - Interior elements: {"Pset_WallCommon.IsExternal": False}
       - Exterior elements: {"Pset_WallCommon.IsExternal": True}
       - Specific type: {"PredefinedType": "ROOF"}
       - By name: {"Name": "Wall1"}

    2. Filter by measurements:
       - Walls thicker than 15cm: {"Width": (">", 0.15)}
       - Walls exactly 20cm thick: {"Width": ("=", 0.20)}
       - Walls up to 30cm thick: {"Width": ("<=", 0.30)}

    3. Filter by multiple names:
       - Multiple spaces: {"Name": ["Kitchen", "Bathroom", "Living"]}
       - Exclude spaces: {"Name": ["Void", "Shaft"]}

    4. Combining filters:
       - Interior walls thicker than 15cm:
         {
             "Pset_WallCommon.IsExternal": False,
             "Width": (">", 0.15)
         }

    Filter Logic:
    - "AND": Element must match all conditions (default)
    - "OR": Element must match any condition

    All measurements should be in meters for length/width/height
    and square meters for areas.
    """
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
        Filters can contain numeric comparisons using tuples: {"Width": (">", 0.15)}
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: Optional[str] = None,
    ) -> float:
        """
        Calculates the gross floor area.
        The default values are based on the abstractBIM IFC.

        Args:
            include_filter: Optional override for default gross area filter
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for areas to subtract 
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: Optional[str] = None,
    ) -> float:
        """
        Calculates the gross floor volume.
        The default values are based on the abstractBIM IFC.

        In the abstractBIM IFC standard, Gross Volume is calculated based on
        the volume enclosed by the exterior face of exterior walls, including all interior spaces.

        Args:
            include_filter: Optional override for default gross volume filter
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for volumes to subtract
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcCovering",
        pset_name: str = "Qto_CoveringBaseQuantities",
        prop_name: str = "NetArea",
    ) -> float:
        """
        Calculates the total area of exterior coverings.
        The default values are based on the abstractBIM IFC.
        In the abstractBIM IFC standard, exterior coverings are defined as coverings
        where the 'IsExternal' attribute is True.

        Args:
            include_filter: Optional override for the default filter (IsExternal: True)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for coverings to subtract (e.g., temporary insulation)
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcCovering",
        pset_name: str = "Qto_CoveringBaseQuantities",  
        prop_name: str = "NetArea",
    ) -> float:
        """
        Calculates the total area of interior coverings.
        The default values are based on the abstractBIM IFC.

        Args:
            include_filter: Optional filter for interior coverings (default: IsExternal = False)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for coverings to subtract (e.g., temporary insulation)
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
            ifc_entity: IFC class to extract areas from (default: "IfcCovering")
            pset_name: Property set name (default: "Qto_CoveringBaseQuantities")
            prop_name: Quantity name in the property set (default: "NetArea")

        Returns:
            float: Total area of interior coverings in m²

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_interior_coverings_area()
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcWindow",
        pset_name: str = "Qto_WindowBaseQuantities",
        prop_name: str = "Area",
    ) -> float:
        """
        Calculates the total area of exterior windows.
        The default values are based on the abstractBIM IFC.

        Windows are considered exterior if the 'IsExternal' property in Pset_WindowCommon is True.

        Args:
            include_filter: Optional filter for exterior windows (default: IsExternal = True)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter to subtract some windows (e.g., temporary or construction openings)
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcWindow",
        pset_name: str = "Qto_WindowBaseQuantities",
        prop_name: str = "Area",
    ) -> float:
        """
        Calculates the total area of exterior windows.
        The default values are based on the abstractBIM IFC.

        Windows are considered exterior if the 'IsExternal' property in Pset_WindowCommon is True.

        Args:
            include_filter: Optional filter for exterior windows (default: IsExternal = True)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter to subtract some windows (e.g., temporary or construction openings)
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcDoor",
        pset_name: str = "Qto_DoorBaseQuantities",
        prop_name: str = "Area",
    ) -> float:
        """
        Calculates the total area of exterior doors.
        The default values are based on the abstractBIM IFC.

        Doors are considered exterior if the 'IsExternal' property in Pset_DoorCommon is True.

        Args:
            include_filter: Optional filter for exterior doors (default: IsExternal = True)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter to exclude certain doors (e.g., temporary construction openings)
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcDoor",
        pset_name: str = "Qto_DoorBaseQuantities",
        prop_name: str = "Area",
    ) -> float:
        """
        Calculates the total area of interior doors.
        The default values are based on the abstractBIM IFC.
        Doors are considered interior if the 'IsExternal' property in Pset_DoorCommon is False.

        Args:
            include_filter: Optional filter for interior doors (default: IsExternal = False)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter to exclude certain doors
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcWallStandardCase",
        pset_name: str = "Qto_WallBaseQuantities",
        prop_name: str = "NetSideArea",
    ) -> float:
        """
        Calculates the total net side area of exterior walls.
        The default values are based on the abstractBIM IFC.

        Walls are considered exterior if the 'IsExternal' property in Pset_WallCommon is True.
        The net side area excludes openings like windows and doors.

        Args:
            include_filter: Optional filter for exterior walls (default: IsExternal = True)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter to exclude certain walls
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcWallStandardCase",
        pset_name: str = "Qto_WallBaseQuantities",
        prop_name: str = "NetSideArea",
    ) -> float:
        """
        Calculates the total net side area of interior walls.
        The default values are based on the abstractBIM IFC.
        Walls are considered interior if the 'IsExternal' property in Pset_WallCommon is False.
        The net side area excludes openings like doors and windows.

        Args:
            include_filter: Optional filter for interior walls (default: IsExternal = False)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter to exclude certain walls
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
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
    def calculate_walls_interior_structural_area(
        self,
        include_filter: Optional[dict] = {
            "Pset_WallCommon.IsExternal": False,
            "Qto_WallBaseQuantities.Width": ("<", 0.15)
        },
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "AND",
        ifc_entity: str = "IfcWallStandardCase",
        pset_name: str = "Qto_WallBaseQuantities",
        prop_name: str = "NetSideArea",
    ) -> float:
        """
        Calculates the total area of interior structural walls (walls thicker than 15cm).
        The default values are based on the abstractBIM IFC.
        Assumption is, that walls thicker than 15cm are structural walls.
        This is a simplification and may not be 100% accurate.

        Examples:
            >>> calculator = QtoCalculator(loader)
            
            # Get all interior structural walls (default)
            >>> area = calculator.calculate_walls_interior_structural_area()
            
            # Get very thick interior walls (more than 25cm)
            >>> area = calculator.calculate_walls_interior_structural_area(
            ...     include_filter={
            ...         "Pset_WallCommon.IsExternal": False,
            ...         "Width": (">", 0.25)
            ...     }
            ... )
            
            # Get specific walls by name
            >>> area = calculator.calculate_walls_interior_structural_area(
            ...     include_filter={
            ...         "Name": ["Load-bearing Wall 1", "Load-bearing Wall 2"]
            ...     }
            ... )

        The default settings will:
        - Include only interior walls (IsExternal = False)
        - Include only walls thicker than 15cm
        - Calculate their net area (excluding openings like doors and windows)
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
        The default values are based on the abstractBIM IFC.

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
        prop_name: str = "NetVolume",
    ) -> float:
        """
        Calculates the total volume of spaces. 
        The default values are based on the abstractBIM IFC.

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

    def calculate_space_exterior_area(
        self,
        include_filter: Optional[dict] = {"PredefinedType": "EXTERNAL"},
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: str = "NetFloorArea",
    ) -> float:
        """
        Calculates the total exterior area of spaces.
        The default values are based on the abstractBIM IFC.

        Args:
            include_filter: Optional filter for spaces to include (default: external spaces)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for spaces to subtract
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")   
            ifc_entity: IFC class to extract areas from (default: "IfcSpace")
            pset_name: Property set name (default: "Qto_SpaceBaseQuantities")
            prop_name: Quantity name (default: "NetFloorArea")

        Returns:
            float: Total exterior area of spaces in m²
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

    def calculate_slab_balcony_area(
        self,
        include_filter: Optional[dict] = {"Name": "Slab Balcony"},
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSlab",
        pset_name: str = "Qto_SlabBaseQuantities",
        prop_name: str = "NetArea",
    ) -> float:
        """
        Calculates the total exterior area of slabs.

        In the abstractBIM IFC standard, exterior slabs are defined as:
        - Balconies: Slabs with exterior space above
        - Cantilevered roofs: Also included as they meet the same criteria

        Args:
            include_filter: Optional filter for exterior slabs (default: slabs with exterior space above)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter to exclude certain slabs
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
            ifc_entity: IFC class to extract areas from (default: "IfcSlab")
            pset_name: Quantity set name (default: "Qto_SlabBaseQuantities")
            prop_name: Quantity name (default: "NetArea")

        Returns:
            float: Total exterior slab area in m²

        Warning:
            Cantilevered roofs are included in this calculation as they also have exterior space above.

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_slabs_exterior_area()
            >>> print(f"Exterior Slabs Area: {area:.2f} m²")
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

    def calculate_slab_interior_area(
        self,
        include_filter: Optional[dict] = {"PredefinedType": "FLOOR"},
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSlab",
        pset_name: str = "Qto_SlabBaseQuantities",
        prop_name: str = "NetArea",
    ) -> float:

        """
        Calculates the total interior area of slabs.
        The default values are based on the abstractBIM IFC.

        Args:
            include_filter: Optional filter for slabs to include (default: internal slabs)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for slabs to subtract
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
            ifc_entity: IFC class to extract areas from (default: "IfcSlab")
            pset_name: Property set name (default: "Qto_SlabBaseQuantities")
            prop_name: Quantity name (default: "NetArea")

        Returns:
            float: Total interior area of slabs in m²   

        Example:
            >>> qto = QtoCalculator(loader)
            >>> area = qto.calculate_slab_interior_area()
            >>> print(f"Slab Interior Area: {area:.2f} m²")
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

    def calculate_roof_area(
        self,
        include_filter: Optional[dict] = {"PredefinedType": "ROOF"},
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSlab",
        pset_name: str = "Qto_SlabBaseQuantities",
        prop_name: str = "NetArea",
    ) -> float: 
        """
        Calculates the total area of roofs.
        The default values are based on the abstractBIM IFC.

        Args:
            include_filter: Optional filter for roofs to include (default: roofs)   
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for roofs to subtract
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
            ifc_entity: IFC class to extract areas from (default: "IfcRoof")
            pset_name: Property set name (default: "Qto_RoofBaseQuantities")
            prop_name: Quantity name (default: "NetArea")

        Returns:
            float: Total roof area in m²
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

    def calculate_base_slab_area(
        self,
        include_filter: Optional[dict] = {"PredefinedType": "BASESLAB"},
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSlab",
        pset_name: str = "Qto_SlabBaseQuantities",
        prop_name: str = "NetArea",
    ) -> float: 
        """
        Calculates the total area of base slabs.
        The default values are based on the abstractBIM IFC.
        In the abstractBIM IFC standard, base slabs are defined as:
        - Base slabs: Slabs with a internal space above
        - Cantilevered Slabs: Also included as they meet the same criteria (sofar there is no way
         to differentiate between base and cantilevered slabs) 
         TODO: Add a filter for spaces that are in contact with the ground (manual data enrichment). 

        Args:
            include_filter: Optional filter for base slabs to include (default: base slabs)
            include_filter_logic: How to combine include filters ("AND" or "OR", default: "AND")
            subtract_filter: Optional filter for base slabs to subtract (e.g., temporary or construction openings)  
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR", default: "OR")
            ifc_entity: IFC class to extract areas from (default: "IfcSlab")
            pset_name: Property set name (default: "Qto_SlabBaseQuantities")
            prop_name: Quantity name (default: "NetArea")

        Returns:
            float: Total base slab area in m²
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
