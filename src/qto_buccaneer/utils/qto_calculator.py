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
    

    def _get_property_value(self, element, pset_name: str, prop_name: str) -> tuple[Any, Any]:
        """Get a property value from a property set or quantity set.
        
        Args:
            element: The IFC element to get the property from
            pset_name: Name of the property set or quantity set
            prop_name: Name of the property or quantity
            
        Returns:
            Tuple of (raw_value, float_value). float_value will be None if value cannot be converted to float.
        """
        raw_value = self._find_property_or_quantity(element, pset_name, prop_name)
        float_value = self._try_convert_to_float(raw_value)
        return raw_value, float_value

    def _find_property_or_quantity(self, element, pset_name: str, prop_name: str) -> Any:
        """Find a property or quantity value from an element's property/quantity sets."""
        for rel in getattr(element, "IsDefinedBy", []):
            definition = getattr(rel, "RelatingPropertyDefinition", None)
            if not definition:
                continue
                
            if definition.Name != pset_name:
                continue
                
            if definition.is_a("IfcPropertySet"):
                return self._get_property_from_set(definition, prop_name)
            elif definition.is_a("IfcElementQuantity"):
                return self._get_quantity_from_set(definition, prop_name)
                
        return None

    def _get_property_from_set(self, pset, prop_name: str) -> Any:
        """Get a property value from a property set."""
        for prop in pset.HasProperties:
            if prop.Name == prop_name and hasattr(prop, 'NominalValue'):
                return prop.NominalValue.wrappedValue
        return None

    def _get_quantity_from_set(self, qto, quantity_name: str) -> Any:
        """Get a quantity value from a quantity set."""
        for quantity in qto.Quantities:
            if quantity.Name == quantity_name:
                if quantity.is_a("IfcQuantityArea"):
                    return quantity.AreaValue
                elif quantity.is_a("IfcQuantityVolume"):
                    return quantity.VolumeValue
                elif quantity.is_a("IfcQuantityLength"):
                    return quantity.LengthValue
        return None

    def _try_convert_to_float(self, value: Any) -> Optional[float]:
        """Try to convert a value to float, return None if conversion fails."""
        if value is None:
            return None
            
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _compare_numeric(self, value: float, operator: str, compare_value: float) -> bool:
        """Compare two numeric values using the specified operator."""
        print(f"Comparing {value} {operator} {compare_value} (types: {type(value)}, {type(compare_value)})")
        result = False
        if operator == ">":
            result = value > compare_value
        elif operator == ">=":
            result = value >= compare_value
        elif operator == "<":
            result = value < compare_value
        elif operator == "<=":
            result = value <= compare_value
        elif operator == "=":
            result = value == compare_value
        print(f"Comparison result: {result}")
        return result

    def _check_value_match(self, test_value: Any, filter_value: Any) -> bool:
        """Check if a value matches a filter condition."""
        print(f"\nChecking value match:")
        print(f"Test value: {test_value} (type: {type(test_value)})")
        print(f"Filter value: {filter_value} (type: {type(filter_value)})")
        
        # Handle numeric comparisons
        if isinstance(filter_value, list):
            if len(filter_value) == 2 and filter_value[0] in [">", ">=", "<", "<=", "="]:
                try:
                    test_float = float(test_value) if test_value is not None else None
                    compare_value = float(filter_value[1])
                    print(f"Numeric comparison: {test_float} {filter_value[0]} {compare_value}")
                    print(f"Test value type: {type(test_float)}, Compare value type: {type(compare_value)}")
                    if test_float is not None:
                        result = self._compare_numeric(test_float, filter_value[0], compare_value)
                        print(f"Numeric comparison result: {result}")
                        return result
                except (ValueError, TypeError) as e:
                    print(f"Failed to convert to float: {e}")
                    return False
            else:
                # List of possible values
                result = str(test_value) in [str(v) for v in filter_value]
                print(f"List comparison result: {result}")
                return result
        else:
            # Direct comparison
            result = str(test_value) == str(filter_value)
            print(f"Direct comparison result: {result}")
            return result
        return False

    def _apply_filter(self, element, filter_dict: dict, filter_logic: str = "AND") -> bool:
        """Apply a filter dictionary to an element."""
        if not filter_dict:
            return True
            
        print(f"\nApplying filter to element {element.GlobalId}:")
        print(f"Filter dict: {filter_dict}")
        print(f"Filter logic: {filter_logic}")
        
        matches = []
        for key, value in filter_dict.items():
            print(f"\nChecking filter: {key} = {value}")
            # Handle property set attributes
            if "." in key:
                pset_name, prop_name = key.split(".")
                prop_value, _ = self._get_property_value(element, pset_name, prop_name)
                print(f"Property {pset_name}.{prop_name} value: {prop_value}")
                match_result = self._check_value_match(prop_value, value)
                print(f"Match result: {match_result}")
                matches.append(match_result)
            else:
                # Direct attribute
                attr_value = getattr(element, key, None)
                print(f"Direct attribute {key} value: {attr_value}")
                match_result = self._check_value_match(attr_value, value)
                print(f"Match result: {match_result}")
                matches.append(match_result)
        
        if filter_logic == "AND":
            result = all(matches)
        else:  # OR logic
            result = any(matches)
            
        print(f"Final filter result: {result} (matches: {matches})")
        return result

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

        # Get all elements of the specified type first
        elements = self.loader.get_elements(ifc_entity=ifc_entity) or []
        print(f"\nFound {len(elements)} {ifc_entity} elements")
        
        # Apply include filter
        if include_filter:
            filtered_elements = [
                element for element in elements 
                if self._apply_filter(element, include_filter, include_filter_logic)
            ]
            elements = filtered_elements
            print(f"After include filtering: {len(elements)} elements")
        
        # Apply subtract filter
        if subtract_filter:
            elements = [
                element for element in elements 
                if not self._apply_filter(element, subtract_filter, subtract_filter_logic)
            ]
            print(f"After subtract filtering: {len(elements)} elements")

        if quantity_type == "count":
            # For count, just return the number of elements
            return len(elements)
        else:
            # For area and volume, sum the quantities
            return self.sum_quantity(elements, pset_name, prop_name)



    def _get_elements_by_space(
        self,
        ifc_entity: str,
        pset_name: str,
        prop_name: str,
        grouping_attribute: str,
        room_reference_attribute_guid: str,
        include_filter: dict = None,
        include_filter_logic: str = "AND",
    ) -> dict:
        """Get elements grouped by space and sum their quantities.

        Args:
            ifc_entity: The IFC entity to get elements for.
            pset_name: The name of the property set to get the quantity from.
            prop_name: The name of the property to get the quantity from.
            grouping_attribute: The attribute to group the elements by.
            room_reference_attribute_guid: The property set and property name for the room reference GUID.
            include_filter: A dictionary of conditions to include only specific elements.
            include_filter_logic: The logic to use when combining multiple include filters.

        Returns:
            A dictionary with the space name as key and the sum of quantities as value.
        """
        # Get all elements of the specified entity
        elements = self.ifc_file.by_type(ifc_entity)
        print(f"Found {len(elements)} {ifc_entity} elements")

        # Apply include filters if specified
        if include_filter:
            elements = self._apply_filters(elements, include_filter, include_filter_logic)

        # Create a dictionary to store the sum of quantities for each space
        space_quantities = {}

        # Get all spaces for mapping GUIDs to names
        spaces = self.ifc_file.by_type("IfcSpace")
        space_map = {space.GlobalId: space.LongName for space in spaces}
        print(f"Found {len(spaces)} spaces for mapping")

        # Process each element
        for element in elements:
            # Get the quantity from the property set
            quantity = self._get_quantity(element, pset_name, prop_name)
            if quantity is None:
                continue

            # Get space references from the property set
            space_guids = []
            if room_reference_attribute_guid:
                pset_name, prop_name = room_reference_attribute_guid.split(".")
                space_guids = self._get_property_value(element, pset_name, prop_name)
                if space_guids is None:
                    space_guids = []
                elif not isinstance(space_guids, list):
                    space_guids = [space_guids]

            # For each space reference, add the quantity to the space's total
            for space_guid in space_guids:
                space_name = space_map.get(space_guid)
                if space_name:
                    if space_name not in space_quantities:
                        space_quantities[space_name] = 0
                    space_quantities[space_name] += quantity

        print(f"Calculated quantities for {len(space_quantities)} spaces")
        return space_quantities


    def _get_elements_by_attribute(
        self,
        ifc_entity: str,
        grouping_attribute: str,
        grouping_pset: Optional[str] = None,
        include_filter: Optional[dict] = None,
        include_filter_logic: Literal["AND", "OR"] = "AND",
        subtract_filter: Optional[dict] = None,
        subtract_filter_logic: Literal["AND", "OR"] = "AND",
        pset_name: str = "Qto_BaseQuantities",
        prop_name: str = "NetArea",
    ) -> dict:
        """Get elements grouped by an attribute with their quantities."""
        # Get filtered elements first
        print(f"\nGetting elements with filters:")
        print(f"Entity: {ifc_entity}")
        print(f"Include filter: {include_filter}")
        print(f"Include filter logic: {include_filter_logic}")
        print(f"Grouping attribute: {grouping_attribute}")
        print(f"Grouping pset: {grouping_pset}")
        print(f"Pset name: {pset_name}")
        print(f"Prop name: {prop_name}")
        
        # Get all elements of the specified type first
        elements = self.loader.get_elements(ifc_entity=ifc_entity) or []
        print(f"\nFound {len(elements)} {ifc_entity} elements")
        
        # Debug first element's properties
        if elements:
            self.debug_element_properties(elements[0])
        
        # Initialize result
        result = {}
        
        # Process each element
        for element in elements:
            print(f"\nProcessing element {element.GlobalId}")
            
            # Get the quantity
            quantity = 0.0
            for rel in getattr(element, "IsDefinedBy", []):
                qto = getattr(rel, "RelatingPropertyDefinition", None)
                if not qto or not qto.is_a("IfcElementQuantity"):
                    continue
                print(f"Found quantity set: {qto.Name}")
                for q in getattr(qto, "Quantities", []):
                    if q.Name == prop_name:
                        if q.is_a("IfcQuantityArea"):
                            quantity = q.AreaValue
                            print(f"Found area: {quantity}")
                        elif q.is_a("IfcQuantityVolume"):
                            quantity = q.VolumeValue
                        elif q.is_a("IfcQuantityLength"):
                            quantity = q.LengthValue
                        break
            
            if quantity == 0.0:
                print(f"Warning: No quantity found for element {element.GlobalId}")
                continue

            # Get the grouping value
            group_value = None
            
            # Check if grouping_attribute is a property set attribute
            if "." in grouping_attribute:
                pset_name_group, prop_name_group = grouping_attribute.split(".")
                print(f"Looking for property {pset_name_group}.{prop_name_group}")
                
                # Get the property value directly
                group_value, _ = self._get_property_value(element, pset_name_group, prop_name_group)
                if group_value is not None:
                    print(f"Found group value: {group_value}")
            else:
                # For direct attributes (e.g., "LongName")
                if hasattr(element, grouping_attribute):
                    group_value = getattr(element, grouping_attribute)
                    print(f"Got direct attribute {grouping_attribute} = {group_value}")
            
            if group_value is not None:
                # Convert group value to string for consistency
                group_value = str(group_value)
                if group_value not in result:
                    result[group_value] = 0.0
                result[group_value] += quantity
                print(f"Added quantity {quantity} to group {group_value}")
            else:
                print(f"Warning: No grouping value found for element {element.GlobalId}")
                self.debug_element_properties(element)

        print(f"Final result: {result}")
        return result

    def debug_element_attributes(self, ifc_entity: str):
        """Debug function to understand how to access element attributes."""
        elements = self.loader.get_elements(ifc_entity=ifc_entity) or []
        
        if not elements:
            print(f"No elements found for entity {ifc_entity}")
            return
            
        element = elements[0]  # Take first element as example
        print(f"\nDebugging element: {element}")
        
        # 1. Print all direct attributes
        print("\nDirect attributes:")
        for attr in dir(element):
            if not attr.startswith('_'):
                try:
                    value = getattr(element, attr)
                    print(f"{attr}: {value}")
                except:
                    print(f"{attr}: <error accessing>")
        
        # 2. Print all property sets and their properties
        print("\nProperty sets:")
        for rel in getattr(element, "IsDefinedBy", []):
            pset = getattr(rel, "RelatingPropertyDefinition", None)
            if pset and pset.is_a("IfcPropertySet"):
                print(f"\nProperty Set: {pset.Name}")
                for prop in pset.HasProperties:
                    if hasattr(prop, 'NominalValue'):
                        print(f"  {prop.Name}: {prop.NominalValue.wrappedValue}")
                    else:
                        print(f"  {prop.Name}: <no NominalValue>")
        
        # 3. Print all quantity sets
        print("\nQuantity sets:")
        for rel in getattr(element, "IsDefinedBy", []):
            qto = getattr(rel, "RelatingPropertyDefinition", None)
            if qto and qto.is_a("IfcElementQuantity"):
                print(f"\nQuantity Set: {qto.Name}")
                for q in getattr(qto, "Quantities", []):
                    if q.is_a("IfcQuantityArea"):
                        print(f"  {q.Name}: {q.AreaValue}")
                    elif q.is_a("IfcQuantityVolume"):
                        print(f"  {q.Name}: {q.VolumeValue}")
                    elif q.is_a("IfcQuantityLength"):
                        print(f"  {q.Name}: {q.LengthValue}")
                    else:
                        print(f"  {q.Name}: <unknown quantity type>")

    def debug_element_properties(self, element) -> None:
        """Debug method to print all property sets and their properties for an element."""
        print("\nDEBUG - Element Properties:")
        print(f"Element Type: {element.is_a()}")
        print(f"Element GlobalId: {element.GlobalId}")
        
        for rel in getattr(element, "IsDefinedBy", []):
            definition = getattr(rel, "RelatingPropertyDefinition", None)
            if not definition:
                continue
                
            print(f"\nProperty Set/Quantity Set: {definition.Name}")
            print(f"Type: {definition.is_a()}")
            
            if definition.is_a("IfcPropertySet"):
                for prop in definition.HasProperties:
                    if hasattr(prop, 'NominalValue'):
                        print(f"  Property: {prop.Name} = {prop.NominalValue.wrappedValue}")
            elif definition.is_a("IfcElementQuantity"):
                for quantity in definition.Quantities:
                    if quantity.is_a("IfcQuantityArea"):
                        print(f"  Quantity: {quantity.Name} = {quantity.AreaValue}")
                    elif quantity.is_a("IfcQuantityVolume"):
                        print(f"  Quantity: {quantity.Name} = {quantity.VolumeValue}")
                    elif quantity.is_a("IfcQuantityLength"):
                        print(f"  Quantity: {quantity.Name} = {quantity.LengthValue}")



    