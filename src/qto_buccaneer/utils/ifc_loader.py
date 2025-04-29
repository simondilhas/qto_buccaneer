import ifcopenshell
import os
from typing import List, Optional, Any, Dict, Union, Literal
from ifcopenshell.entity_instance import entity_instance
import pandas as pd
import time
from functools import lru_cache
import numpy as np

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
        ifc_entity: str,
        filters: Optional[dict] = None,
        filter_logic: Literal["AND", "OR"] = "AND",
    ) -> List[IfcElement]:
        """Get elements of a specific type with optional filters."""
        elements = self.model.by_type(ifc_entity)
        
        if not filters:
            return elements
            
        print(f"\nFiltering {len(elements)} {ifc_entity} elements with:")
        print(f"Filters: {filters}")
        print(f"Filter logic: {filter_logic}")
        
        filtered_elements = []
        for element in elements:
            matches = []
            for key, value in filters.items():
                # Get the attribute value
                attr_value = getattr(element, key, None)
                print(f"\nElement: {element}")
                print(f"Checking filter {key}: {value}")
                print(f"Element has {key}: {attr_value}")
                
                # Handle different types of filter values
                if isinstance(value, list):
                    # For list values, check if any match
                    if isinstance(value[0], tuple) and len(value[0]) == 2:
                        # Handle comparison operators
                        op, val = value[0]
                        if op == ">":
                            matches.append(attr_value > val)
                        elif op == ">=":
                            matches.append(attr_value >= val)
                        elif op == "<":
                            matches.append(attr_value < val)
                        elif op == "<=":
                            matches.append(attr_value <= val)
                        elif op == "=":
                            matches.append(attr_value == val)
                    else:
                        # For simple list values, check if any match
                        matches.append(attr_value in value)
                else:
                    # For single values, check exact match
                    matches.append(attr_value == value)
            
            # Apply filter logic
            if filter_logic == "AND":
                if all(matches):
                    filtered_elements.append(element)
            else:  # OR
                if any(matches):
                    filtered_elements.append(element)
        
        print(f"Found {len(filtered_elements)} matching elements")
        return filtered_elements

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

    def get_entity_metadata_df(self, ifc_entity: str) -> pd.DataFrame:
        """
        Get metadata for all entities of a type as a DataFrame.
        """
        elements = self.model.by_type(ifc_entity)
        data = []
        for element in elements:
            metadata = self.get_entity_metadata(element)
            data.append(metadata)
        return pd.DataFrame(data)

    def get_entity_geometry_df(self, ifc_entity: str) -> pd.DataFrame:
        """
        Get geometry for all entities of a type as a DataFrame.
        """
        elements = self.model.by_type(ifc_entity)
        data = []
        for element in elements:
            geometry = self.get_entity_geometry(element)
            data.append(geometry)
        return pd.DataFrame(data)

    def get_filtered_elements(self, 
                            ifc_entity: str, 
                            filters: Optional[Dict[str, Any]] = None,
                            logic: Literal["AND", "OR"] = "AND") -> pd.DataFrame:
        """
        Get elements of a type with optional filtering.
        """
        df = self.get_entity_metadata_df(ifc_entity)
        if filters:
            df = IfcFilter.filter_elements(df, filters, logic)
        return df

   
