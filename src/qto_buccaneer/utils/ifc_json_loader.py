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
        
        # Build indexes from the data
        self.by_type_index = {}
        self.global_id_to_id = {}
        
        for elem_id, element in properties_json["elements"].items():
            # Build by_type index
            ifc_entity = element.get("IfcEntity")
            if ifc_entity:
                if ifc_entity not in self.by_type_index:
                    self.by_type_index[ifc_entity] = []
                self.by_type_index[ifc_entity].append(int(elem_id))
            
            # Build global_id to id mapping
            global_id = element.get("GlobalId")
            if global_id:
                self.global_id_to_id[global_id] = elem_id
        
        # Initialize storey cache
        self._storey_cache = {}  # element_id -> storey_name
        self._build_storey_cache()
    
    def _build_storey_cache(self):
        """Build a cache of element_id -> storey_name mappings."""
        # First build storey name lookup
        storey_names = {}
        for storey_id in self.by_type_index.get('IfcBuildingStorey', []):
            storey = self.properties_index.get(str(storey_id))
            if storey:
                storey_names[str(storey_id)] = storey.get('Name', 'Unknown')
        
        print(f"\n=== Building Storey Cache ===")
        print(f"Found {len(storey_names)} storeys with names:")
        for storey_id, name in storey_names.items():
            print(f"  - Storey {storey_id}: {name}")
            storey = self.properties_index.get(str(storey_id))
            print(f"    Full storey data: {storey}")
        
        print("\n=== Building Element -> Storey Mapping ===")
        # First map elements directly contained in storeys
        for storey_id, storey_name in storey_names.items():
            storey = self.properties_index.get(str(storey_id))
            if not storey:
                continue
                
            # Get elements directly contained in this storey
            contained_elements = storey.get('ContainsElements', [])
            if isinstance(contained_elements, str):
                # Handle case where it's a string representation of a list
                contained_elements = [e.strip("'") for e in contained_elements.strip('[]').split(',')]
            
            print(f"\nStorey {storey_name} contains elements:")
            for element_id in contained_elements:
                if element_id:
                    self._storey_cache[str(element_id)] = storey_name
                    element = self.properties_index.get(str(element_id))
                    print(f"  - Element {element_id}:")
                    print(f"    Type: {element.get('IfcEntity', 'Unknown') if element else 'Unknown'}")
                    print(f"    Properties: {element}")
        
        # Then handle elements that might be nested under other elements
        for element_id, element in self.properties_index.items():
            if element_id in self._storey_cache:
                continue
                
            current_id = str(element_id)
            path = []
            while current_id:
                path.append(current_id)
                if current_id in storey_names:
                    self._storey_cache[str(element_id)] = storey_names[current_id]
                    print(f"\nElement {element_id}:")
                    print(f"  Type: {element.get('IfcEntity', 'Unknown')}")
                    print(f"  Parent chain: {' -> '.join(path)}")
                    print(f"  Assigned to storey: {storey_names[current_id]}")
                    break
                current = self.properties_index.get(str(current_id))
                if not current:
                    print(f"\nElement {element_id}:")
                    print(f"  Type: {element.get('IfcEntity', 'Unknown')}")
                    print(f"  Parent chain: {' -> '.join(path)}")
                    print(f"  WARNING: Parent chain broken at {current_id}")
                    break
                # Convert parent_id to string if it exists
                parent_id = current.get('parent_id')
                current_id = str(parent_id) if parent_id is not None else None
                if not current_id:
                    print(f"\nElement {element_id}:")
                    print(f"  Type: {element.get('IfcEntity', 'Unknown')}")
                    print(f"  Parent chain: {' -> '.join(path)}")
                    print(f"  WARNING: No parent_id found for {current_id}")
        
        print(f"\n=== Summary ===")
        print(f"Built storey cache with {len(self._storey_cache)} elements")
        print(f"Elements without storey: {len(self.properties_index) - len(self._storey_cache)}")
        
        # Print space-specific summary
        spaces = [id for id, elem in self.properties_index.items() if elem.get('IfcEntity') == 'IfcSpace']
        spaces_with_storey = [id for id in spaces if id in self._storey_cache]
        print(f"\n=== Spaces Summary ===")
        print(f"Total spaces: {len(spaces)}")
        print(f"Spaces with storey: {len(spaces_with_storey)}")
        print(f"Spaces without storey: {len(spaces) - len(spaces_with_storey)}")
        for space_id in spaces:
            storey = self._storey_cache.get(str(space_id))
            print(f"\nSpace {space_id}:")
            print(f"  Storey: {storey if storey else 'Not found'}")
            space = self.properties_index.get(str(space_id))
            print(f"  Parent ID: {space.get('parent_id', 'None')}")
            print(f"  Properties: {space}")
    
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
            space = self.properties_index.get(str(space_id))
            if not space:
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
        return self._storey_cache.get(str(element_id))
