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
            geometry_json: List of geometry objects, each containing a 'ifc_global_id' and geometry data
            properties_json: Dictionary containing elements and their properties
        """
        self.geometry = geometry_json
        self.properties = properties_json
        
        # Create indexes for faster lookups
        self.geometry_index = {item["ifc_global_id"]: item for item in self.geometry}
        self.properties_index = {elem["ifc_global_id"]: elem for elem in properties_json["elements"].values()}
        
        # Create indexes from metadata
        self.by_type_index = properties_json.get("indexes", {}).get("by_type", {})
        self.global_id_to_id = properties_json.get("global_id_to_id", {})
        
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
                        self._storey_cache[space["ifc_global_id"]] = parent.get("name", "Unknown")
    
    def get_spaces_in_storey(self, storey_name: str) -> List[str]:
        """Return a list of GlobalIds of spaces in a given storey.
        
        Args:
            storey_name: Name of the storey to filter spaces by
            
        Returns:
            List of GlobalIds for spaces in the specified storey
        """
        guids = []
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
            space_storey = self._storey_cache.get(space["ifc_global_id"])
            
            # If no storey info, include the space in all storeys
            if space_storey is None:
                guids.append(space["ifc_global_id"])
                print(f"Found space {space['ifc_global_id']} (no storey info)")
            # Otherwise check if the storey name matches
            elif space_storey == storey_name:
                guids.append(space["ifc_global_id"])
                print(f"Found space {space['ifc_global_id']} in storey {storey_name}")
        
        return guids
    
    def get_geometry(self, guid: str) -> Optional[Dict[str, Any]]:
        """Get geometry for a given GlobalId.
        
        Args:
            guid: The GlobalId of the element to get geometry for
            
        Returns:
            Geometry data for the element, or None if not found
        """
        return self.geometry_index.get(guid)
    
    def get_properties(self, guid: str) -> Optional[Dict[str, Any]]:
        """Get properties for a given GlobalId.
        
        Args:
            guid: The GlobalId of the element to get properties for
            
        Returns:
            Properties data for the element, or None if not found
        """
        # First try direct lookup
        props = self.properties_index.get(guid)
        if props:
            return props
            
        # If not found, try using the global_id_to_id index
        element_id = self.global_id_to_id.get(guid)
        if element_id:
            return self.properties["elements"].get(str(element_id))
            
        return None
    
    def get_storey_for_space(self, guid: str) -> Optional[str]:
        """Get the storey name for a given space.
        
        Args:
            guid: The GlobalId of the space
            
        Returns:
            The storey name, or None if not found
        """
        return self._storey_cache.get(guid)
