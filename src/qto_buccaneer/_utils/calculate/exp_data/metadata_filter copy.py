import pandas as pd
from typing import Dict, Any, Literal

class MetadataFilter:
    """Filter structured metadata based on criteria.
    
    Examples:
        Basic filtering:
        >>> df = pd.DataFrame({
        ...     'Name': ['Room 101', 'Room 102', 'Room 103'],
        ...     'Area': [20.0, 25.0, 30.0],
        ...     'Type': ['Office', 'Meeting', 'Office']
        ... })
        >>> 
        >>> # Simple equality filter
        >>> filters = {'Type': 'Office'}
        >>> filtered_df = MetadataFilter.filter_df(df, filters)
        >>> print(filtered_df)
        >>> # Output:
        >>> #      Name  Area    Type
        >>> # 0  Room 101  20.0  Office
        >>> # 2  Room 103  30.0  Office
        >>> 
        >>> # Multiple values filter (OR)
        >>> filters = {'Type': ['Office', 'Meeting']}
        >>> filtered_df = MetadataFilter.filter_df(df, filters)
        >>> print(filtered_df)
        >>> # Output:
        >>> #      Name  Area      Type
        >>> # 0  Room 101  20.0    Office
        >>> # 1  Room 102  25.0  Meeting
        >>> # 2  Room 103  30.0    Office
        >>> 
        >>> # Comparison filter
        >>> filters = {'Area': [('>', 25.0)]}
        >>> filtered_df = MetadataFilter.filter_df(df, filters)
        >>> print(filtered_df)
        >>> # Output:
        >>> #      Name  Area    Type
        >>> # 2  Room 103  30.0  Office
        >>> 
        >>> # Complex filter with AND logic
        >>> filters = {
        ...     'Type': 'Office',
        ...     'Area': [('>', 20.0)]
        ... }
        >>> filtered_df = MetadataFilter.filter_df(df, filters, logic='AND')
        >>> print(filtered_df)
        >>> # Output:
        >>> #      Name  Area    Type
        >>> # 2  Room 103  30.0  Office
        >>> 
        >>> # Complex filter with OR logic
        >>> filters = {
        ...     'Type': 'Office',
        ...     'Area': [('>', 25.0)]
        ... }
        >>> filtered_df = MetadataFilter.filter_df(df, filters, logic='OR')
        >>> print(filtered_df)
        >>> # Output:
        >>> #      Name  Area    Type
        >>> # 0  Room 101  20.0  Office
        >>> 
        >>> # Filter using string expression
        >>> filter_str = "Type=Office AND Area>20.0"
        >>> filtered_df = MetadataFilter.filter_df_from_str(df, filter_str)
        >>> print(filtered_df)
        >>> # Output:
        >>> #      Name  Area    Type
        >>> # 2  Room 103  30.0  Office
    """
    
    @staticmethod
    def filter_df(df: pd.DataFrame, 
                 filters: Dict[str, Any], 
                 logic: Literal["AND", "OR"] = "AND") -> pd.DataFrame:
        """
        Filter a DataFrame of metadata based on criteria.
        
        Args:
            df: DataFrame containing metadata
            filters: Dictionary of filter criteria
            logic: "AND" or "OR" logic for combining filters
            
        Returns:
            Filtered DataFrame
            
        Examples:
            # Basic usage with IFC data
            >>> loader = IfcLoader("model.ifc")
            >>> spaces_df = loader.get_entity_metadata_df("IfcSpace")
            >>> 
            >>> # Filter spaces by area and type
            >>> filters = {
            ...     "Qto_SpaceBaseQuantities.NetFloorArea": [(">", 20.0)],
            ...     "PredefinedType": "OFFICE"
            ... }
            >>> filtered_spaces = MetadataFilter.filter_df(spaces_df, filters)
            >>> 
            >>> # Filter spaces by storey
            >>> filters = {
            ...     "Pset_SpatialData.ElevationOfStory": [(">=", 0.0)]
            ... }
            >>> ground_floor_spaces = MetadataFilter.filter_df(spaces_df, filters)
            >>> 
            >>> # Filter walls by type and length
            >>> walls_df = loader.get_entity_metadata_df("IfcWall")
            >>> filters = {
            ...     "PredefinedType": "SOLIDWALL",
            ...     "Qto_WallBaseQuantities.NetLength": [(">", 5.0)]
            ... }
            >>> filtered_walls = MetadataFilter.filter_df(walls_df, filters)
        """
        if not filters:
            return df
            
        masks = []
        for key, value in filters.items():
            if isinstance(value, list):
                if isinstance(value[0], tuple):  # Comparison operators
                    op, val = value[0]
                    mask = df[key].apply(lambda x: MetadataFilter._compare_values(x, op, val))
                else:  # List of values
                    mask = df[key].isin(value)
            else:  # Single value
                mask = df[key] == value
            masks.append(mask)
            
        if logic == "AND":
            final_mask = pd.concat(masks, axis=1).all(axis=1)
        else:  # OR
            final_mask = pd.concat(masks, axis=1).any(axis=1)
            
        return df[final_mask]

    @staticmethod
    def filter_df_from_str(df: pd.DataFrame, filter_str: str) -> pd.DataFrame:
        """
        Filter a DataFrame using a string expression.
        
        Args:
            df: DataFrame containing metadata
            filter_str: String expression containing filter criteria
            
        Returns:
            Filtered DataFrame
            
        Examples:
            >>> df = pd.DataFrame({
            ...     'Name': ['Room 101', 'Room 102', 'Room 103'],
            ...     'Area': [20.0, 25.0, 30.0],
            ...     'Type': ['Office', 'Meeting', 'Office']
            ... })
            >>> 
            >>> # Simple filter
            >>> filtered_df = MetadataFilter.filter_df_from_str(df, "Type=Office")
            >>> 
            >>> # Complex filter
            >>> filtered_df = MetadataFilter.filter_df_from_str(df, "Type=Office AND Area>20.0")
            >>> 
            >>> # Filter with OR condition
            >>> filtered_df = MetadataFilter.filter_df_from_str(df, "Type=Office AND (Area>25.0 OR Area<15.0)")
        """
        filters = MetadataFilter._parse_filter_expression(filter_str)
        return MetadataFilter.filter_df(df, filters)

    @staticmethod
    def _parse_filter_expression(filter_str: str) -> dict:
        """Parse a filter expression string into a filter dictionary.
        
        Examples:
            >>> MetadataFilter._parse_filter_expression("IfcEntity=IfcSpace AND (PredefinedType=EXTERNAL OR PredefinedType=INTERNAL)")
            {'IfcEntity': 'IfcSpace', 'PredefinedType': ['EXTERNAL', 'INTERNAL']}
            
            >>> MetadataFilter._parse_filter_expression("Area>25.0 AND Type=Office")
            {'Area': [('>', 25.0)], 'Type': 'Office'}
        """
        # Split by AND operators
        parts = filter_str.split(' AND ')
        filters = {}
        
        for part in parts:
            part = part.strip()
            
            # Handle OR conditions in parentheses
            if part.startswith('(') and part.endswith(')'):
                inner_parts = part[1:-1].split(' OR ')
                key = None
                values = []
                
                for inner_part in inner_parts:
                    if '=' in inner_part:
                        k, v = inner_part.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if key is None:
                            key = k
                        values.append(v)
                
                if key and values:
                    filters[key] = values
                    
            # Handle comparison operators
            elif any(op in part for op in ['>', '<', '>=', '<=', '=']):
                for op in ['>=', '<=', '>', '<', '=']:
                    if op in part:
                        key, value = part.split(op, 1)
                        key = key.strip()
                        value = value.strip()
                        try:
                            value = float(value)
                            filters[key] = [(op, value)]
                        except ValueError:
                            filters[key] = value
                        break
                        
            # Handle simple equality
            elif '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip()
                filters[key] = value
        
        return filters

    @staticmethod
    def _compare_values(x: Any, op: str, val: Any) -> bool:
        """Compare values based on operator."""
        if op == ">": return x > val
        elif op == ">=": return x >= val
        elif op == "<": return x < val
        elif op == "<=": return x <= val
        elif op == "=": return x == val
        return False