"""
Geometry Extraction Module for qto_buccaneer Viewer
Handles extraction of Custom_Mesh geometry and QTO properties from IFC elements.
"""

import json
import numpy as np
from scipy.spatial.transform import Rotation
import yaml
from pathlib import Path


class GeometryExtractor:
    """Extracts geometry from Custom_Mesh properties and QTO properties."""
    
    def __init__(self, color_config_path=None):
        """
        Initialize GeometryExtractor with optional color configuration.
        
        Parameters:
        -----------
        color_config_path : str, optional
            Path to YAML file containing color mappings for IFC types
        """
        self.color_map = self._load_color_config(color_config_path) if color_config_path else {}
    
    def _load_color_config(self, config_path):
        """Load color mappings from YAML configuration file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            color_map = {}
            plots = config.get('plots', {})
            
            for plot_name, plot_config in plots.items():
                elements = plot_config.get('elements', [])
                for element in elements:
                    element_filter = element.get('filter', '')
                    color = element.get('color')
                    
                    # Extract IFC type from filter (e.g., "type=IfcWall" -> "IfcWall")
                    if 'type=' in element_filter and color:
                        ifc_type = element_filter.split('type=')[1].split(' ')[0]
                        color_map[ifc_type] = color
            
            return color_map
        except Exception as e:
            print(f"⚠️ Could not load color config: {e}")
            return {}
    
    def get_color_for_element(self, element):
        """
        Get color for an IFC element based on its type.
        
        Parameters:
        -----------
        element : IFC element
            The IFC element to get color for
            
        Returns:
        --------
        str or None
            Hex color code or None if no mapping exists
        """
        ifc_type = element.is_a()
        return self.color_map.get(ifc_type)
    
    @staticmethod
    def extract_custom_mesh_from_entity(entity):
        """Extract Custom_Mesh property from an IFC entity."""
        if not hasattr(entity, 'IsDefinedBy'):
            return None
        for rel in entity.IsDefinedBy:
            if rel.is_a("IfcRelDefinesByProperties"):
                pset = rel.RelatingPropertyDefinition
                if hasattr(pset, 'Name') and pset.Name == "Pset_CustomGeometry":
                    if hasattr(pset, 'HasProperties'):
                        for prop in pset.HasProperties:
                            if hasattr(prop, 'Name') and prop.Name == "Custom_Mesh":
                                if hasattr(prop, 'NominalValue') and prop.NominalValue:
                                    return prop.NominalValue.wrappedValue
        return None

    @staticmethod
    def extract_qto_properties(entity, model):
        """Extracts all QTO properties from IfcElementQuantity sets."""
        qto_props = {}
        
        # Check if the element has geometry
        if not GeometryExtractor.extract_custom_mesh_from_entity(entity):
            return qto_props

        # Extract QTO properties of the main element
        if hasattr(entity, 'IsDefinedBy'):
            for rel in entity.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if pset.is_a("IfcElementQuantity") and hasattr(pset, 'Name') and pset.Name.startswith("Qto_"):
                        if hasattr(pset, 'Quantities'):
                            for qty in pset.Quantities:
                                qty_name = getattr(qty, 'Name', 'Unknown')
                                qty_value = None
                                
                                if qty.is_a('IfcQuantityLength'):
                                    qty_value = getattr(qty, 'LengthValue', None)
                                elif qty.is_a('IfcQuantityArea'):
                                    qty_value = getattr(qty, 'AreaValue', None)
                                elif qty.is_a('IfcQuantityVolume'):
                                    qty_value = getattr(qty, 'VolumeValue', None)
                                elif qty.is_a('IfcQuantityCount'):
                                    qty_value = getattr(qty, 'CountValue', None)
                                elif qty.is_a('IfcQuantityWeight'):
                                    qty_value = getattr(qty, 'WeightValue', None)

                                if qty_value is not None:
                                    qto_props[qty_name] = qty_value

        # Check associated elements (e.g. IfcCovering for IfcWall)
        if entity.is_a("IfcWall") or entity.is_a("IfcWallStandardCase"):
            for rel in model.by_type("IfcRelCoversBldgElements"):
                if rel.RelatingBuildingElement == entity and rel.RelatedCoverings:
                    for covering in rel.RelatedCoverings:
                        if GeometryExtractor.extract_custom_mesh_from_entity(covering):
                            if hasattr(covering, 'IsDefinedBy'):
                                for rel_cov in covering.IsDefinedBy:
                                    if rel_cov.is_a("IfcRelDefinesByProperties"):
                                        pset = rel_cov.RelatingPropertyDefinition
                                        if pset.is_a("IfcElementQuantity") and hasattr(pset, 'Name') and pset.Name.startswith("Qto_"):
                                            if hasattr(pset, 'Quantities'):
                                                for qty in pset.Quantities:
                                                    qty_name = getattr(qty, 'Name', 'Unknown')
                                                    qty_value = None
                                                    
                                                    if qty.is_a('IfcQuantityLength'):
                                                        qty_value = getattr(qty, 'LengthValue', None)
                                                    elif qty.is_a('IfcQuantityArea'):
                                                        qty_value = getattr(qty, 'AreaValue', None)
                                                    elif qty.is_a('IfcQuantityVolume'):
                                                        qty_value = getattr(qty, 'VolumeValue', None)
                                                    elif qty.is_a('IfcQuantityCount'):
                                                        qty_value = getattr(qty, 'CountValue', None)
                                                    elif qty.is_a('IfcQuantityWeight'):
                                                        qty_value = getattr(qty, 'WeightValue', None)
                                                    
                                                    if qty_value is not None:
                                                        qto_props[f"{qty_name}_Covering"] = qty_value

        return qto_props

    @staticmethod
    def transform_coordinates(vertices, rotation, translation):
        """Transform mesh coordinates using rotation and translation."""
        vertices = np.array(vertices, dtype=np.float32).reshape(-1, 3)
        if rotation and any(rotation.values()):
            quat = [rotation["qw"], rotation["qx"], rotation["qy"], rotation["qz"]]
            rot = Rotation.from_quat(quat)
            vertices = rot.apply(vertices)
        vertices = vertices[:, [0, 2, 1]]
        position = [translation["x"], translation["z"], translation["y"]]
        vertices += position
        return vertices
