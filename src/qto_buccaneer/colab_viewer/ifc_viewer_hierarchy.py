"""
Hierarchical Structure Module for qto_buccaneer Viewer
Builds and manages the hierarchical organization of IFC elements.
"""

from collections import defaultdict
from .ifc_viewer_geometry import GeometryExtractor


class HierarchicalStructure:
    """Builds and manages hierarchical structure of IFC model."""
    
    def __init__(self, model):
        """
        Initialize hierarchical structure builder.
        
        Parameters:
        -----------
        model : ifcopenshell.file
            Loaded IFC model
        """
        self.model = model
        self.hierarchy = defaultdict(lambda: defaultdict(list))
        self.build_hierarchy()

    def build_hierarchy(self):
        """Build the hierarchical structure from the IFC model."""
        building_storeys = self.model.by_type("IfcBuildingStorey")
        
        if not building_storeys:
            self._build_default_hierarchy()
            return
        
        for storey in building_storeys:
            storey_name = storey.Name or f"Storey_{storey.GlobalId[:8]}"
            if hasattr(storey, 'ContainsElements'):
                for rel in storey.ContainsElements:
                    if rel.is_a("IfcRelContainedInSpatialStructure"):
                        for element in rel.RelatedElements:
                            if element.is_a("IfcProduct"):
                                ifc_type = element.is_a()
                                self.hierarchy[storey_name][ifc_type].append(element)
        
        if not any(self.hierarchy.values()):
            self._build_fallback_hierarchy()
            return

    def _build_fallback_hierarchy(self):
        """Build fallback hierarchy when elements aren't in storeys."""
        elements_with_mesh = []
        all_products = self.model.by_type("IfcProduct")
        
        for element in all_products:
            if GeometryExtractor.extract_custom_mesh_from_entity(element):
                elements_with_mesh.append(element)
        
        building_storeys = self.model.by_type("IfcBuildingStorey")
        
        for element in elements_with_mesh:
            assigned_storey = None
            for storey in building_storeys:
                if hasattr(storey, 'ContainsElements'):
                    for rel in storey.ContainsElements:
                        if rel.is_a("IfcRelContainedInSpatialStructure"):
                            if element in rel.RelatedElements:
                                assigned_storey = storey
                                break
                if assigned_storey:
                    break
            
            if not assigned_storey:
                if building_storeys:
                    assigned_storey = building_storeys[0]
                else:
                    assigned_storey = None
            
            if assigned_storey:
                storey_name = assigned_storey.Name or f"Storey_{assigned_storey.GlobalId[:8]}"
            else:
                storey_name = "Default_Level"
            
            ifc_type = element.is_a()
            self.hierarchy[storey_name][ifc_type].append(element)

    def _build_default_hierarchy(self):
        """Build default hierarchy for models without storeys."""
        all_products = self.model.by_type("IfcProduct")
        for element in all_products:
            if GeometryExtractor.extract_custom_mesh_from_entity(element):
                storey_name = "Default_Level"
                ifc_type = element.is_a()
                self.hierarchy[storey_name][ifc_type].append(element)

    def get_hierarchy(self):
        """
        Get the built hierarchy.
        
        Returns:
        --------
        dict
            Dictionary mapping storey names to IFC types to elements
        """
        return dict(self.hierarchy)
