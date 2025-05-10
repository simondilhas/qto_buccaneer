import pandas as pd
from typing import Dict, Any, Literal, List, Tuple, Union

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
            
        field_masks = {}
        
        # Process each filter field
        for key, value in filters.items():
            if key not in field_masks:
                field_masks[key] = []
                
            if isinstance(value, list):
                if len(value) > 0 and isinstance(value[0], tuple):  # Comparison operators
                    # Handle each comparison operator separately
                    for op, val in value:
                        mask = df[key].apply(lambda x: MetadataFilter._compare_values(x, op, val))
                        field_masks[key].append(mask)
                else:  # List of values (OR condition)
                    mask = df[key].isin(value)
                    field_masks[key].append(mask)
            else:  # Single value
                mask = df[key] == value
                field_masks[key].append(mask)
        
        # Combine masks for each field with AND logic
        field_combined_masks = []
        for field, masks in field_masks.items():
            if masks:
                # Combine all masks for this field with AND logic
                field_mask = masks[0]
                for mask in masks[1:]:
                    field_mask = field_mask & mask
                field_combined_masks.append(field_mask)
        
        # Combine field masks according to the specified logic
        if not field_combined_masks:
            return df
            
        if logic == "AND":
            final_mask = field_combined_masks[0]
            for mask in field_combined_masks[1:]:
                final_mask = final_mask & mask
        else:  # OR
            final_mask = field_combined_masks[0]
            for mask in field_combined_masks[1:]:
                final_mask = final_mask | mask
            
        return df[final_mask]

    @staticmethod
    def filter_df_from_str(df: pd.DataFrame, filter_str: str) -> pd.DataFrame:
        """
        Filter a DataFrame using a string expression.
        
        Args:
            df: DataFrame to filter
            filter_str: Filter expression string
            
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
            >>> print(filtered_df)
            >>> # Output:
            >>> #      Name  Area    Type
            >>> # 0  Room 101  20.0  Office
            >>> # 2  Room 103  30.0  Office
            >>> 
            >>> # Complex filter
            >>> filtered_df = MetadataFilter.filter_df_from_str(df, "Type=Office AND Area>20.0")
            >>> print(filtered_df)
            >>> # Output:
            >>> #      Name  Area    Type
            >>> # 2  Room 103  30.0  Office
        """
        if not filter_str:
            return df
            
        # Start with the full DataFrame
        result_df = df.copy()
        
        # Verificăm dacă avem un OR la nivel superior (nu în paranteze)
        if " OR " in filter_str and "(" not in filter_str:
            # Împărțim expresia în părți separate prin OR
            or_parts = filter_str.split(" OR ")
            or_dfs = []
            
            # Aplicăm fiecare parte separat și combinăm rezultatele
            for part in or_parts:
                part = part.strip()
                if part:
                    filtered = MetadataFilter.filter_df_from_str(df, part)
                    or_dfs.append(filtered)
            
            # Combinăm toate rezultatele OR
            if or_dfs:
                return pd.concat(or_dfs).drop_duplicates()
            return result_df
        
        # Split by AND operators
        parts = filter_str.split(' AND ')
        
        for part in parts:
            part = part.strip()
            
            # Handle parenthesized OR expressions
            if part.startswith("(") and part.endswith(")"):
                inner_expr = part[1:-1].strip()
                or_parts = inner_expr.split(" OR ")
                
                # Create a temporary DataFrame for each OR condition
                or_dfs = []
                for or_part in or_parts:
                    or_part = or_part.strip()
                    # Parse the simple condition
                    if "=" in or_part:
                        key, value = or_part.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                        # Map 'type' to 'IfcEntity'
                        if key.lower() == 'type':
                            key = 'IfcEntity'
                        or_dfs.append(df[df[key] == value])
                    elif ">" in or_part:
                        key, value = or_part.split(">", 1)
                        key = key.strip()
                        value = float(value.strip())
                        or_dfs.append(df[df[key] > value])
                    elif "<" in or_part:
                        key, value = or_part.split("<", 1)
                        key = key.strip()
                        value = float(value.strip())
                        or_dfs.append(df[df[key] < value])
                
                # Combine all OR conditions
                if or_dfs:
                    or_combined = pd.concat(or_dfs).drop_duplicates()
                    # Intersect with the current result
                    result_df = pd.merge(result_df, or_combined, how='inner')
            else:
                # Handle simple conditions
                simple_filter = MetadataFilter._parse_filter_expression(part)
                result_df = MetadataFilter.filter_df(result_df, simple_filter)
        
        return result_df

    @staticmethod
    def _handle_complex_expression(df: pd.DataFrame, filter_str: str) -> pd.DataFrame:
        """Handle complex filter expressions with AND, OR, and parentheses."""
        # Split by AND
        and_parts = filter_str.split(" AND ")
        result_df = df.copy()
        
        for part in and_parts:
            part = part.strip()
            
            # Handle parenthesized OR expressions
            if part.startswith("(") and part.endswith(")"):
                inner_expr = part[1:-1].strip()
                or_parts = inner_expr.split(" OR ")
                
                # Create a temporary DataFrame for each OR condition
                or_dfs = []
                for or_part in or_parts:
                    or_part = or_part.strip()
                    # Parse the simple condition
                    if "=" in or_part:
                        key, value = or_part.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                        # Map 'type' to 'IfcEntity'
                        if key.lower() == 'type':
                            key = 'IfcEntity'
                        or_dfs.append(df[df[key] == value])
                    elif ">" in or_part:
                        key, value = or_part.split(">", 1)
                        key = key.strip()
                        value = float(value.strip())
                        or_dfs.append(df[df[key] > value])
                    elif "<" in or_part:
                        key, value = or_part.split("<", 1)
                        key = key.strip()
                        value = float(value.strip())
                        or_dfs.append(df[df[key] < value])
                
                # Combine all OR conditions
                if or_dfs:
                    or_combined = pd.concat(or_dfs).drop_duplicates()
                    # Intersect with the current result
                    result_df = pd.merge(result_df, or_combined, how='inner')
            else:
                # Handle simple conditions
                simple_filter = MetadataFilter._parse_filter_expression(part)
                result_df = MetadataFilter.filter_df(result_df, simple_filter)
        
        return result_df

    @staticmethod
    def _parse_filter_expression(filter_str: str) -> Dict[str, Union[str, List[Tuple[str, float]]]]:
        """Parse a filter expression string into a filter dictionary.
        
        Examples:
            >>> MetadataFilter._parse_filter_expression("type=IfcSpace AND (PredefinedType=EXTERNAL OR PredefinedType=INTERNAL)")
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
                    inner_part = inner_part.strip()
                    if '=' in inner_part:
                        k, v = inner_part.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if key is None:
                            key = k
                        values.append(v)
                
                if key and values:
                    # Map 'type' to 'IfcEntity'
                    if key.lower() == 'type':
                        key = 'IfcEntity'
                    filters[key] = values
            
            # Handle comparison operators
            elif any(op in part for op in ['>', '<', '>=', '<=', '=']):
                for op in ['>=', '<=', '>', '<', '=']:
                    if op in part:
                        key, value = part.split(op, 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Map 'type' to 'IfcEntity'
                        if key.lower() == 'type':
                            key = 'IfcEntity'
                            
                        if op == '=':
                            # Handle equality
                            try:
                                value = float(value)
                            except ValueError:
                                pass
                            filters[key] = value
                        else:
                            # Handle comparison operators
                            try:
                                value = float(value)
                                if key not in filters:
                                    filters[key] = []
                                if isinstance(filters[key], list):
                                    filters[key].append((op, value))
                                else:
                                    # Convert existing value to list if needed
                                    filters[key] = [(op, value)]
                            except ValueError:
                                # For non-numeric values, treat as equality
                                filters[key] = value
                        break
        
        return filters

    @staticmethod
    def _compare_values(x: Any, op: str, val: Any) -> bool:
        """Compare values based on operator."""
        if x is None:
            return False
            
        try:
            # Try to convert to numeric for comparison
            if isinstance(x, str) and x.replace('.', '', 1).isdigit():
                x = float(x)
        except (ValueError, TypeError):
            pass
            
        if op == ">": return x > val
        elif op == ">=": return x >= val
        elif op == "<": return x < val
        elif op == "<=": return x <= val
        elif op == "=": return x == val
        return False