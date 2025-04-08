from typing import List, Optional, Any, Literal, Union
from ifcopenshell.entity_instance import entity_instance as IfcElement
import pandas as pd


class QtoCalculator:
    """
    Calculator for quantity takeoffs from IFC models.

    The default values are based on the abstractBIM IFC, but can be overridden.

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
        quantity_type: Literal["area", "volume", "count"],
        include_filter: Optional[dict] = None,
        include_filter_logic: Literal["AND", "OR"] = "OR",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        ifc_entity: str = "IfcSpace",
        pset_name: Optional[str] = None,
        prop_name: Optional[str] = None
    ) -> Union[float, int]:
        """
        Generic method to calculate quantities (area, volume, or count) with filters and filter logic.
        For count metrics, pset_name and prop_name are optional as we just count the elements.
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
            },
            "count": {
                "include_filter": None,
                "prop_name": None
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

        if quantity_type == "count":
            # For count, just return the number of elements
            return len(include_elements) - len(subtract_elements)
        else:
            # For area and volume, sum the quantities
            included_total = self.sum_quantity(include_elements, pset_name, prop_name)
            subtracted_total = self.sum_quantity(subtract_elements, pset_name, prop_name)
            return included_total - subtracted_total



    def _get_elements_by_space(
        self,
        ifc_entity: str,
        grouping_attribute: str = "LongName",
        room_reference_attribute_guid: str = "ePset_abstractBIM.Spaces",
        include_filter: Optional[dict] = None,
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "OR",
        pset_name: str = "Qto_BaseQuantities",
        prop_name: str = "NetArea",
    ) -> dict:
        """Get elements grouped by space with their areas.
        
        Args:
            ifc_entity: Type of element to get (e.g., "IfcCovering", "IfcWindow", "IfcDoor")
            grouping_attribute: Space attribute to group by (default: "LongName")
            room_reference_attribute_guid: Property set and property containing space references
            include_filter: Filter to apply to elements
            include_filter_logic: How to combine include filters ("AND" or "OR")
            subtract_filter: Filter for elements to subtract
            subtract_filter_logic: How to combine subtract filters ("AND" or "OR")
            pset_name: Name of the quantity property set
            prop_name: Name of the area property
        
        Returns:
            Dictionary mapping space names to total element areas
        """
        # Get elements
        elements = self.loader.get_elements(
            filters=include_filter,
            filter_logic=include_filter_logic,
            ifc_entity=ifc_entity
        ) or []
        
        # Get all spaces
        spaces = self.loader.get_elements(ifc_entity="IfcSpace") or []
        space_map = {space.GlobalId: getattr(space, grouping_attribute, space.GlobalId) 
                     for space in spaces}
        
        # Initialize result
        result = {}
        
        # Process each element
        for element in elements:
            # Get the area
            area = 0.0
            for rel in getattr(element, "IsDefinedBy", []):
                qto = getattr(rel, "RelatingPropertyDefinition", None)
                if not qto or not qto.is_a("IfcElementQuantity") or qto.Name != pset_name:
                    continue
                for quantity in getattr(qto, "Quantities", []):
                    if quantity.Name == prop_name and quantity.is_a("IfcQuantityArea"):
                        area = quantity.AreaValue
                        break
            
            if area == 0.0:
                continue
            
            # Get the space references
            for rel in getattr(element, "IsDefinedBy", []):
                pset = getattr(rel, "RelatingPropertyDefinition", None)
                if not pset or not pset.is_a("IfcPropertySet"):
                    continue
                
                pset_name_ref, prop_name_ref = room_reference_attribute_guid.split(".")
                if pset.Name != pset_name_ref:
                    continue
                
                for prop in pset.HasProperties:
                    if prop.Name == prop_name_ref:
                        space_refs = []
                        if isinstance(prop.NominalValue.wrappedValue, list):
                            space_refs.extend(prop.NominalValue.wrappedValue)
                        else:
                            space_refs.append(prop.NominalValue.wrappedValue)
                        
                        # Add area to each referenced space
                        for space_ref in space_refs:
                            room_key = space_map.get(space_ref)
                            if room_key:
                                if room_key not in result:
                                    result[room_key] = 0.0
                                result[room_key] += area
    
        return result



    