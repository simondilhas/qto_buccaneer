from typing import Optional, Dict, Any

class SimpleIFC:
    """
    A beginner-friendly wrapper for IFC quantity calculations.
    Provides simple methods for common building measurement tasks.
    """
    
    def __init__(self, ifc_loader):
        """
        Initialize with an IFC loader.
        
        Args:
            ifc_loader: An instance of your IFC loader class
        """
        from .qto_calculator import QtoCalculator
        self.calculator = QtoCalculator(ifc_loader)
        self.loader = ifc_loader
    
    # ===== Floor Area Methods =====
    
    def calculate_gross_floor_area(self, exclude_technical: bool = False) -> float:
        """
        Calculate the total gross floor area.
        
        Args:
            exclude_technical: If True, excludes technical rooms
            
        Returns:
            float: Gross floor area in m²
        """
        subtract_filter = {"LongName": "Technical"} if exclude_technical else None
        return self.calculator.calculate_area("space", subtract_filter=subtract_filter)
    
    def calculate_floor_area_by_usage(self, usage_type: str) -> float:
        """
        Calculate floor area by usage type.
        
        Args:
            usage_type: Usage type (e.g., "Office", "Residential", "Commercial")
            
        Returns:
            float: Floor area for the specified usage type in m²
        """
        return self.calculator.calculate_area(
            "space", 
            additional_filter={"Pset_SpaceCommon.OccupancyType": usage_type}
        )
    
    # ===== Envelope Methods =====
    
    def calculate_exterior_wall_area(self) -> float:
        """
        Calculate the total exterior wall area.
        
        Returns:
            float: Exterior wall area in m²
        """
        return self.calculator.calculate_area(
            "covering", 
            is_external=True,
            additional_filter={"PredefinedType": "CLADDING"}
        )
    
    def calculate_exterior_window_area(self) -> float:
        """
        Calculate the total exterior window area.
        
        Returns:
            float: Exterior window area in m²
        """
        return self.calculator.calculate_area("window", is_external=True)
    
    def calculate_interior_window_area(self) -> float:
        """
        Calculate the total interior window area.
        
        Returns:
            float: Interior window area in m²
        """
        return self.calculator.calculate_area("window", is_external=False)
    
    def calculate_exterior_door_area(self) -> float:
        """
        Calculate the total exterior door area.
        
        Returns:
            float: Exterior door area in m²
        """
        return self.calculator.calculate_area("door", is_external=True)
    
    def calculate_interior_door_area(self) -> float:
        """
        Calculate the total interior door area.
        
        Returns:
            float: Interior door area in m²
        """
        return self.calculator.calculate_area("door", is_external=False)
    
    # ===== Volume Methods =====
    
    def calculate_gross_volume(self, exclude_technical: bool = False) -> float:
        """
        Calculate the gross building volume.
        
        Args:
            exclude_technical: If True, excludes technical spaces
            
        Returns:
            float: Gross volume in m³
        """
        subtract_filter = {"LongName": "Technical"} if exclude_technical else None
        return self.calculator.calculate_volume("space", subtract_filter=subtract_filter)
    
    # ===== Advanced/Custom Queries =====
    
    def find_spaces_by_criteria(self, criteria: Dict[str, Any]) -> list:
        """
        Find spaces matching specific criteria.
        
        Args:
            criteria: Dictionary of property filters
            
        Returns:
            list: List of matching IFC space elements
        """
        return self.loader.get_elements(filters=criteria, ifc_entity="IfcSpace")
    
    def calculate_custom_area(self, 
                             entity_type: str,
                             is_external: Optional[bool] = None,
                             additional_filter: Optional[Dict] = None) -> float:
        """
        Calculate area with custom filters for advanced users.
        
        Args:
            entity_type: Type of entity ("space", "window", "door", "covering")
            is_external: If True, only include external elements; if False, only internal
            additional_filter: Additional filters to apply
            
        Returns:
            float: Calculated area in m²
        """
        return self.calculator.calculate_area(
            entity_type, 
            is_external=is_external,
            additional_filter=additional_filter
        )