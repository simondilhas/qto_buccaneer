import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple, Union
import yaml
from pathlib import Path
from datetime import datetime
import json
import math
import pandas as pd

from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader
from qto_buccaneer._utils.plot.plots_utils import (
    parse_filter,
    element_matches_conditions
)
from qto_buccaneer.utils.metadata_filter import MetadataFilter

def create_floorplan_per_storey(
    geometry_dir: Union[str, Path],
    properties_path: Union[str, Path],
    config_path: Union[str, Path],
    output_dir: Union[str, Path],
    plot_name: str
) -> Dict[str, str]:
    """Create a floorplan visualization for each storey of the building.
    
    Args:
        geometry_dir: Directory containing geometry JSON files (expected one Json per IfcEntity)
        properties_path: Path to properties JSON file
        config_path: Path to plot configuration YAML file
        output_dir: Output directory for the visualization
        plot_name: Name of the plot configuration to use
        
    Returns:
        Dictionary mapping storey names to their output file paths
    """
    # Convert all paths to Path objects
    geometry_dir = Path(geometry_dir)
    properties_path = Path(properties_path)
    config_path = Path(config_path)
    output_dir = Path(output_dir)
    
    # Load plot configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    plot_config = config['plots'][plot_name]
    plot_settings = config.get('plot_settings', {})
    
    # Initialize color mapping from config and used colors set
    color_mapping = plot_settings.get('color_mapping', {})
    used_colors = set(color_mapping.values())
    
    # Initialize IfcJsonLoader
    loader = IfcJsonLoader(properties_path, geometry_dir)
    
    # Get all elements matching the filter conditions from the config
    filtered_elements = {}
    for element_config in plot_config.get('elements', []):
        filter_str = element_config.get('filter', '')
        if filter_str:
            elements = loader.get_elements_by_filter(filter_str)
            filtered_elements[element_config.get('name', 'unnamed')] = elements
            print(f"\nFound {len(elements)} elements matching filter: {filter_str}")
    
    if not filtered_elements:
        print("No elements found matching filter conditions")
        return {}
    
    # Get unique storeys from all filtered elements
    storey_ids = set()
    for elements in filtered_elements.values():
        for element in elements.values():
            parent_id = element.get('parent_id')
            if parent_id:
                storey_ids.add(parent_id)
    
    # Get storey information
    storeys = []
    for storey_id in storey_ids:
        storey = loader.properties['elements'].get(str(storey_id))
        if storey and storey.get('IfcEntity') == 'IfcBuildingStorey':
            storeys.append(storey)
    
    print(f"\nFound {len(storeys)} storeys with matching elements")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # First pass: Calculate global bounds across all floors
    global_x_coords = []
    global_y_coords = []
    for storey in storeys:
        storey_name = storey.get('Name', 'Unknown')
        print(f"\nCollecting coordinates for storey: {storey_name}")
        
        # Filter elements for this storey
        storey_elements = {}
        for element_name, elements in filtered_elements.items():
            storey_elements[element_name] = {
                element_id: element for element_id, element in elements.items()
                if element.get('parent_id') == storey['id']
            }
        
        # Collect coordinates for current storey
        for elements in storey_elements.values():
            for element in elements.values():
                geometry = loader.get_geometry(str(element['id']))
                if geometry and 'vertices' in geometry:
                    global_x_coords.extend([v[0] for v in geometry['vertices']])
                    global_y_coords.extend([v[1] for v in geometry['vertices']])
    
    # Calculate global bounds with margin
    if global_x_coords and global_y_coords:
        x_min, x_max = min(global_x_coords), max(global_x_coords)
        y_min, y_max = min(global_y_coords), max(global_y_coords)
        
        # Add margin (5% of the larger dimension)
        margin = max(x_max - x_min, y_max - y_min) * 0.05
        x_min -= margin
        x_max += margin
        y_min -= margin
        y_max += margin
        
        # Calculate aspect ratio
        width = x_max - x_min
        height = y_max - y_min
        aspect_ratio = width / height
        
        # A4 aspect ratio is 1:√2 (approximately 1:1.4142)
        a4_ratio = 1.4142
        
        # Create consistent layout settings
        consistent_layout = {
            'xaxis': {
                'range': [x_min, x_max],
                'scaleanchor': 'y',
                'scaleratio': a4_ratio,  # Force A4 aspect ratio
                'showgrid': False,
                'showticklabels': False,
                'showline': False
            },
            'yaxis': {
                'range': [y_min, y_max],
                'showgrid': False,
                'showticklabels': False,
                'showline': False
            },
            'showlegend': True,
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            'width': 794,  # Fixed A4 width in pixels
            'height': 1123,  # Fixed A4 height in pixels
            'autosize': False  # Prevent automatic resizing
        }
    else:
        consistent_layout = {}
    
    # Dictionary to store output paths
    storey_paths = {}
    
    # Second pass: Create figures with consistent layout
    for storey in storeys:
        storey_name = storey.get('Name', 'Unknown')
        print(f"\nProcessing storey: {storey_name}")
        
        # Filter elements for this storey
        storey_elements = {}
        for element_name, elements in filtered_elements.items():
            storey_elements[element_name] = {
                element_id: element for element_id, element in elements.items()
                if element.get('parent_id') == storey['id']
            }
            print(f"Found {len(storey_elements[element_name])} {element_name} elements in storey {storey_name}")
        
        # Create figure
        fig = go.Figure()
        
        # Process each element in the plot configuration
        for element_config in plot_config.get('elements', []):
            element_name = element_config.get('name', 'unnamed')
            if element_name in storey_elements:
                # Pass the pre-filtered elements for this storey
                element_config['filtered_elements'] = storey_elements[element_name]
            _process_element(fig, loader, element_config, plot_settings, storey_name, plot_config, color_mapping, used_colors)
        
        # Update layout with consistent bounds and title
        fig.update_layout(
            title=f"{storey_name}",
            **consistent_layout
        )
        
        # Save figure
        output_path = output_dir / f"{plot_name}_{storey_name}.html"
        fig.write_html(str(output_path))
        fig.write_image(str(output_path.with_suffix('.png')))
        fig.write_json(str(output_path.with_suffix('.json')))
        storey_paths[storey_name] = str(output_path)
        print(f"Saved figure to: {output_path}")
    
    return storey_paths

def load_plot_config(config_path: str) -> Dict:
    """Load plot configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def create_single_plot(
    geometry_json: List[Dict[str, Any]],
    properties_json: Dict[str, Any],
    config: Dict,
    plot_name: str,
    file_info: Optional[Dict] = None
) -> Dict[str, go.Figure]:
    """Create a single plot based on the configuration."""
    if plot_name not in config.get('plots', {}):
        raise ValueError(f"Plot '{plot_name}' not found in configuration")
    
    loader = IfcJsonLoader(geometry_json, properties_json)
    plot_config = config['plots'][plot_name]
    
    try:
        # For floor plans, create separate figures for each storey
        if plot_config.get('mode') == 'floor_plan':
            # Get all storeys from the loader
            storey_ids = loader.by_type_index.get('IfcBuildingStorey', [])
            print(f"\nFound {len(storey_ids)} storeys in by_type_index")
            storey_figures = {}
            
            for storey_id in storey_ids:
                print(f"\nProcessing storey with ID {storey_id}")
                storey = loader.properties['elements'].get(str(storey_id))
                if not storey:
                    print(f"No storey properties found for ID {storey_id}")
                    continue
                    
                storey_name = storey.get('Name', 'Unknown')
                print(f"Storey name: {storey_name}")
                
                # Create a new figure for this storey
                fig = go.Figure()
                _process_plot_creation(
                    fig, loader, plot_name, plot_config,
                    config['plot_settings'], file_info, storey_name
                )
                
                # Force 2D view for floor plans
                fig.update_layout(
                    scene=dict(
                        camera=dict(
                            up=dict(x=0, y=0, z=1),
                            center=dict(x=0, y=0, z=0),
                            eye=dict(x=0, y=0, z=1)
                        )
                    )
                )
                
                storey_figures[storey_name] = fig
                print(f"Added figure for storey {storey_name}")
                
            print(f"\nCreated figures for {len(storey_figures)} storeys")
            return storey_figures
        else:
            # Create single figure for non-floor plan views
            fig = go.Figure()
            _process_plot_creation(
                fig, loader, plot_name, plot_config,
                config['plot_settings'], file_info
            )
            return {'default': fig}
            
    except Exception as e:
        raise RuntimeError(f"Error creating plot '{plot_name}': {str(e)}")

def _process_plot_creation(
    fig: go.Figure,
    loader: IfcJsonLoader,
    plot_name: str,
    plot_config: Dict,
    plot_settings: Dict,
    file_info: Optional[Dict] = None,
    storey_name: Optional[str] = None
) -> None:
    """Process plot creation based on configuration."""
    # Apply layout settings directly
    defaults = plot_settings.get('defaults', {})
    layout_settings = {}
    
    # Font settings
    font_settings = {}
    if 'font_family' in defaults:
        font_settings['family'] = defaults['font_family']
    if 'text_size' in defaults:
        font_settings['size'] = defaults['text_size']
    if font_settings:
        layout_settings['font'] = font_settings
    
    # Legend settings
    if 'show_legend' in defaults:
        layout_settings['showlegend'] = defaults['show_legend']
    
    legend_settings = {}
    legend_keys = {
        'legend_x': 'x',
        'legend_y': 'y',
        'legend_xanchor': 'xanchor',
        'legend_yanchor': 'yanchor',
        'legend_bgcolor': 'bgcolor',
        'legend_bordercolor': 'bordercolor',
        'legend_borderwidth': 'borderwidth',
        'legend_orientation': 'orientation',
        'legend_traceorder': 'traceorder',
        'legend_itemwidth': 'itemwidth',
        'legend_itemsizing': 'itemsizing',
        'legend_tracegroupgap': 'tracegroupgap'
    }
    
    for config_key, plotly_key in legend_keys.items():
        if config_key in defaults:
            legend_settings[plotly_key] = defaults[config_key]
    
    if legend_settings:
        layout_settings['legend'] = legend_settings
    
    # Background color
    if 'background_color' in defaults:
        layout_settings['paper_bgcolor'] = defaults['background_color']
        layout_settings['plot_bgcolor'] = defaults['background_color']
    
    # Margin settings
    margin_settings = {}
    margin_keys = {
        'margin_left': 'l',
        'margin_right': 'r',
        'margin_top': 't',
        'margin_bottom': 'b',
        'margin_pad': 'pad'
    }
    
    for config_key, plotly_key in margin_keys.items():
        if config_key in defaults:
            margin_settings[plotly_key] = defaults[config_key]
    
    if margin_settings:
        layout_settings['margin'] = margin_settings
    
    # Size settings
    if 'autosize' in defaults:
        layout_settings['autosize'] = defaults['autosize']
    if 'width' in defaults:
        layout_settings['width'] = defaults['width']
    if 'height' in defaults:
        layout_settings['height'] = defaults['height']
    
    # Apply layout settings
    fig.update_layout(**layout_settings)
    
    # Process each element in the plot configuration
    for element_config in plot_config.get('elements', []):
        _process_element(fig, loader, element_config, plot_settings, storey_name, plot_config, color_mapping, used_colors)

def _process_element(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    storey_name: Optional[str],
    plot_config: Dict,
    color_mapping: Dict[str, str],
    used_colors: set
) -> None:
    """Process a single element from the configuration."""
    filter_str = element_config.get('filter', '')
    element_type, conditions = parse_filter(filter_str)
    
    if element_type == 'IfcSpace':
        _add_spaces_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config, color_mapping, used_colors)
    elif element_type == 'IfcDoor':
        _add_door_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
    elif element_type == 'IfcWindow':
        _add_window_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
    elif element_type == 'IfcBuildingStorey':
        pass  # Storey visualization not implemented
    elif element_type == 'IfcWallStandardCase':
        print("Starting wall visualization")  # Debug log
        _add_wall_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config, color_mapping, used_colors)
        print("Wall visualization completed")  # Debug log
    else:
        _add_geometry_to_plot(
            fig, loader, element_config, element_type, conditions, plot_settings,
            storey_name, plot_config, element_type == 'IfcSpace', color_mapping, used_colors
        )

def _add_spaces_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    element_type: Optional[str],
    conditions: List[List[str]],
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None,
    color_mapping: Dict[str, str] = None,
    used_colors: set = None
) -> None:
    """Add spaces to the plot with consistent coloring."""
    # Get color settings
    color_by = element_config.get('color_by')
    fixed_color = element_config.get('color')
    color_map = element_config.get('color_map', {})
    
    # Use pre-filtered elements if available
    if 'filtered_elements' in element_config:
        matching_spaces = list(element_config['filtered_elements'].values())
    else:
        # Build filter string
        filter_parts = []
        if element_type:
            filter_parts.append(f"IfcEntity={element_type}")
        
        for or_group in conditions:
            or_parts = []
            for condition in or_group:
                if '=' in condition:
                    key, value = condition.split('=', 1)
                    or_parts.append(f"{key.strip()}={value.strip()}")
            if or_parts:
                if len(or_parts) > 1:
                    filter_parts.append(f"({' OR '.join(or_parts)})")
                else:
                    filter_parts.append(or_parts[0])
        
        filter_str = " AND ".join(filter_parts)
        
        # Get spaces that match the filter conditions
        filtered_elements = loader.get_elements_by_filter(filter_str)
        matching_spaces = list(filtered_elements.values())
    
    # Group spaces and calculate areas
    grouped_spaces, total_areas = _group_spaces(matching_spaces, color_by, element_config)
    
    # Add each group to the plot
    for group_value, space_group in grouped_spaces.items():
        # Use color from color_map if available, otherwise use fixed_color or generate new color
        color = color_map.get(group_value, fixed_color) or _get_color_for_group(group_value, color_mapping, used_colors)
        total_area = total_areas.get(group_value, 0.0)
        legend_name = f"{group_value} ({total_area:.1f} m²)"
        
        for i, space in enumerate(space_group):
            _add_single_space_to_plot(
                fig=fig,
                loader=loader,
                space=space,
                storey_name=storey_name,
                color=color,
                view='2d' if plot_config and plot_config.get('mode') == 'floor_plan' else '3d',
                plot_settings=plot_settings,
                group_name=legend_name if i == 0 else None,
                show_in_legend=(i == 0),
                legendgroup=group_value,
                element_index=i
            )

def _group_spaces(
    spaces: List[Dict],
    color_by: Optional[str],
    element_config: Dict
) -> Tuple[Dict[str, List[Dict]], Dict[str, float]]:
    """Group spaces and calculate their total areas."""
    grouped_spaces = {}
    total_areas = {}
    
    for space in spaces:
        # Get group value
        group_value = None
        if color_by:
            if color_by in space:
                group_value = space[color_by]
        else:
            group_value = element_config.get('name', 'Unknown')
        
        if group_value:
            if group_value not in grouped_spaces:
                grouped_spaces[group_value] = []
                total_areas[group_value] = 0.0
            
            grouped_spaces[group_value].append(space)
            
            # Add to total area
            if 'Qto_SpaceBaseQuantities.NetFloorArea' in space:
                area = space['Qto_SpaceBaseQuantities.NetFloorArea']
                if isinstance(area, (int, float)):
                    total_areas[group_value] += area
    
    return grouped_spaces, total_areas

def _get_color_for_group(group_value: str, color_mapping: Dict[str, str], used_colors: set) -> str:
    """Get a color for a group value, using config mapping or generating a new color.
    
    Args:
        group_value: The value to get a color for
        color_mapping: Dictionary mapping group values to colors
        used_colors: Set of colors already in use
        
    Returns:
        Color string for the group value
    """
    # Try to get color from mapping
    if group_value in color_mapping:
        return color_mapping[group_value]
    
    # Generate a new color that's not in use
    available_colors = [
        'lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 
        'lightpink', 'lightskyblue', 'lightseagreen', 'lightsteelblue',
        'lightgoldenrodyellow', 'lightcyan', 'lightgray'
    ]
    
    # Filter out used colors
    unused_colors = [c for c in available_colors if c not in used_colors]
    
    if unused_colors:
        # Use first unused color
        color = unused_colors[0]
    else:
        # If all colors are used, pick a random one
        color = available_colors[hash(group_value) % len(available_colors)]
    
    # Add to used colors and mapping
    used_colors.add(color)
    color_mapping[group_value] = color
    
    return color

def _add_single_space_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    space: Dict,
    storey_name: Optional[str],
    color: str,
    view: str,
    plot_settings: Dict,
    group_name: Optional[str] = None,
    show_in_legend: bool = True,
    legendgroup: Optional[str] = None,
    element_index: Optional[int] = None
) -> None:
    """Add a single space to the plot."""
    # Get geometry using the numeric ID
    space_id = str(space.get('id'))
    geometry = loader.get_geometry(space_id)
    if not geometry:
        return
        
    # Create mesh trace
    vertices = geometry['vertices']
    faces = geometry['faces']
    
    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    z = [v[2] for v in vertices]
    
    i = [f[0] for f in faces]
    j = [f[1] for f in faces]
    k = [f[2] for f in faces]
    
    # Get the space name and area from properties
    space_name = None
    space_area = None
    
    if 'LongName' in space:
        space_name = space['LongName']
    elif 'Name' in space:
        space_name = space['Name']
    if 'Qto_SpaceBaseQuantities.NetFloorArea' in space:
        space_area = space['Qto_SpaceBaseQuantities.NetFloorArea']
    
    # For legend, use the group name which already contains the total area
    legend_name = group_name if show_in_legend else None
    
    if view == '2d':
        # For 2D view, create a filled polygon with sharp corners
        fig.add_trace(go.Scatter(
            x=x + [x[0]],  # Close the polygon
            y=y + [y[0]],  # Close the polygon
            fill='toself',
            name=legend_name,
            fillcolor=color,
            line=dict(
                color=color,
                width=0,
                shape='linear'  # This ensures sharp corners
            ),
            mode='none',  # Don't show lines or markers
            opacity=0.8,
            showlegend=show_in_legend,
            legendgroup=legendgroup
        ))
    else:
        # For 3D view, create a mesh
        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            name=legend_name,
            color=color,
            opacity=0.8,
            showlegend=show_in_legend,
            legendgroup=legendgroup
        ))

def _add_geometry_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    element_type: Optional[str],
    conditions: List[List[str]],
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None,
    is_space: bool = False,
    color_mapping: Dict[str, str] = None,
    used_colors: set = None
) -> None:
    """Add doors and windows to the plot with special visualization."""
    # Get filter and color settings
    filter_str = element_config.get('filter', '')
    
    # Parse the filter to get the element type
    if 'type=' in filter_str:
        element_type = filter_str.split('type=')[1].split()[0]
        print(f"Processing {element_type} in 2D view")  # Debug log
    else:
        return  # No type specified in filter
    
    # Determine view type from plot config
    view = '2d'
    if plot_config and plot_config.get('mode') == '3d_view':
        view = '3d'
    
    # Special handling for doors and windows in 2D view
    if view == '2d':
        if element_type == 'IfcDoor':
            _add_door_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
        elif element_type == 'IfcWindow':
            print("Starting window visualization")  # Debug log
            _add_window_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
            print("Window visualization completed")  # Debug log
        elif element_type == 'IfcWallStandardCase':
            print("Starting wall visualization")  # Debug log
            _add_wall_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config, color_mapping, used_colors)
            print("Wall visualization completed")  # Debug log

def _create_oriented_symbol(
    vertices: List[List[float]],
    symbol_type: str,
    line_width: float = 1,
    line_extension: float = 2.5
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Create coordinates for a door or window symbol with proper orientation and scaling.
    
    Args:
        vertices: List of vertices [[x1,y1,z1], [x2,y2,z2], ...]
        symbol_type: Either 'door' or 'window'
        line_width: Width of the line (default: 1)
        line_extension: Factor to extend the line beyond the door (default: 2.5)
        
    Returns:
        Tuple of (rect_x, rect_y, line_x, line_y) coordinates
    """
    # Project vertices to 2D by ignoring z-coordinate
    vertices_2d = [[v[0], v[1]] for v in vertices]
    
    if len(vertices_2d) < 4:
        return [], [], [], []
    
    # Find edges and their properties
    edges = []
    for i in range(len(vertices_2d)):
        v1 = vertices_2d[i]
        v2 = vertices_2d[(i + 1) % len(vertices_2d)]
        dx = v2[0] - v1[0]
        dy = v2[1] - v1[1]
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        edges.append((v1, v2, length, angle))
    
    # Sort edges by length to find the longest edges (opening) and shortest edges (thickness)
    edges.sort(key=lambda x: x[2], reverse=True)
    opening_edges = edges[:2]  # Two longest edges
    thickness_edges = edges[-2:]  # Two shortest edges
    
    # Get the wall thickness from the shorter edges
    thickness = thickness_edges[0][2]  # Length of one of the thickness edges
    
    # Use the first opening edge as reference
    v1, v2, length, angle = opening_edges[0]
    
    # Calculate the center point of the opening
    center_x = (v1[0] + v2[0]) / 2
    center_y = (v1[1] + v2[1]) / 2
    
    # Calculate the perpendicular vector (normalized)
    perp_dx = -math.sin(angle)
    perp_dy = math.cos(angle)
    
    # Create rectangle vertices in local coordinates
    # Rectangle is centered at origin
    half_length = length / 2
    half_thickness = thickness / 2
    local_rect_x = [-half_length, half_length, half_length, -half_length, -half_length]
    local_rect_y = [-half_thickness, -half_thickness, half_thickness, half_thickness, -half_thickness]
    
    # Create line coordinates based on symbol type
    if symbol_type == 'door':
        # Door: perpendicular line at midpoint
        local_line_x = [0, 0]
        local_line_y = [-half_thickness, -half_thickness - thickness * line_extension]
    else:
        # Window: centered line along opening
        local_line_x = [-half_length, half_length]
        local_line_y = [0, 0]
    
    # Rotate and translate coordinates
    rect_x, rect_y = [], []
    line_x, line_y = [], []
    
    # Rotation matrix
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    
    # Transform rectangle vertices
    for x, y in zip(local_rect_x, local_rect_y):
        # First rotate around origin
        rotated_x = x * cos_a - y * sin_a
        rotated_y = x * sin_a + y * cos_a
        # Then translate to center point
        rect_x.append(rotated_x + center_x)
        rect_y.append(rotated_y + center_y)
    
    # Transform line vertices
    for x, y in zip(local_line_x, local_line_y):
        # First rotate around origin
        rotated_x = x * cos_a - y * sin_a
        rotated_y = x * sin_a + y * cos_a
        # Then translate to center point
        line_x.append(rotated_x + center_x)
        line_y.append(rotated_y + center_y)
    
    return rect_x, rect_y, line_x, line_y

def _create_door_symbol(
    vertices: List[List[float]],
    line_width: float = 1,
    line_extension: float = 2.5
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Create coordinates for a door symbol with a white square and a perpendicular line."""
    return _create_oriented_symbol(vertices, 'door', line_width, line_extension)

def _add_window_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    element_type: Optional[str],
    conditions: List[List[str]],
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None
) -> None:
    """Add windows to the plot as white rectangles with a thin black border and a thin center line."""
    # Get all window elements
    window_ids = loader.by_type_index.get('IfcWindow', [])
    print(f"Found {len(window_ids)} windows in by_type_index")
    
    for window_id in window_ids:
        print(f"Processing window with ID {window_id}")
        # Get the window element using the numeric ID
        window = loader.properties['elements'].get(str(window_id))
        if not window:
            print(f"No window properties found for ID {window_id}")
            continue
            
        # Get geometry using the numeric ID
        geometry = loader.get_geometry(str(window_id))
        if not geometry:
            print(f"No geometry found for window {window_id}")
            continue
        if 'vertices' not in geometry:
            print(f"No vertices found for window {window_id}")
            continue
            
        # Get the window's storey using the numeric ID
        if storey_name:
            window_storey = loader.get_storey_for_element(str(window_id))
            if window_storey:
                # Get the average Z coordinate of the window
                z_coords = [v[2] for v in geometry['vertices']]
                window_z = sum(z_coords) / len(z_coords)
                print(f"Window {window_id} Z coordinate: {window_z:.3f}")
                
                # Get the storey elevation
                storey_data = None
                for storey in loader.properties['elements'].values():
                    if storey.get('type') == 'IfcBuildingStorey' and storey.get('Name') == storey_name:
                        storey_data = storey
                        break
                
                if storey_data and 'Elevation' in storey_data:
                    storey_elevation = float(storey_data['Elevation'])
                    print(f"Storey {storey_name} elevation: {storey_elevation:.3f}")
                    
                    # Check if window is within reasonable range of storey elevation (±2m)
                    if abs(window_z - storey_elevation) > 2.0:
                        print(f"Window {window_id} not in storey {storey_name} (elevation difference: {abs(window_z - storey_elevation):.3f}m)")
                        continue
                elif window_storey != storey_name:
                    print(f"Window {window_id} not in storey {storey_name}")
                    continue
            
        # Create window symbol using the vertices directly
        rect_x, rect_y, line_x, line_y = _create_window_symbol(geometry['vertices'])
        
        if not rect_x:  # Skip if no valid window symbol could be created
            continue
        
        # Add the window rectangle with a thin black border
        fig.add_trace(go.Scatter(
            x=rect_x,
            y=rect_y,
            fill='toself',
            fillcolor='white',
            line=dict(color='black', width=1),  # Add thin black border
            mode='lines',
            showlegend=False,
            zorder=2
        ))
        
        # Add the center line representing the glass with higher z-order and thinner line
        if line_x and line_y:  # Only add line if we have coordinates
            fig.add_trace(go.Scatter(
                x=line_x,
                y=line_y,
                line=dict(color='black', width=1),  # Make line thinner
                mode='lines',
                showlegend=False,
                zorder=10  # Increase z-order to ensure visibility on top
            ))

def _create_window_symbol(
    vertices: List[List[float]],
    line_width: float = 1
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Create coordinates for a window symbol using actual geometry.
    Handles both rectangular and non-rectangular windows."""
    
    # Project vertices to 2D
    vertices_2d = [[v[0], v[1]] for v in vertices]
    
    # Remove duplicate vertices with tolerance
    unique_vertices = []
    tolerance = 0.0001
    for v in vertices_2d:
        is_duplicate = False
        for u in unique_vertices:
            if (abs(v[0] - u[0]) < tolerance and abs(v[1] - u[1]) < tolerance):
                is_duplicate = True
                break
        if not is_duplicate:
            unique_vertices.append(v)
    
    if len(unique_vertices) < 3:
        print("Warning: Not enough unique vertices for window symbol")
        return [], [], [], []
    
    # Find all edges and their lengths
    edges = []
    for i in range(len(unique_vertices)):
        v1 = unique_vertices[i]
        v2 = unique_vertices[(i + 1) % len(unique_vertices)]
        dx = v2[0] - v1[0]
        dy = v2[1] - v1[1]
        length = math.sqrt(dx*dx + dy*dy)
        if length > tolerance:  # Only consider non-zero length edges
            edges.append({
                'start': v1,
                'end': v2,
                'length': length,
                'direction': [dx/length, dy/length]
            })
    
    if not edges:
        print("Warning: No valid edges found")
        return [], [], [], []
    
    # Sort edges by length (descending)
    edges.sort(key=lambda e: e['length'], reverse=True)
    
    # Determine if we have a rectangular window (two pairs of equal length edges)
    is_rectangular = (len(edges) >= 4 and 
                     abs(edges[0]['length'] - edges[1]['length']) < tolerance and
                     abs(edges[2]['length'] - edges[3]['length']) < tolerance)
    
    # Get the opening edge (longest edge)
    opening_edge = edges[0]
    
    # Calculate window thickness
    if is_rectangular:
        # For rectangular windows, use the shorter edge length
        thickness = edges[2]['length']
    else:
        # For non-rectangular windows, calculate minimum perpendicular distance
        thickness = float('inf')
        edge_start = opening_edge['start']
        edge_end = opening_edge['end']
        edge_dir = opening_edge['direction']
        
        for v in unique_vertices:
            # Skip vertices that are on the opening edge
            if (abs(v[0] - edge_start[0]) < tolerance and abs(v[1] - edge_start[1]) < tolerance) or \
               (abs(v[0] - edge_end[0]) < tolerance and abs(v[1] - edge_end[1]) < tolerance):
                continue
            
            # Calculate perpendicular distance from point to opening edge line
            dx = v[0] - edge_start[0]
            dy = v[1] - edge_start[1]
            dist = abs(dx * (-edge_dir[1]) + dy * edge_dir[0])  # Cross product for perpendicular distance
            thickness = min(thickness, dist)
        
        if thickness == float('inf'):
            thickness = opening_edge['length'] * 0.1  # Fallback: use 10% of opening length
    
    # Calculate the center point of the window
    # Use the midpoint of the opening edge as the reference point
    edge_start = opening_edge['start']
    edge_end = opening_edge['end']
    edge_dir = opening_edge['direction']
    
    # Calculate the center point of the opening edge
    center_x = (edge_start[0] + edge_end[0]) / 2
    center_y = (edge_start[1] + edge_end[1]) / 2
    
    # Calculate perpendicular direction
    perp_dir = [-edge_dir[1], edge_dir[0]]
    
    # Create rectangle coordinates centered on the opening edge
    half_length = opening_edge['length'] / 2
    half_thickness = thickness / 2
    
    # Create the rectangle vertices
    rect_x = [
        center_x - edge_dir[0] * half_length - perp_dir[0] * half_thickness,  # Bottom left
        center_x + edge_dir[0] * half_length - perp_dir[0] * half_thickness,  # Bottom right
        center_x + edge_dir[0] * half_length + perp_dir[0] * half_thickness,  # Top right
        center_x - edge_dir[0] * half_length + perp_dir[0] * half_thickness,  # Top left
        center_x - edge_dir[0] * half_length - perp_dir[0] * half_thickness   # Close polygon
    ]
    
    rect_y = [
        center_y - edge_dir[1] * half_length - perp_dir[1] * half_thickness,  # Bottom left
        center_y + edge_dir[1] * half_length - perp_dir[1] * half_thickness,  # Bottom right
        center_y + edge_dir[1] * half_length + perp_dir[1] * half_thickness,  # Top right
        center_y - edge_dir[1] * half_length + perp_dir[1] * half_thickness,  # Top left
        center_y - edge_dir[1] * half_length - perp_dir[1] * half_thickness   # Close polygon
    ]
    
    # Create line along the opening edge
    line_x = [
        center_x - edge_dir[0] * half_length,
        center_x + edge_dir[0] * half_length
    ]
    
    line_y = [
        center_y - edge_dir[1] * half_length,
        center_y + edge_dir[1] * half_length
    ]
    
    return rect_x, rect_y, line_x, line_y

def _add_door_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    element_type: Optional[str],
    conditions: List[List[str]],
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None
) -> None:
    """Add doors to the plot as white squares with a line perpendicular to the door's orientation."""
    # Get all door elements
    door_ids = loader.by_type_index.get('IfcDoor', [])
    print(f"Found {len(door_ids)} doors in by_type_index")
    
    for door_id in door_ids:
        print(f"Processing door with ID {door_id}")
        # Get the door element using the numeric ID
        door = loader.properties['elements'].get(str(door_id))
        if not door:
            print(f"No door properties found for ID {door_id}")
            continue
            
        # Get geometry using the numeric ID
        geometry = loader.get_geometry(str(door_id))
        if not geometry:
            print(f"No geometry found for door {door_id}")
            continue
        if 'vertices' not in geometry:
            print(f"No vertices found for door {door_id}")
            continue
            
        # Get the door's storey using the numeric ID
        if storey_name:
            door_storey = loader.get_storey_for_element(str(door_id))
            if door_storey and door_storey != storey_name:
                print(f"Door {door_id} not in storey {storey_name}")
                continue
            
        # Create door symbol using the vertices directly
        rect_x, rect_y, line_x, line_y = _create_door_symbol(geometry['vertices'])
        
        if not rect_x:  # Skip if no valid door symbol could be created
            continue
        
        # Add the door rectangle without border
        fig.add_trace(go.Scatter(
            x=rect_x,
            y=rect_y,
            fill='toself',
            fillcolor='white',
            line=dict(width=0),  # Remove border
            mode='lines',
            showlegend=False,
            zorder=2
        ))
        
        # Add the perpendicular line
        fig.add_trace(go.Scatter(
            x=line_x,
            y=line_y,
            line=dict(color='black', width=1),
            mode='lines',
            showlegend=False,
            zorder=2
        ))

def _add_wall_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    element_type: Optional[str],
    conditions: List[List[str]],
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None,
    color_mapping: Dict[str, str] = None,
    used_colors: set = None
) -> None:
    """Add walls to the plot as filled rectangles."""
    # Get all wall elements
    wall_ids = loader.by_type_index.get('IfcWallStandardCase', [])
    print(f"Found {len(wall_ids)} walls in by_type_index")
    
    # Group walls by color_by property if specified
    color_by = element_config.get('color_by')
    grouped_walls = {}
    
    for wall_id in wall_ids:
        print(f"Processing wall with ID {wall_id}")
        # Get the wall element using the numeric ID
        wall = loader.properties['elements'].get(str(wall_id))
        if not wall:
            print(f"No wall properties found for ID {wall_id}")
            continue
            
        # Get geometry using the numeric ID
        geometry = loader.get_geometry(str(wall_id))
        if not geometry:
            print(f"No geometry found for wall {wall_id}")
            continue
        if 'vertices' not in geometry:
            print(f"No vertices found for wall {wall_id}")
            continue
            
        # Get the wall's storey using the numeric ID
        if storey_name:
            wall_storey = loader.get_storey_for_element(str(wall_id))
            if wall_storey and wall_storey != storey_name:
                print(f"Wall {wall_id} not in storey {storey_name}")
                continue
        
        # Get the color group value
        group_value = None
        if color_by:
            if color_by in wall.get('properties', {}):
                group_value = wall['properties'][color_by]
            elif color_by in wall:
                group_value = wall[color_by]
        else:
            group_value = element_config.get('name', 'Unknown')
        
        if not group_value:
            group_value = 'Unknown'
            
        if group_value not in grouped_walls:
            grouped_walls[group_value] = {
                'walls': [],
                'total_area': 0.0
            }
            
        # Calculate wall area
        area = 0.0
        if 'properties' in wall and 'Qto_WallBaseQuantities.NetSideArea' in wall['properties']:
            try:
                area = float(wall['properties']['Qto_WallBaseQuantities.NetSideArea'])
            except (ValueError, TypeError):
                pass
                
        grouped_walls[group_value]['walls'].append((wall, geometry))
        grouped_walls[group_value]['total_area'] += area
    
    # Add each group of walls to the plot
    for group_value, group_data in grouped_walls.items():
        walls = group_data['walls']
        total_area = group_data['total_area']
        
        # Get color for this group
        color = _get_color_for_group(group_value, color_mapping, used_colors)
        
        # Create legend name with total area
        legend_name = f"{group_value} ({total_area:.1f} m²)"
        
        # First add a dummy trace for the legend with no line
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                color=color,
                size=10,
                symbol='square'
            ),
            name=legend_name,
            showlegend=True,
            legendgroup=group_value
        ))
        
        # Add each wall as a separate trace but with the same legend name
        for i, (wall, geometry) in enumerate(walls):
            # Get wall vertices and calculate dimensions
            vertices = geometry['vertices']
            
            # For 2D view, we'll use all vertices and project them to 2D
            # We'll use the vertices with the most common z-coordinate
            z_coords = [v[2] for v in vertices]
            most_common_z = max(set(z_coords), key=z_coords.count)
            
            # Filter vertices to those with the most common z-coordinate
            x_coords = []
            y_coords = []
            for v in vertices:
                if abs(v[2] - most_common_z) < 0.1:  # Allow small tolerance
                    x_coords.append(v[0])
                    y_coords.append(v[1])
            
            if not x_coords or not y_coords:
                print(f"No valid 2D vertices found for wall {wall.get('id')}")
                continue
                
            # Calculate wall bounds
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            
            # Add the wall rectangle
            fig.add_trace(go.Scatter(
                x=[min_x, max_x, max_x, min_x, min_x],  # Close the rectangle
                y=[min_y, min_y, max_y, max_y, min_y],  # Close the rectangle
                fill='toself',
                fillcolor=color,
                line=dict(color='black', width=1),
                mode='lines',
                name=None,  # No name for actual walls
                showlegend=False,  # Don't show in legend
                legendgroup=group_value,  # Group with the dummy trace
                zorder=1
            ))

def _calculate_optimal_layout(x_coords: List[float], y_coords: List[float]) -> Dict:
    """Calculate optimal layout settings based on coordinate bounds.
    
    Args:
        x_coords: List of x coordinates
        y_coords: List of y coordinates
        
    Returns:
        Dictionary with layout settings including margins and aspect ratio
    """
    # Calculate bounds
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    # Calculate dimensions
    width = x_max - x_min
    height = y_max - y_min
    
    # Add margins (10% of the larger dimension)
    margin = max(width, height) * 0.1
    x_min -= margin
    x_max += margin
    y_min -= margin
    y_max += margin
    
    return {
        'xaxis': {
            'range': [x_min, x_max],
            'scaleanchor': 'y',
            'scaleratio': 1,
            'showgrid': False
        },
        'yaxis': {
            'range': [y_min, y_max],
            'showgrid': False
        },
        'showlegend': True,
        'plot_bgcolor': 'white',
        'paper_bgcolor': 'white'
    }

def _find_point_inside_polygon(polygon: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Find a point that is guaranteed to be inside a polygon.
    
    Args:
        polygon: List of (x,y) coordinates forming a closed polygon
        
    Returns:
        Tuple of (x,y) coordinates of a point inside the polygon
    """
    # Find the bounding box of the polygon
    x_coords = [p[0] for p in polygon]
    y_coords = [p[1] for p in polygon]
    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)
    
    # Start with the center of the bounding box
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    
    # If the center is inside the polygon, use it
    if _is_point_inside_polygon(center_x, center_y, polygon):
        return center_x, center_y
    
    # Otherwise, try points along a line from center to each vertex
    for vertex in polygon:
        # Calculate direction vector from center to vertex
        dx = vertex[0] - center_x
        dy = vertex[1] - center_y
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            continue
            
        # Try points at 25%, 50%, and 75% of the distance
        for t in [0.25, 0.5, 0.75]:
            test_x = center_x + dx * t
            test_y = center_y + dy * t
            if _is_point_inside_polygon(test_x, test_y, polygon):
                return test_x, test_y
    
    # If all else fails, return the center (might be outside but better than nothing)
    return center_x, center_y

def _is_point_inside_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
    """Check if a point is inside a polygon using ray casting algorithm.
    
    Args:
        x: X coordinate of point to test
        y: Y coordinate of point to test
        polygon: List of (x,y) coordinates forming a closed polygon
        
    Returns:
        True if point is inside polygon, False otherwise
    """
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside