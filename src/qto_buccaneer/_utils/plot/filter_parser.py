from typing import Dict, List, Optional, Union, Any
import re

class FilterParser:
    """A class to parse and evaluate filter expressions for IFC elements."""
    
    @staticmethod
    def parse_filter(filter_str: str) -> tuple[Optional[str], List[List[str]]]:
        """Parse a filter string into element type and conditions.
        
        Args:
            filter_str: The filter string to parse (e.g., "type=IfcSpace AND PredefinedType=INTERNAL")
            
        Returns:
            Tuple of (element_type, conditions) where:
            - element_type: The type of element to filter (e.g., "IfcSpace")
            - conditions: List of OR groups, where each group is a list of AND conditions
        """
        if not filter_str:
            return None, []
            
        # First extract the type
        type_part = None
        if 'type=' in filter_str:
            type_part = filter_str.split('type=')[1].split()[0]
            # Remove the type part from the filter
            filter_str = filter_str.replace(f"type={type_part}", "").strip()
            # Remove any leading AND/OR
            if filter_str.startswith("AND "):
                filter_str = filter_str[4:].strip()
            elif filter_str.startswith("OR "):
                filter_str = filter_str[3:].strip()
        
        # Split into individual conditions
        conditions = []
        if filter_str:
            # Split by AND first
            and_parts = [p.strip() for p in filter_str.split(" AND ")]
            
            for part in and_parts:
                # Handle parentheses for OR conditions
                if '(' in part and ')' in part:
                    start = part.find('(')
                    end = part.rfind(')')
                    inner = part[start+1:end].strip()
                    # Split by OR
                    or_conditions = [c.strip() for c in inner.split(" OR ")]
                    conditions.append(or_conditions)
                else:
                    # Single condition
                    conditions.append([part.strip()])
        
        return type_part, conditions

    @staticmethod
    def evaluate_condition(element: Dict[str, Any], key: str, value: str) -> bool:
        """Evaluate a single condition against an element.
        
        Args:
            element: The element to check
            key: The property key to check
            value: The expected value
            
        Returns:
            True if the condition is met, False otherwise
        """
        # Check if the property exists and matches the value (case-insensitive)
        if key in element:
            return str(element[key]).lower() == value.lower()
        
        return False

    @staticmethod
    def element_matches_conditions(
        element: Dict[str, Any],
        element_type: Optional[str],
        conditions: List[List[str]]
    ) -> bool:
        """Check if an element matches all filter conditions.
        
        Args:
            element: The element to check
            element_type: The expected element type
            conditions: List of OR groups, where each group is a list of AND conditions
            
        Returns:
            True if the element matches all conditions, False otherwise
        """
        # First check if the element is of the correct type
        if element_type and element.get('IfcEntity') != element_type:
            return False
            
        # Then check all conditions
        for or_group in conditions:
            # At least one condition in the OR group must be true
            or_group_matched = False
            for condition in or_group:
                # Split condition into key and value
                if '=' in condition:
                    key, value = condition.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if FilterParser.evaluate_condition(element, key, value):
                        or_group_matched = True
                        break
            
            # If no condition in the OR group matched, the whole AND fails
            if not or_group_matched:
                return False
        
        # All conditions passed
        return True 