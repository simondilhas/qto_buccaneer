import ifcopenshell
import os
from typing import List, Optional, Any, Dict, Union, Literal
from ifcopenshell.entity_instance import entity_instance
import pandas as pd
import time

IfcElement = Any

class IfcError(Exception):
    """Base exception for IFC-related errors"""
    pass

class IfcFileNotFoundError(IfcError):
    """Raised when the IFC file cannot be found"""
    pass

class IfcInvalidFileError(IfcError):
    """Raised when the file is not a valid IFC file"""
    pass


class IfcLoader:
    def __init__(self, model_or_path: Union[str, 'ifcopenshell.file']):
        """Initialize an IFC project from a file path or model.

        Args:
            model_or_path: Either a path to an IFC file (str) or an already loaded IFC model
        
        Raises:
            IfcFileNotFoundError: If a file path is provided and cannot be found
            IfcInvalidFileError: If the file path provided is not a valid IFC file
        """
        if isinstance(model_or_path, str):
            self.file_path = model_or_path
            
            # Check if file exists
            if not os.path.exists(model_or_path):
                raise IfcFileNotFoundError(f"IFC file not found: {model_or_path}")
            
            try:
                self.model = ifcopenshell.open(model_or_path)
            except Exception as e:
                raise IfcInvalidFileError(f"Could not open {model_or_path} as an IFC file: {str(e)}")
        else:
            self.file_path = None
            self.model = model_or_path

    def get_property_value(self, element, set_name: str, prop_name: str) -> Optional[Any]:
        """
        Retrieves the value of a property or quantity from a specified Pset or Qset.
        Supports both IfcPropertySet and IfcElementQuantity.

        Args:
            element: The IFC element to extract the property from.
            set_name (str): The name of the property set or quantity set (e.g. "Pset_SpaceCommon", "Qto_SpaceBaseQuantities").
            prop_name (str): The name of the property or quantity (e.g. "IsExternal", "NetFloorArea").

        Returns:
            The unwrapped property value if found, otherwise None.
        """
        if element is None or not hasattr(element, "IsDefinedBy"):
            return None

        for definition in element.IsDefinedBy:
            if not hasattr(definition, "RelatingPropertyDefinition"):
                continue

            prop_def = definition.RelatingPropertyDefinition
            if prop_def is None:
                continue

            # Process property sets
            if prop_def.is_a("IfcPropertySet") and prop_def.Name == set_name:
                for prop in getattr(prop_def, "HasProperties", []):
                    if prop.Name == prop_name:
                        if hasattr(prop, "NominalValue"):
                            val = prop.NominalValue
                            if hasattr(val, "wrappedValue"):
                                return val.wrappedValue
                            return val
                        elif hasattr(prop, "Value"):  # For simple props
                            val = prop.Value
                            if hasattr(val, "wrappedValue"):
                                return val.wrappedValue
                            return val

            # Process quantity sets
            elif prop_def.is_a("IfcElementQuantity") and prop_def.Name == set_name:
                for quantity in getattr(prop_def, "Quantities", []):
                    if quantity.Name == prop_name:
                        if quantity.is_a("IfcQuantityArea"):
                            val = quantity.AreaValue
                        elif quantity.is_a("IfcQuantityVolume"):
                            val = quantity.VolumeValue
                        elif quantity.is_a("IfcQuantityLength"):
                            val = quantity.LengthValue
                        elif quantity.is_a("IfcQuantityCount"):
                            val = quantity.CountValue
                        elif quantity.is_a("IfcQuantityWeight"):
                            val = quantity.WeightValue
                        elif hasattr(quantity, "NominalValue"):
                            val = quantity.NominalValue
                        else:
                            val = None

                        if hasattr(val, "wrappedValue"):
                            return val.wrappedValue
                        return val

        return None


    def get_property_sets(self, element) -> Dict[str, Dict[str, Any]]:
        """
        Get all property sets for an element with their properties.
        
        Args:
            element: The IFC element
            
        Returns:
            Dictionary of property sets with their properties
            
        Example:
            >>> loader = IfcLoader("house.ifc")
            >>> wall = loader.model.by_type("IfcWall")[0]
            >>> property_sets = loader.get_property_sets(wall)
            >>> for pset_name, properties in property_sets.items():
            >>>     print(f"Property Set: {pset_name}")
            >>>     for prop_name, value in properties.items():
            >>>         print(f"  {prop_name}: {value}")
        """
        result = {}
        
        if not hasattr(element, "IsDefinedBy"):
            return result
            
        for definition in element.IsDefinedBy:
            if not hasattr(definition, "RelatingPropertyDefinition"):
                continue
                
            prop_def = definition.RelatingPropertyDefinition
            if prop_def is None:
                continue
                
            # Process property sets
            if prop_def.is_a("IfcPropertySet"):
                pset_name = prop_def.Name
                properties = {}
                
                for prop in getattr(prop_def, "HasProperties", []):
                    if hasattr(prop, "NominalValue"):
                        properties[prop.Name] = prop.NominalValue
                    elif hasattr(prop, "Value"):
                        properties[prop.Name] = prop.Value
                        
                result[pset_name] = properties
                
            # Process quantity sets
            elif prop_def.is_a("IfcElementQuantity"):
                qset_name = prop_def.Name
                quantities = {}
                
                for quantity in getattr(prop_def, "Quantities", []):
                    if quantity.is_a("IfcQuantityArea"):
                        quantities[quantity.Name] = quantity.AreaValue
                    elif quantity.is_a("IfcQuantityVolume"):
                        quantities[quantity.Name] = quantity.VolumeValue
                    elif quantity.is_a("IfcQuantityLength"):
                        quantities[quantity.Name] = quantity.LengthValue
                    elif quantity.is_a("IfcQuantityCount"):
                        quantities[quantity.Name] = quantity.CountValue
                    elif quantity.is_a("IfcQuantityWeight"):
                        quantities[quantity.Name] = quantity.WeightValue
                        
                result[qset_name] = quantities
                
        return result

    def get_elements(
        self,
        filters: Optional[dict] = None,
        filter_logic: Literal["AND", "OR"] = "AND",
        ifc_entity: str = None
    ) -> List[Any]:
        """Get elements from the IFC file that match the given filters.
        
        Args:
            filters: Dictionary of property filters
            filter_logic: How to combine filters ("AND" or "OR")
            ifc_entity: IFC entity type to filter for (e.g., "IfcSpace", "IfcWall")
        
        Returns:
            List of matching IFC elements
        """
        # Get all elements of the specified type
        if ifc_entity:
            elements = self.model.by_type(ifc_entity)
        else:
            elements = self.model.by_type("IfcProduct")
        
        # If no filters, return all elements
        if not filters:
            return elements
        
        # Filter elements
        filtered_elements = []
        for element in elements:
            matches = []
            
            for key, value in filters.items():
                # Handle direct attribute comparison
                if not "." in key:
                    element_value = getattr(element, key, None)
                    matches.append(self._compare_values(element_value, value))
                    continue
                
                # Handle property set values
                pset_name, prop_name = key.split(".")
                prop_value = None
                
                # Check IfcPropertySet and IfcElementQuantity
                for rel in getattr(element, "IsDefinedBy", []):
                    definition = getattr(rel, "RelatingPropertyDefinition", None)
                    if not definition:
                        continue
                        
                    if definition.is_a("IfcPropertySet") and definition.Name == pset_name:
                        for prop in definition.HasProperties:
                            if prop.Name == prop_name:
                                prop_value = getattr(prop, "NominalValue", None)
                                if prop_value:
                                    prop_value = prop_value.wrappedValue
                                break
                
                    # Check IfcElementQuantity
                    elif definition.is_a("IfcElementQuantity") and definition.Name == pset_name:
                        for quantity in definition.Quantities:
                            if quantity.Name == prop_name:
                                if quantity.is_a("IfcQuantityArea"):
                                    prop_value = quantity.AreaValue
                                elif quantity.is_a("IfcQuantityLength"):
                                    prop_value = quantity.LengthValue
                                elif quantity.is_a("IfcQuantityVolume"):
                                    prop_value = quantity.VolumeValue
                                break
                
                matches.append(self._compare_values(prop_value, value))
            
            # Add element if it matches according to filter logic
            if filter_logic == "AND" and all(matches):
                filtered_elements.append(element)
            elif filter_logic == "OR" and any(matches):
                filtered_elements.append(element)
        
        return filtered_elements

    def _compare_values(self, actual_value: Any, filter_value: Any) -> bool:
        # Handle string operators like "<=0.15"
        if isinstance(filter_value, str):
            operators = [">=", "<=", "!=", "=", ">", "<"]
            for op in operators:
                if filter_value.startswith(op):
                    try:
                        value = float(filter_value[len(op):])
                        actual_value = float(actual_value)
                        return {
                            ">": actual_value > value,
                            "<": actual_value < value,
                            "=": actual_value == value,
                            "!=": actual_value != value,
                            "<=": actual_value <= value,
                            ">=": actual_value >= value
                        }[op]
                    except (TypeError, ValueError):
                        return False
        
        # Handle list with operator and value
        elif isinstance(filter_value, list) and len(filter_value) == 2:
            operator, value = filter_value
            try:
                actual_value = float(actual_value)
                value = float(value)
                return {
                    ">": actual_value > value,
                    "<": actual_value < value,
                    "=": actual_value == value,
                    "!=": actual_value != value,
                    "<=": actual_value <= value,
                    ">=": actual_value >= value
                }[operator]
            except (TypeError, ValueError):
                return False
        # Handle regular list membership
        elif isinstance(filter_value, list):
            return actual_value in filter_value
        
        return actual_value == filter_value

    def get_project_info(self) -> dict:
        """
        Get project information from IFC file.
        
        Returns:
            dict: Project information including name, number, phase etc.
        """
        project = self.model.by_type("IfcProject")[0]
        return {
            "project_name": getattr(project, "Name", "Unknown"),
            "project_number": getattr(project, "GlobalId", "Unknown"),
            "project_phase": getattr(project, "Phase", "Unknown"),
            "project_status": getattr(project, "Status", "Unknown")
        }

    def get_space_information(self, ifc_entity: str = "IfcSpace") -> pd.DataFrame:
        """
        Get space information from IFC file and return it as a DataFrame.
        
        Args:
            ifc_entity (str): The IFC entity type to query (default: "IfcSpace")
            
        Returns:
            pd.DataFrame: Element information including:
                - Direct attributes (e.g., Name, GlobalId)
                - Property set values (columns named as 'PsetName.PropertyName')
                - Quantity set values (columns named as 'QsetName.QuantityName')
        """
        elements = self.model.by_type(ifc_entity)
        
        # Initialize empty list to store data
        data = []
        
        for element in elements:
            # Get basic attributes
            element_data = {
                'GlobalId': getattr(element, "GlobalId", None),
                'Name': getattr(element, "Name", None),
                'LongName': getattr(element, "LongName", None),
                'Description': getattr(element, "Description", None),
                'ObjectType': getattr(element, "ObjectType", None),
                'IFC_ENTITY_TYPE': element.is_a()  # This gets the IFC entity type
            }
            
            # Get property and quantity sets
            psets = self.get_property_sets(element)
            
            # Add properties and quantities with combined names
            for set_name, properties in psets.items():
                for prop_name, value in properties.items():
                    # Handle wrapped values
                    if hasattr(value, "wrappedValue"):
                        value = value.wrappedValue
                    column_name = f"{set_name}.{prop_name}"
                    element_data[column_name] = value
            
            data.append(element_data)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        return df

    def get_element_spatial_relationship(self, ifc_entity: Optional[str] = None) -> pd.DataFrame:
        """
        Get spatial information for IFC elements, including both contained elements (through
        IfcRelContainedInSpatialStructure) and aggregated elements like spaces (through IfcRelAggregates).
        
        Args:
            ifc_entity (Optional[str]): Optional filter for specific IFC entity types
            
        Returns:
            pd.DataFrame: DataFrame containing element GlobalIds and their associated stories/elevations
        """
        print("Start")
        
        data = {
            'GlobalId': [],
            'BuildingStory': [],
            'ElevationOfStory': []
        }
        
        try:
            connected_elements = set()  # Use set to avoid duplicates
            stories = self.model.by_type("IfcBuildingStorey")
            print(f"Found {len(stories)} stories")
            
            for story in stories:
                # Get all relationships where this story is the container
                for rel in self.model.get_inverse(story):
                    # Handle contained elements (walls, doors, etc)
                    if rel.is_a('IfcRelContainedInSpatialStructure'):
                        elements = rel.RelatedElements
                    # Handle aggregated elements (typically spaces)
                    elif rel.is_a('IfcRelAggregates'):
                        elements = rel.RelatedObjects
                    else:
                        continue
                    
                    # Process all elements from the relationship
                    for element in elements:
                        # If specific entity type is requested, filter for it
                        if ifc_entity is None or element.is_a(ifc_entity):
                            connected_elements.add(element)
                            data['GlobalId'].append(element.GlobalId)
                            data['BuildingStory'].append(story.Name)
                            data['ElevationOfStory'].append(float(getattr(story, "Elevation", 0.0)))
            
            print(f"Found {len(connected_elements)} elements connected to stories")
            
            df = pd.DataFrame(data)
            print(f"DataFrame shape: {df.shape}")
            return df
            
        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame(columns=list(data.keys()))

   
