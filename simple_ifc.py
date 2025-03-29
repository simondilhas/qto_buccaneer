from typing import List, Dict, Any, Optional
from ifc_loader import IfcLoader
from qto_calculator import QtoCalculator

# TODO: realy necessary? update when all the functionality is implemented


class SimpleIFC:
    """
    A simplified interface for working with IFC files.
    Designed for users with minimal programming experience.
    """
    
    def __init__(self, file_path: str):
        """
        Open an IFC file for analysis.
        
        Args:
            file_path: Path to your IFC file
            
        Example:
            >>> project = SimpleIFC("my_building.ifc")
        """
        self.loader = IfcLoader(file_path)
        self.calculator = QtoCalculator(self.loader)
        self.file_path = file_path
    
    def get_spaces(self, name_contains: Optional[str] = None) -> List[Any]:
        """
        Get spaces from the model, optionally filtering by name.
        
        Args:
            name_contains: Optional text to search for in space names
            
        Returns:
            List of spaces matching the criteria
            
        Example:
            >>> project = SimpleIFC("office_building.ifc")
            >>> # Get all spaces
            >>> all_spaces = project.get_spaces()
            >>> # Get only office spaces
            >>> offices = project.get_spaces(name_contains="Office")
        """
        spaces = self.loader.model.by_type("IfcSpace")
        
        if name_contains:
            return [space for space in spaces 
                    if hasattr(space, "Name") and space.Name 
                    and name_contains.lower() in space.Name.lower()]
        return spaces
    
    def get_total_floor_area(self, exclude_spaces: Optional[List[str]] = None) -> float:
        """
        Calculate the total floor area of the building.
        
        Args:
            exclude_spaces: Optional list of space names to exclude
                            (e.g., ["Technical", "Shaft"])
            
        Returns:
            Total floor area in square meters
            
        Example:
            >>> project = SimpleIFC("house.ifc")
            >>> area = project.get_total_floor_area(exclude_spaces=["Garage"])
            >>> print(f"Total living area: {area:.2f} m²")
        """
        subtract_filter = None
        if exclude_spaces:
            # Create a filter to exclude spaces with matching names
            # This is simplified and assumes exact matches
            subtract_filter = {"Name": exclude_spaces[0]} if len(exclude_spaces) == 1 else None
            # Note: This is a simplification - for multiple exclusions,
            # you would need more advanced filtering
        
        return self.calculator.calculate_gross_floor_area(
            subtract_filter=subtract_filter
        )
    
    def get_total_volume(self, exclude_spaces: Optional[List[str]] = None) -> float:
        """
        Calculate the total volume of the building.
        
        Args:
            exclude_spaces: Optional list of space names to exclude
                           (e.g., ["Technical", "Shaft"])
            
        Returns:
            Total volume in cubic meters
            
        Example:
            >>> project = SimpleIFC("house.ifc")
            >>> volume = project.get_total_volume()
            >>> print(f"Building volume: {volume:.2f} m³")
        """
        subtract_filter = None
        if exclude_spaces:
            # Same simplification as in get_total_floor_area
            subtract_filter = {"Name": exclude_spaces[0]} if len(exclude_spaces) == 1 else None
        
        return self.calculator.calculate_gross_floor_volume(
            subtract_filter=subtract_filter
        )
    
    def get_property(self, element: Any, property_name: str, set_name: str = "Pset_Common") -> Any:
        """
        Get a property value from an element.
        
        Args:
            element: An IFC element
            property_name: Name of the property to retrieve
            set_name: Name of the property set (default: "Pset_Common")
            
        Returns:
            The property value if found, None otherwise
            
        Example:
            >>> project = SimpleIFC("house.ifc")
            >>> walls = project.loader.model.by_type("IfcWall")
            >>> if walls:
            >>>     is_external = project.get_property(walls[0], "IsExternal")
            >>>     print(f"Is this wall external? {is_external}")
        """
        return self.loader.get_property_value(element, set_name, property_name)
    
    def find_elements_by_property(self, 
                                 element_type: str,
                                 property_name: str, 
                                 property_value: Any,
                                 set_name: str = "Pset_Common") -> List[Any]:
        """
        Find elements by a specific property value.
        
        Args:
            element_type: Type of IFC element (e.g., "IfcWall", "IfcSpace")
            property_name: Name of the property to check
            property_value: Value to match
            set_name: Name of the property set (default: "Pset_Common")
            
        Returns:
            List of elements matching the criteria
            
        Example:
            >>> project = SimpleIFC("house.ifc")
            >>> external_walls = project.find_elements_by_property(
            >>>     element_type="IfcWall",
            >>>     property_name="IsExternal",
            >>>     property_value=True
            >>> )
            >>> print(f"Found {len(external_walls)} external walls")
        """
        elements = self.loader.model.by_type(element_type)
        results = []
        
        for element in elements:
            value = self.get_property(element, property_name, set_name)
            if value == property_value:
                results.append(element)
                
        return results
    
    def get_element_info(self, element: Any) -> Dict[str, Any]:
        """
        Get readable information about an element.
        
        Args:
            element: An IFC element
            
        Returns:
            Dictionary with readable element information
            
        Example:
            >>> project = SimpleIFC("house.ifc")
            >>> spaces = project.get_spaces()
            >>> if spaces:
            >>>     info = project.get_element_info(spaces[0])
            >>>     for key, value in info.items():
            >>>         print(f"{key}: {value}")
        """
        info = {
            "Type": element.is_a(),
            "GlobalId": getattr(element, "GlobalId", None),
            "Name": getattr(element, "Name", None)
        }
        
        # Add common properties
        common_properties = ["Description", "LongName", "ObjectType"]
        for prop in common_properties:
            if hasattr(element, prop):
                info[prop] = getattr(element, prop)
        
        # Try to get floor area for spaces
        if element.is_a("IfcSpace"):
            area = self.calculator.sum_quantity(
                [element], 
                "Qto_SpaceBaseQuantities", 
                "NetFloorArea"
            )
            if area > 0:
                info["Area"] = f"{area:.2f} m²"
        
        return info