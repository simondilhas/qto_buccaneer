# TODO make it work with the data from Microservice

from typing import Dict, List, Optional, Any

class IfcJsonLoader:
    """A class to load and manage IFC data from JSON files.
    
    This class provides methods to access geometry and properties data from IFC models
    that have been converted to JSON format.
    """
    
    def __init__(self, geometry_json: List[Dict[str, Any]], properties_json: Dict[str, Any]):
        """Initialize the loader with geometry and properties data.
        
        Args:
            geometry_json: List of geometry objects, each containing an 'id' and geometry data
            properties_json: Dictionary containing elements and their properties
        """
        self.geometry = geometry_json
        self.properties = properties_json
        
        # Create indexes for faster lookups using numeric IDs
        self.geometry_index = {str(item["id"]): item for item in self.geometry}
        self.properties_index = {str(elem_id): elem for elem_id, elem in properties_json["elements"].items()}
        
        # Create indexes from metadata
        self.by_type_index = properties_json.get("indexes", {}).get("by_type", {})
        self.global_id_to_id = properties_json.get("global_id_to_id", {})
        
        # Create a storey index for faster lookups
        self.storey_index = {}
        for element_id, element in properties_json["elements"].items():
            if element.get('type') == 'IfcBuildingStorey':
                self.storey_index[element_id] = element
            elif 'storey_id' in element:
                # Add reverse lookup from element to storey
                self.storey_index[element_id] = self.properties['elements'].get(str(element['storey_id']))
        
        # Cache for storey information
        self._storey_cache: Dict[str, str] = {}
        self._build_storey_cache()
    
    def _build_storey_cache(self):
        """Build a cache of storey information for faster lookups."""
        # Get all spaces using the by_type index
        space_ids = self.by_type_index.get("IfcSpace", [])
        for space_id in space_ids:
            space = self.properties["elements"].get(str(space_id))
            if space:
                # Get storey from parent
                parent_id = space.get("parent_id")
                if parent_id:
                    parent = self.properties["elements"].get(str(parent_id))
                    if parent and parent.get("type") == "IfcBuildingStorey":
                        self._storey_cache[str(space_id)] = parent.get("name", "Unknown")
    
    def get_spaces_in_storey(self, storey_name: str) -> List[str]:
        """Return a list of IDs of spaces in a given storey.
        
        Args:
            storey_name: Name of the storey to filter spaces by
            
        Returns:
            List of IDs for spaces in the specified storey
        """
        ids = []
        # Get all spaces using the by_type index
        space_ids = self.by_type_index.get("IfcSpace", [])
        
        for space_id in space_ids:
            space = self.properties["elements"].get(str(space_id))
            if not space:
                continue
                
            # Check PredefinedType if it exists
            predefined_type = space.get("properties", {}).get("PredefinedType", "")
            if predefined_type and predefined_type not in ["INTERNAL", "EXTERNAL"]:
                continue
            
            # Get storey from cache
            space_storey = self._storey_cache.get(str(space_id))
            
            # If no storey info, include the space in all storeys
            if space_storey is None:
                ids.append(str(space_id))
                print(f"Found space {space_id} (no storey info)")
            # Otherwise check if the storey name matches
            elif space_storey == storey_name:
                ids.append(str(space_id))
                print(f"Found space {space_id} in storey {storey_name}")
        
        return ids
    
    def get_geometry(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get geometry for a given element ID.
        
        Args:
            element_id: The ID of the element to get geometry for
            
        Returns:
            Geometry data for the element, or None if not found
        """
        return self.geometry_index.get(str(element_id))
    
    def get_properties(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get properties for a given element ID.
        
        Args:
            element_id: The ID of the element to get properties for
            
        Returns:
            Properties data for the element, or None if not found
        """
        return self.properties_index.get(str(element_id))
    
    def get_storey_for_space(self, space_id: str) -> Optional[str]:
        """Get the storey name for a given space.
        
        Args:
            space_id: The ID of the space
            
        Returns:
            The storey name, or None if not found
        """
        return self._storey_cache.get(str(space_id))

    def get_storey_for_element(self, element_id: str) -> Optional[str]:
        """Get the storey name for an element by its ID."""
        print(f"\nTrying to find storey for element {element_id}")
        element = self.properties['elements'].get(str(element_id))
        if not element:
            print(f"Element {element_id} not found in properties")
            return None
            
        print(f"Element type: {element.get('type')}")
            
        # First check if the element has a direct storey_id
        if 'storey_id' in element:
            storey = self.properties['elements'].get(str(element['storey_id']))
            if storey and storey.get('type') == 'IfcBuildingStorey':
                print(f"Found direct storey_id: {storey.get('name', 'Unknown')}")
                return storey.get('name', 'Unknown')
        
        # If not, try to find the storey through the parent chain
        current = element
        while current and 'parent_id' in current:
            parent = self.properties['elements'].get(str(current['parent_id']))
            if not parent:
                break
            
            print(f"Checking parent: {parent.get('type')}")
            
            # If we found a storey, return its name
            if parent.get('type') == 'IfcBuildingStorey':
                print(f"Found storey in parent chain: {parent.get('name', 'Unknown')}")
                return parent.get('name', 'Unknown')
            
            # If parent has a storey_id, use that
            if 'storey_id' in parent:
                storey = self.properties['elements'].get(str(parent['storey_id']))
                if storey and storey.get('type') == 'IfcBuildingStorey':
                    print(f"Found storey_id in parent: {storey.get('name', 'Unknown')}")
                    return storey.get('name', 'Unknown')
            
            current = parent
        
        # For doors and windows, try to find a containing space
        if element.get('type') in ['IfcDoor', 'IfcWindow']:
            print(f"Looking for containing space for {element.get('type')}")
            # Get the element's geometry
            geometry = self.get_geometry(str(element_id))
            if geometry and 'vertices' in geometry:
                # Use the first vertex as a reference point
                ref_point = geometry['vertices'][0]
                print(f"Reference point: {ref_point}")
                
                # Check all spaces to find one that contains this point
                space_ids = self.by_type_index.get('IfcSpace', [])
                print(f"Found {len(space_ids)} spaces to check")
                
                for space_id in space_ids:
                    space = self.properties['elements'].get(str(space_id))
                    if not space or 'storey_id' not in space:
                        continue
                    
                    space_geometry = self.get_geometry(str(space_id))
                    if not space_geometry or 'vertices' not in space_geometry:
                        continue
                    
                    # Get the space's bounds
                    x_coords = [v[0] for v in space_geometry['vertices']]
                    y_coords = [v[1] for v in space_geometry['vertices']]
                    
                    # Check if the reference point is within the space's bounds
                    if (min(x_coords) <= ref_point[0] <= max(x_coords) and
                        min(y_coords) <= ref_point[1] <= max(y_coords)):
                        # Found a containing space, get its storey
                        storey = self.properties['elements'].get(str(space['storey_id']))
                        if storey and storey.get('type') == 'IfcBuildingStorey':
                            print(f"Found containing space in storey: {storey.get('name', 'Unknown')}")
                            return storey.get('name', 'Unknown')
        
        # If we still haven't found a storey, try to find a wall that contains this element
        if element.get('type') in ['IfcDoor', 'IfcWindow']:
            print(f"Looking for containing wall for {element.get('type')}")
            # Get the element's geometry
            geometry = self.get_geometry(str(element_id))
            if geometry and 'vertices' in geometry:
                # Use the first vertex as a reference point
                ref_point = geometry['vertices'][0]
                
                # Check all walls to find one that contains this point
                wall_ids = self.by_type_index.get('IfcWall', [])
                print(f"Found {len(wall_ids)} walls to check")
                
                for wall_id in wall_ids:
                    wall = self.properties['elements'].get(str(wall_id))
                    if not wall or 'storey_id' not in wall:
                        continue
                    
                    wall_geometry = self.get_geometry(str(wall_id))
                    if not wall_geometry or 'vertices' not in wall_geometry:
                        continue
                    
                    # Get the wall's bounds
                    x_coords = [v[0] for v in wall_geometry['vertices']]
                    y_coords = [v[1] for v in wall_geometry['vertices']]
                    
                    # Check if the reference point is within the wall's bounds
                    if (min(x_coords) <= ref_point[0] <= max(x_coords) and
                        min(y_coords) <= ref_point[1] <= max(y_coords)):
                        # Found a containing wall, get its storey
                        storey = self.properties['elements'].get(str(wall['storey_id']))
                        if storey and storey.get('type') == 'IfcBuildingStorey':
                            print(f"Found containing wall in storey: {storey.get('name', 'Unknown')}")
                            return storey.get('name', 'Unknown')
        
        print(f"Could not find storey for element {element_id}")
        return None
