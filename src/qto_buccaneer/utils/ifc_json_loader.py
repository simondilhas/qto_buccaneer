from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
import pandas as pd
from qto_buccaneer.utils.metadata_filter import MetadataFilter
class IfcJsonLoader:
    """A class to load and manage IFC data from JSON files.

    This class provides methods to access geometry and properties data from IFC models
    that have been converted to JSON format.
    """

    def __init__(self, properties_json: Union[str, Path], json_paths: Optional[Union[str, Path]] = None):
        """Initialize the loader with paths to geometry and properties data.
        
        Args:
            properties_json: Path to properties JSON file
            json_paths: Optional path to directory containing geometry JSON files
        """
        # Convert paths to Path objects
        self.properties_json = Path(properties_json)
        self.json_paths = Path(json_paths) if json_paths else None

        # Load properties data
        print(f"\nLoading properties data from {self.properties_json}...")
        with open(self.properties_json, 'r') as f:
            self.properties = json.load(f)
            elements = self.properties.get('elements', {})
            print(f"  - Loaded {len(elements)} elements")
        
        # Create a simple index of elements by type
        self.by_type_index = {}
        for elem_id, elem in elements.items():
            if isinstance(elem, dict):
                ifc_type = elem.get("IfcEntity")
                if ifc_type:
                    if ifc_type not in self.by_type_index:
                        self.by_type_index[ifc_type] = []
                    self.by_type_index[ifc_type].append(elem_id)
        
        print("\nElements by type:")
        for ifc_type, ids in self.by_type_index.items():
            print(f"  - {ifc_type}: {len(ids)} elements")
        
        # Cache for loaded geometry files
        self._geometry_cache = {}
        
        # Only build element cache if we have geometry paths
        if self.json_paths:
            self._element_cache: Dict[str, Dict[str, Any]] = {}
            self._build_element_cache()
            print(f"\nCreated element cache with {len(self._element_cache)} entries")

    def _build_element_cache(self):
        """Build a cache of elements with their properties and geometry."""
        print("\nBuilding element cache...")
        
        # Process all elements
        for elem_id, elem in self.properties.get("elements", {}).items():
            if not isinstance(elem, dict):
                continue
                
            # Get basic element info
            ifc_type = elem.get("IfcEntity")
            if not ifc_type:
                continue
                
            # Get geometry (but don't skip if not found)
            geometry = self.get_geometry(elem_id)
            
            # Create cache entry
            cache_entry = {
                "id": elem_id,
                "type": ifc_type,
                "name": elem.get("Name", "Unknown"),
                "parent_id": elem.get("parent_id"),
                "properties": elem,
                "geometry": geometry
            }
            self._element_cache[elem_id] = cache_entry
            
            # Print some debug info for storeys and spaces
            if ifc_type == "IfcBuildingStorey":
                print(f"Found storey: {cache_entry['name']} (ID: {elem_id})")
            elif ifc_type == "IfcSpace":
                parent = self.properties.get("elements", {}).get(str(cache_entry["parent_id"]), {})
                parent_name = parent.get("Name", "Unknown")
                print(f"Found space: {cache_entry['name']} (ID: {elem_id}) in storey: {parent_name}")
        
        # Print summary
        print("\nElement cache summary:")
        type_counts = {}
        for entry in self._element_cache.values():
            ifc_type = entry["type"]
            type_counts[ifc_type] = type_counts.get(ifc_type, 0) + 1
        
        for ifc_type, count in type_counts.items():
            print(f"  - {ifc_type}: {count} elements")
        
        # Print geometry matching statistics
        print("\nGeometry matching statistics:")
        total_elements = len(self._element_cache)
        print(f"  - Total elements with geometry: {total_elements}")
        
        # Print by_type index statistics
        print("\nBy_type index statistics:")
        for ifc_type, ids in self.by_type_index.items():
            elements_with_geo = sum(1 for elem_id in ids if self._element_cache.get(str(elem_id)))
            print(f"  - {ifc_type}: {len(ids)} elements total, {elements_with_geo} with geometry")

    def get_elements_by_type(self, ifc_type: str) -> List[Dict[str, Any]]:
        """Get all elements of a specific IFC type.
        
        Args:
            ifc_type: The IFC type to filter by (e.g., "IfcSpace", "IfcBuildingStorey")
            
        Returns:
            List of element dictionaries with their properties and geometry (if available)
        """
        # Get all elements of the specified type from properties
        elements = [
            {"id": elem_id, "type": ifc_type, **elem}
            for elem_id, elem in self.properties.get('elements', {}).items()
            if isinstance(elem, dict) and elem.get("IfcEntity") == ifc_type
        ]
        
        # If we have geometry data, add it to the elements
        if hasattr(self, '_element_cache'):
            for elem in elements:
                cache_entry = self._element_cache.get(elem["id"])
                if cache_entry and "geometry" in cache_entry:
                    elem["geometry"] = cache_entry["geometry"]
        
        return elements

    def get_spaces_in_storey(self, storey_name: str) -> List[str]:
        """Return a list of space IDs in a given storey.
        
        Args:
            storey_name: Name of the storey to filter spaces by
            
        Returns:
            List of space IDs in the specified storey
        """
        # First find the storey ID
        storey_id = None
        for entry in self._element_cache.values():
            if entry["type"] == "IfcBuildingStorey" and entry["name"] == storey_name:
                storey_id = entry["id"]
                break
        
        if not storey_id:
            print(f"Storey '{storey_name}' not found")
            return []
        
        # Find all spaces with this storey as parent
        space_ids = []
        for entry in self._element_cache.values():
            if entry["type"] == "IfcSpace" and entry["parent_id"] == storey_id:
                space_ids.append(entry["id"])
        
        return space_ids

    def get_storey_for_space(self, space_id: str) -> Optional[str]:
        """Get the storey name for a given space.
        
        Args:
            space_id: The ID of the space
            
        Returns:
            The storey name, or None if not found
        """
        space_entry = self._element_cache.get(space_id)
        if not space_entry or space_entry["type"] != "IfcSpace":
            return None
            
        parent_id = space_entry["parent_id"]
        if not parent_id:
            return None
            
        parent_entry = self._element_cache.get(parent_id)
        if not parent_entry or parent_entry["type"] != "IfcBuildingStorey":
            return None
            
        return parent_entry["name"]

    def get_geometry(self, elem_id: str) -> Optional[Dict[str, Any]]:
        """Get geometry for a given element ID.
        
        Args:
            elem_id: The ID of the element
            
        Returns:
            Geometry data for the element, or None if not found
        """
        # Get the element's type from metadata
        element = self.properties.get('elements', {}).get(str(elem_id))
        if not element or not isinstance(element, dict):
            print(f"Warning: Element {elem_id} not found in metadata")
            return None
            
        ifc_type = element.get("IfcEntity")
        if not ifc_type:
            print(f"Warning: Element {elem_id} has no IfcEntity type")
            return None
            
        # Check if we already have this geometry file loaded
        if ifc_type not in self._geometry_cache:
            geometry_file = self.json_paths / f"{ifc_type}.json"
            if not geometry_file.exists():
                print(f"Warning: No geometry file found for {ifc_type}")
                return None
                
            print(f"Loading geometry from {geometry_file}")
            with open(geometry_file, 'r') as f:
                geometry_data = json.load(f)
                if not isinstance(geometry_data, list):
                    print(f"Warning: {geometry_file.name} does not contain a list of elements")
                    return None
                    
                # Create a dictionary for quick lookup by ID
                self._geometry_cache[ifc_type] = {
                    str(item["id"]): item 
                    for item in geometry_data 
                    if "id" in item and "vertices" in item and "polygons" in item
                }
                print(f"  - Loaded {len(geometry_data)} elements")
        
        # Get geometry from cache
        return self._geometry_cache[ifc_type].get(str(elem_id))

    def get_geometry_by_list(self, elem_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get geometry for multiple elements efficiently.
        
        Args:
            elem_ids: List of element IDs to get geometry for
            
        Returns:
            Dictionary mapping element IDs to their geometry data. Elements not found
            will have None as their value.
            
        Example:
            >>> geometries = ifc.get_geometry_by_list(['123', '456'])
            >>> print(geometries['123'])  # Geometry data for element 123
            >>> print(geometries['456'])  # Geometry data for element 456
        """
        if not self.json_paths:
            print("Warning: No geometry path provided. Cannot load geometry files.")
            return {elem_id: None for elem_id in elem_ids}
            
        # Get unique IFC types for the requested elements
        ifc_types = set()
        for elem_id in elem_ids:
            element = self.properties.get('elements', {}).get(str(elem_id))
            if element and isinstance(element, dict):
                ifc_type = element.get("IfcEntity")
                if ifc_type:
                    ifc_types.add(ifc_type)
        
        # Load geometry files for each type if not already loaded
        for ifc_type in ifc_types:
            if ifc_type not in self._geometry_cache:
                geometry_file = self.json_paths / f"{ifc_type}.json"
                if not geometry_file.exists():
                    print(f"Warning: No geometry file found for {ifc_type}")
                    continue
                    
                print(f"Loading geometry from {geometry_file}")
                with open(geometry_file, 'r') as f:
                    geometry_data = json.load(f)
                    if not isinstance(geometry_data, list):
                        print(f"Warning: {geometry_file.name} does not contain a list of elements")
                        continue
                        
                    # Create a dictionary for quick lookup by ID
                    self._geometry_cache[ifc_type] = {
                        str(item["id"]): item 
                        for item in geometry_data 
                        if "id" in item and "vertices" in item and "polygons" in item
                    }
                    print(f"  - Loaded {len(geometry_data)} elements")
        
        # Get geometry for each element
        result = {}
        for elem_id in elem_ids:
            element = self.properties.get('elements', {}).get(str(elem_id))
            if not element or not isinstance(element, dict):
                result[elem_id] = None
                continue
                
            ifc_type = element.get("IfcEntity")
            if not ifc_type or ifc_type not in self._geometry_cache:
                result[elem_id] = None
                continue
                
            result[elem_id] = self._geometry_cache[ifc_type].get(str(elem_id))
        
        return result

    def get_properties(self, guid: str) -> Optional[Dict[str, Any]]:
        """Get properties for a given ID.
        
        Args:
            guid: The ID of the element to get properties for
            
        Returns:
            Properties data for the element, or None if not found
        """
        return self.properties_index.get(guid)
    
    def get_metadata_by_type_as_df(self, ifc_type: str) -> pd.DataFrame:
        """Get all elements of a specific IFC type as a pandas DataFrame.
        
        Args:
            ifc_type: The IFC type to filter by (e.g., "IfcSpace", "IfcBuildingStorey")
            
        Returns:
            A pandas DataFrame containing the elements of the specified IFC type
        """
        elements = self.get_elements_by_type(ifc_type)
        return pd.DataFrame(elements)

    def get_all_elements(self) -> List[Dict[str, Any]]:
        """Get all elements from the IFC JSON data.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing element metadata including:
                - id
                - IfcEntity
                - All properties from the JSON data
                - geometry (if available)
        """
        all_elements = []
        
        # Get all elements of each type
        for ifc_type in self.by_type_index.keys():
            elements = self.get_elements_by_type(ifc_type)
            all_elements.extend(elements)
        
        print(f"\nTotal elements: {len(all_elements)}")
        return all_elements

    def get_elements_by_filter_old(self, filter_expression: str) -> List[Dict[str, Any]]:
        """Get elements matching a filter expression.
        
        Args:
            filter_expression: A string containing the filter expression. Examples:
                - Simple: "IfcEntity=IfcSpace"
                - Multiple values: "IfcEntity=IfcSpace AND (LongName=LUF OR LongName=SPH)"
                - Comparison: "IfcEntity=IfcSpace AND Qto_SpaceBaseQuantities.NetFloorArea>20.0"
                - Complex: "IfcEntity=IfcSpace AND (Qto_SpaceBaseQuantities.NetFloorArea>20.0 OR Qto_SpaceBaseQuantities.NetVolume>100.0)"
                - Boolean: "IfcEntity=IfcSpace AND IsExternal=true"
                - Max value: "IfcEntity=IfcSpace AND max(Qto_SpaceBaseQuantities.NetFloorArea)"
            
        Returns:
            List[Dict[str, Any]]: List of elements matching the filter criteria
        """
        print(f"\nFilter expression: {filter_expression}")
        
        # Parse the filter expression
        filters = MetadataFilter._parse_filter_expression(filter_expression)
        print(f"Parsed filters: {filters}")
        
        # Get all elements
        all_elements = self.get_all_elements()
        print(f"Total elements before filtering: {len(all_elements)}")
        
        # Apply filters directly to the list of dictionaries
        filtered_elements = []
        for elem in all_elements:
            matches = True
            for key, value in filters.items():
                if key not in elem:
                    print(f"Key '{key}' not found in element. Available keys: {sorted(elem.keys())}")
                    matches = False
                    break
                    
                if isinstance(value, list):
                    if value and isinstance(value[0], tuple):
                        # Handle comparison operators
                        elem_matches = False
                        for op, val in value:
                            if op == 'max':
                                continue
                            if MetadataFilter._compare_values(elem[key], op, val):
                                elem_matches = True
                                break
                        if not elem_matches:
                            matches = False
                            break
                    else:
                        # Handle list of values (OR condition)
                        if elem[key] not in value:
                            matches = False
                            break
                else:
                    # Handle single value
                    if elem[key] != value:
                        matches = False
                        break
            
            if matches:
                filtered_elements.append(elem)
        
        print(f"Found {len(filtered_elements)} matching elements")
        return filtered_elements
    
    def get_elements_by_filter(self, filter_expression: str) -> Dict[int, Dict[str, Any]]:
        """Get elements matching a filter expression, including geometry if available.
        Returns a dict of id -> element.
        """
        print(f"\nFilter expression: {filter_expression}")

        filters = MetadataFilter._parse_filter_expression(filter_expression)
        print(f"Parsed filters: {filters}")

        all_elements = self.get_all_elements()
        print(f"Total elements before filtering: {len(all_elements)}")

        filtered_elements = {}  # <-- now a dict, not a list!

        for elem in all_elements:
            matches = True
            for key, value in filters.items():
                if key not in elem:
                    print(f"Key '{key}' not found in element. Available keys: {sorted(elem.keys())}")
                    matches = False
                    break

                if isinstance(value, list):
                    if value and isinstance(value[0], tuple):
                        elem_matches = False
                        for op, val in value:
                            if op == 'max':
                                continue
                            if MetadataFilter._compare_values(elem[key], op, val):
                                elem_matches = True
                                break
                        if not elem_matches:
                            matches = False
                            break
                    else:
                        if elem[key] not in value:
                            matches = False
                            break
                else:
                    if elem[key] != value:
                        matches = False
                        break

            if matches:
                # Now inject geometry if available
                elem_id = elem["id"]
                cached = self._element_cache.get(str(elem_id))
                if cached and "geometry" in cached:
                    elem["geometry"] = cached["geometry"]
                filtered_elements[elem_id] = elem  # <-- save by ID into dict

        print(f"Found {len(filtered_elements)} matching elements")
        return filtered_elements



    def plot_merged_geometry(self, merged_geometry: Dict[str, Any], title: str = "Merged Geometry") -> None:
        """Create a Plotly 3D visualization of merged geometry.
        
        Args:
            merged_geometry: Dictionary containing merged geometry data with 'vertices' and 'faces'
            title: Title for the plot
        """
        try:
            import plotly.graph_objects as go
            import numpy as np
        except ImportError:
            print("Please install plotly and numpy to use this function:")
            print("pip install plotly numpy")
            return

        if not merged_geometry or 'vertices' not in merged_geometry or 'faces' not in merged_geometry:
            print("Invalid geometry data. Must contain 'vertices' and 'faces'.")
            return

        # Extract vertices and faces
        vertices = np.array(merged_geometry['vertices'])
        faces = np.array(merged_geometry['faces'])

        # Create mesh3d object
        mesh = go.Mesh3d(
            x=vertices[:, 0],
            y=vertices[:, 1],
            z=vertices[:, 2],
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            opacity=0.8,
            color='lightblue',
            flatshading=True
        )

        # Create figure
        fig = go.Figure(data=[mesh])

        # Update layout
        fig.update_layout(
            title=title,
            scene=dict(
                aspectmode='data',
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z'
            ),
            showlegend=False
        )

        # Show the plot
        fig.show()
