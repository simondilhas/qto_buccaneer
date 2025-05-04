import pandas as pd
import re
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
    
    # Regular expression for parsing filter terms
    token_re = re.compile(r'''
        ^\s*
        (?P<key>.*?)                      # any chars, as few as possible
        (?=\s*(?:!=|>=|<=|=|>|<)\s*)      # assert that an operator follows
        \s*(?P<op>!=|>=|<=|=|>|<)\s*      # capture the operator (multi-char first)
        (?P<val>.+?)                      # capture the rest as the value
        \s*$
    ''', re.VERBOSE)

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
        """Parse a filter expression string into a filter dictionary."""
        print(f"Parsing filter string: {filter_str}")  # Debug log
        # Split by AND operators (case insensitive)
        parts = re.split(r'\s+AND\s+', filter_str, flags=re.IGNORECASE)
        filters = {}
        
        for part in parts:
            part = part.strip()
            print(f"Processing part: {part}")  # Debug log
            
            # Handle OR conditions in parentheses
            if part.startswith('(') and part.endswith(')'):
                inner_parts = part[1:-1].split(' OR ')
                key = None
                values = []
                
                for inner_part in inner_parts:
                    m = MetadataFilter.token_re.match(inner_part.strip())
                    if not m:
                        raise ValueError(f"Cannot parse filter term: {inner_part}")
                    k, op, v = m.group('key'), m.group('op'), m.group('val')
                    k, v = k.strip(' "\''), v.strip(' "\'')
                    print(f"Parsed OR term - key: {k}, op: {op}, val: {v}")  # Debug log
                    
                    if key is None:
                        key = k
                    if op == '=':
                        values.append(v)
                    else:
                        values.append((op, v))
                
                if key and values:
                    filters[key] = values
                continue
                
            # Parse the filter term using regex
            m = MetadataFilter.token_re.match(part)
            if not m:
                raise ValueError(f"Cannot parse filter term: {part}")
                
            key, op, val = m.group('key'), m.group('op'), m.group('val')
            key, val = key.strip(' "\''), val.strip(' "\'')
            print(f"Parsed term - key: {key}, op: {op}, val: {val}")  # Debug log
            
            # Try to convert to numeric if possible
            try:
                num = float(val)
                if num.is_integer():
                    val = int(num)
                else:
                    val = num
            except ValueError:
                pass
                
            if op == '=':
                filters[key] = val
            else:
                filters[key] = [(op, val)]
        
        print(f"Final filters: {filters}")  # Debug log
        return filters

    @staticmethod
    def _compare_values(x: Any, op: str, val: Any) -> bool:
        """Compare values based on operator."""
        # Try to convert both values to float if they're strings
        try:
            if isinstance(x, str):
                x = float(x)
            if isinstance(val, str):
                val = float(val)
        except (ValueError, TypeError):
            # If conversion fails, compare as strings
            pass
            
        if op == ">": return x > val
        elif op == ">=": return x >= val
        elif op == "<": return x < val
        elif op == "<=": return x <= val
        elif op == "=": return x == val
        elif op == "!=": return x != val
        return False

    @staticmethod
    def filter_df(df: pd.DataFrame, filters: dict, logic: Literal["AND", "OR"] = "AND") -> pd.DataFrame:
        """Filter a DataFrame based on the provided filters."""
        if not filters:
            return df
            
        masks = []
        for key, value in filters.items():
            if key not in df.columns:
                raise KeyError(f"Column '{key}' not found in DataFrame. Available columns: {sorted(df.columns.tolist())}")
                
            if isinstance(value, list):
                if value and isinstance(value[0], tuple):  # Comparison operator
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
    def calculate_metric(df: pd.DataFrame, metric_config: dict, building_name: str) -> pd.DataFrame:
        """Calculate a metric based on the provided configuration.
        
        Args:
            df: DataFrame containing the IFC data
            metric_config: Dictionary containing the metric configuration
            building_name: Name of the building being analyzed
            
        Returns:
            DataFrame containing the metric results
        """
        # Handle both old and new style configurations
        if 'config' in metric_config:
            config = metric_config['config']
            # Parse the filter string into a filter dictionary
            filter_str = config['components'][config['formula']]['filter']
            filters = MetadataFilter._parse_filter_expression(filter_str)
            
            # Apply the filter
            filtered_df = MetadataFilter.filter_df(df, filters)
            
            # Get the base quantity
            base_quantity = config['components'][config['formula']]['base_quantity']
            pset_name, prop_name = base_quantity.split('.')
            
            # Calculate the metric
            value = filtered_df[prop_name].sum()
            
            # Create result DataFrame
            result = pd.DataFrame({
                'Building': [building_name],
                'Metric': [metric_config['name']],
                'Value': [value],
                'Unit': [config['unit']],
                'Description': [metric_config['description']]
            })
            
        else:
            # Old style configuration
            filters = metric_config.get('include_filter', {})
            subtract_filters = metric_config.get('subtract_filter', {})
            
            # Apply include filters
            if filters:
                include_logic = metric_config.get('include_filter_logic', 'AND')
                filtered_df = MetadataFilter.filter_df(df, filters, logic=include_logic)
            else:
                filtered_df = df
                
            # Apply subtract filters
            if subtract_filters:
                subtract_logic = metric_config.get('subtract_filter_logic', 'AND')
                subtract_df = MetadataFilter.filter_df(df, subtract_filters, logic=subtract_logic)
                filtered_df = filtered_df[~filtered_df.index.isin(subtract_df.index)]
            
            # Calculate the metric
            value = filtered_df[metric_config['prop_name']].sum()
            
            # Create result DataFrame
            result = pd.DataFrame({
                'Building': [building_name],
                'Metric': [metric_config.get('name', metric_config['description'])],
                'Value': [value],
                'Unit': ['m2' if metric_config['quantity_type'] == 'area' else 
                        'm3' if metric_config['quantity_type'] == 'volume' else 
                        'count'],
                'Description': [metric_config['description']]
            })
            
        return result