from typing import Dict, List, Optional, Tuple
import plotly.graph_objects as go

def parse_filter(filter_str: str) -> Tuple[Optional[str], List[List[str]]]:
    """Parse filter string into element type and conditions.
    
    Args:
        filter_str: Filter string in format "type=IfcType AND (condition1 OR condition2)"
        
    Returns:
        Tuple of (element_type, conditions) where conditions is a list of lists of strings.
        Each inner list represents an OR group, and the outer list represents AND groups.
    """
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

def element_matches_conditions(element: Dict, conditions: List[List[str]]) -> bool:
    """Check if an element matches all filter conditions.
    
    Args:
        element: Element dictionary containing properties
        conditions: List of lists of conditions. Each inner list represents an OR group,
                   and the outer list represents AND groups.
        
    Returns:
        True if element matches all conditions, False otherwise
    """
    for or_group in conditions:
        # At least one condition in the OR group must be true
        or_group_matched = False
        for condition in or_group:
            # Split condition into key and value
            if '=' in condition:
                key, value = condition.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Check if the condition is met
                if key in element.get('properties', {}):
                    if str(element['properties'][key]) == value:
                        or_group_matched = True
                        break
                elif key in element:
                    if str(element[key]) == value:
                        or_group_matched = True
                        break
        
        # If no condition in the OR group matched, the whole AND fails
        if not or_group_matched:
            return False
    
    # All conditions passed
    return True

def apply_layout_settings(fig: go.Figure, plot_settings: Dict) -> None:
    """Apply general layout settings to the figure."""
    defaults = plot_settings['defaults']
    layout_settings = {
        'font': {
            'family': defaults.get('font_family', 'Arial'),
            'size': defaults.get('text_size', 12)
        },
        'showlegend': True,
        'legend': {
            'x': 0.98,
            'y': 0.98,
            'xanchor': 'right',
            'yanchor': 'top',
            'bgcolor': 'rgba(255, 255, 255, 0.8)',
            'bordercolor': 'rgba(0, 0, 0, 0)',
            'borderwidth': 0,
            'orientation': 'v',
            'traceorder': 'normal',
            'itemwidth': 30,
            'itemsizing': 'constant',
            'tracegroupgap': 0
        },
        'paper_bgcolor': defaults.get('background_color', 'white'),
        'plot_bgcolor': defaults.get('background_color', 'white'),
        'margin': {
            'l': 5,
            'r': 5,
            't': 5,
            'b': 25,
            'pad': 0
        },
        'autosize': False
    }
    fig.update_layout(**layout_settings) 