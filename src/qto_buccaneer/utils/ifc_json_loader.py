# TODO make it work with the data from Microservice

from typing import Dict, List, Optional, Any, Union
import pandas as pd
import json
from pathlib import Path
import numpy as np

class IfcJsonLoader:
    """A class to load and manage IFC data from JSON files or pre-loaded JSON data.
    
    This class provides methods to access geometry and properties data from IFC models
    that have been converted to JSON format. It can handle multiple geometry files or
    pre-loaded JSON data.
    """

    # TODO:get_elements_by_type should be the template for the other methods return a pd.DataFrame
    
    def __init__(self, 
                 json_paths: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
                 properties_json: Optional[dict] = None):
        """
        Initialize the loader.
        
        Args:
            json_paths: Optional path or list of paths to IFC JSON files
            properties_json: Optional pre-loaded properties JSON data
        """
        if json_paths is not None:
            # Convert single path to list
            if isinstance(json_paths, (str, Path)):
                json_paths = [json_paths]
                
            self.json_paths = [Path(p) for p in json_paths]
            self.data = self._load_jsons()
        elif properties_json is not None:
            self.json_paths = None
            self.data = properties_json
        else:
            raise ValueError("Either json_paths or properties_json must be provided")
            
        self.elements = self._process_elements()
        self._geometry_loaded = False
        
    def add_geometry_files(self, json_paths: Union[str, Path, List[Union[str, Path]]]) -> None:
        """Add additional geometry files to the loader.
        
        Args:
            json_paths: Path or list of paths to additional IFC JSON files
        """
        if self.json_paths is None:
            raise ValueError("Cannot add geometry files when initialized with properties_json")
            
        # Convert single path to list
        if isinstance(json_paths, (str, Path)):
            json_paths = [json_paths]
            
        new_paths = [Path(p) for p in json_paths]
        self.json_paths.extend(new_paths)
        
        # Load new data
        new_data = self._load_jsons_from_paths(new_paths)
        
        # Update existing data
        if isinstance(self.data, list):
            self.data.extend(new_data)
        else:
            self.data = [self.data] + new_data
            
        # Reprocess elements to include new geometry
        self.elements = self._process_elements()
        self._geometry_loaded = False
        
    def _load_jsons_from_paths(self, paths: List[Path]) -> List[dict]:
        """Load JSON files from specific paths."""
        all_data = []
        for path in paths:
            with open(path, 'r') as f:
                all_data.extend(json.load(f))
        return all_data
        
    def _load_jsons(self) -> List[dict]:
        """Load all JSON files."""
        return self._load_jsons_from_paths(self.json_paths)
            
    def _process_elements(self) -> Dict[str, dict]:
        """Process elements from all JSON data."""
        elements = {}
        
        # Handle both list and dict input
        data_list = self.data if isinstance(self.data, list) else [self.data]
        
        for element in data_list:
            element_id = element.get('ifc_global_id')
            if not element_id:
                continue
                
            # Basic properties
            element_data = {
                'id': element.get('id'),
                'type': element.get('ifc_type'),
                'vertices': np.array(element.get('vertices', [])),
                'faces': np.array(element.get('faces', []))
            }
                
            # If element already exists, merge geometry data
            if element_id in elements:
                existing = elements[element_id]
                # Combine vertices and faces
                existing['vertices'] = np.vstack((existing['vertices'], element_data['vertices']))
                existing['faces'] = np.vstack((existing['faces'], element_data['faces']))
            else:
                elements[element_id] = element_data
            
        return elements
        
    def load_geometry(self) -> None:
        """Load geometry data for all elements from all files."""
        if self._geometry_loaded:
            return
            
        # Handle both list and dict input
        data_list = self.data if isinstance(self.data, list) else [self.data]
            
        for element in data_list:
            element_id = element.get('ifc_global_id')
            if not element_id:
                continue
                
            geometry = self._extract_geometry(element)
            if geometry:
                if 'geometry' not in self.elements[element_id]:
                    self.elements[element_id]['geometry'] = geometry
                else:
                    # Merge geometry data
                    existing = self.elements[element_id]['geometry']
                    existing['vertices'] = np.vstack((existing['vertices'], geometry['vertices']))
                    existing['faces'] = np.vstack((existing['faces'], geometry['faces']))
                
        self._geometry_loaded = True
        
    def load_geometry_for_element(self, element_id: str) -> None:
        """Load geometry data for a specific element from all files."""
        if element_id not in self.elements:
            return
            
        # Handle both list and dict input
        data_list = self.data if isinstance(self.data, list) else [self.data]
            
        elements = [
            e for e in data_list 
            if e.get('ifc_global_id') == element_id
        ]
        
        for element in elements:
            geometry = self._extract_geometry(element)
            if geometry:
                if 'geometry' not in self.elements[element_id]:
                    self.elements[element_id]['geometry'] = geometry
                else:
                    # Merge geometry data
                    existing = self.elements[element_id]['geometry']
                    existing['vertices'] = np.vstack((existing['vertices'], geometry['vertices']))
                    existing['faces'] = np.vstack((existing['faces'], geometry['faces']))
                
    def _extract_geometry(self, element: dict) -> Optional[dict]:
        """Extract geometry data from an element."""
        vertices = element.get('vertices')
        faces = element.get('faces')
        if not vertices or not faces:
            return None
            
        return {
            'vertices': np.array(vertices),
            'faces': np.array(faces)
        }
        
    def get_element(self, global_id: str, load_geometry: bool = False) -> Optional[dict]:
        """Get an element by its GlobalId.
        
        Args:
            global_id: The GlobalId of the element
            load_geometry: Whether to load geometry data if not already loaded
        """
        if load_geometry and not self._geometry_loaded:
            self.load_geometry_for_element(global_id)
            
        return self.elements.get(global_id)
        
    def get_elements_by_type(self, ifc_entity: str) -> pd.DataFrame:
        """Get all element IDs for a given IFC entity type.
        
        Args:
            ifc_entity: The IFC entity type to filter by (e.g., "IfcSpace")
            
        Returns:
            DataFrame containing element IDs and their metadata
        """
        elements_data = []
        
        # Handle both list and dict input
        data_list = self.data if isinstance(self.data, list) else [self.data]
        
        for data in data_list:
            # Get elements from the nested structure
            elements = data.get('elements', {})
            
            for element_id, element in elements.items():
                if element.get('IfcEntity') == ifc_entity:
                    # Create a dictionary with all available data
                    element_data = {}
                    
                    # Add all fields from the element except geometry data
                    for key, value in element.items():
                        # Skip geometry-related fields
                        if key in ['vertices', 'faces', 'geometry']:
                            continue
                            
                        # Handle nested properties
                        if isinstance(value, dict):
                            # Special handling for Qto_SpaceBaseQuantities
                            if key == 'Qto_SpaceBaseQuantities':
                                for nested_key, nested_value in value.items():
                                    new_key = f"{key}.{nested_key}"
                                    element_data[new_key] = nested_value
                            else:
                                for nested_key, nested_value in value.items():
                                    new_key = f"{key}.{nested_key}"
                                    element_data[new_key] = nested_value
                        else:
                            element_data[key] = value
                    
                    # Find storey by traversing up the parent chain
                    current_id = element.get('parent_id')
                    storey_name = 'Unknown'
                    
                    while current_id is not None:
                        current = elements.get(str(current_id))
                        if not current:
                            break
                            
                        if current.get('IfcEntity') == 'IfcBuildingStorey':
                            storey_name = current.get('Name', 'Unknown')
                            break
                            
                        current_id = current.get('parent_id')
                    
                    element_data['BuildingStorey'] = storey_name
                    elements_data.append(element_data)
        
        df = pd.DataFrame(elements_data)
        print("\n=== DataFrame Columns ===")
        print(f"Available columns: {df.columns.tolist()}")
        return df
        
    def get_elements_with_property(self, property_name: str, value: Union[str, float, int], load_geometry: bool = False) -> List[dict]:
        """Get elements with a specific property value.
        
        Args:
            property_name: The name of the property to check
            value: The value to match
            load_geometry: Whether to load geometry data if not already loaded
        """
        if load_geometry and not self._geometry_loaded:
            self.load_geometry()
            
        return [
            element for element in self.elements.values()
            if element['properties'].get(property_name) == value
        ]
        
    def get_elements_with_quantity(self, quantity_name: str, min_value: float = None, max_value: float = None, load_geometry: bool = False) -> List[dict]:
        """Get elements with a quantity within a range.
        
        Args:
            quantity_name: The name of the quantity to check
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            load_geometry: Whether to load geometry data if not already loaded
        """
        if load_geometry and not self._geometry_loaded:
            self.load_geometry()
            
        elements = []
        for element in self.elements.values():
            quantity = element['quantities'].get(quantity_name)
            if quantity is None:
                continue
                
            if min_value is not None and quantity < min_value:
                continue
            if max_value is not None and quantity > max_value:
                continue
                
            elements.append(element)
            
        return elements

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
