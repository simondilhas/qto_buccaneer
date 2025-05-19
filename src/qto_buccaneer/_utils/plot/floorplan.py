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
    color_mapping = plot_settings.get('color_mappings', {}).get('space_types', {})
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
            
            # Update color mapping with element-specific color map if available
            if 'color_map' in element_config:
                color_mapping.update(element_config['color_map'])
                used_colors.update(element_config['color_map'].values())
    
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
        storey_name = storey.get('Elevation') or storey.get('Name') or 'Unknown'
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
        
        # A4 landscape dimensions in pixels (at 96 DPI)
        # 297mm × 210mm = 1123 × 794 pixels
        a4_width = 1123  # Landscape width
        a4_height = 794  # Landscape height
        
        # Create consistent layout settings
        consistent_layout = {
            'xaxis': {
                'range': [x_min, x_max],
                'scaleanchor': 'y',
                'scaleratio': 1,  # Keep aspect ratio of content
                'showgrid': False,
                'showticklabels': False,
                'showline': False,
                'domain': [0, 0.75]  # Use 75% of width for plot
            },
            'yaxis': {
                'range': [y_min, y_max],
                'showgrid': False,
                'showticklabels': False,
                'showline': False,
                'domain': [0, 1]  # Full height
            },
            'showlegend': plot_config.get('show_legend', True),  # Use config setting, default to True if not specified
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            'width': a4_width,  # Landscape A4 width in pixels
            'height': a4_height,  # Landscape A4 height in pixels
            'autosize': False,  # Prevent automatic resizing
            'legend': {
                'orientation': 'v',  # Vertical legend
                'yanchor': 'top',  # Anchor to top
                'y': 1,  # Position at top
                'xanchor': 'left',  # Anchor to left
                'x': 0.8,  # Position in right quarter
                'bgcolor': 'white'
            },
            'margin': {
                'l': 50,  # Left margin
                'r': 50,  # Right margin
                't': 50,  # Top margin
                'b': 50,  # Bottom margin
                'pad': 0
            }
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
        storey_elevation = storey.get('Elevation', 'Unknown')
        title_text = f"{plot_config.get('title', 'Floorplan')} - {storey_elevation} m" if plot_config.get('show_title', True) else None
        fig.update_layout(
            title=title_text,
            **consistent_layout
        )
        
        # Save figure
        output_path = output_dir / f"{plot_name}_{storey_elevation}.html"
        fig.write_html(str(output_path))
        fig.write_image(str(output_path.with_suffix('.png')))
        fig.write_json(str(output_path.with_suffix('.json')))
        storey_paths[storey_elevation] = str(output_path)
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
    """Add spaces to the plot with consistent coloring and QTO calculations."""
    # Get color settings
    color_by = element_config.get('color_by')
    fixed_color = element_config.get('color')
    color_map = element_config.get('color_map', {})
    qto_property = element_config.get('qto')
    
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
    grouped_spaces, total_areas = _group_spaces(matching_spaces, color_by, element_config, qto_property)
    
    # Add each group to the plot
    for group_value, space_group in grouped_spaces.items():
        # First try to find color in element-specific color_map
        color = None
        if color_map:
            # Try to find an exact match first
            if group_value in color_map:
                color = color_map[group_value]
            else:
                # Try to find a partial match (for cases where the key includes additional text)
                for key, value in color_map.items():
                    if key in group_value or group_value in key:
                        color = value
                        break
        
        # If no color found in element-specific color_map, try global color_mapping
        if not color and color_mapping:
            if group_value in color_mapping:
                color = color_mapping[group_value]
            else:
                # Try to find a partial match in global color_mapping
                for key, value in color_mapping.items():
                    if key in group_value or group_value in key:
                        color = value
                        break
        
        # If still no color found, use fixed_color or generate new color
        if not color:
            color = fixed_color or _get_color_for_group(group_value, color_mapping, used_colors)
            
        total_area = total_areas.get(group_value, 0.0)
        # Format the legend name with the QTO value if available
        if qto_property and total_area > 0:
            legend_name = f"{group_value} ({total_area:.1f} m²)"
        else:
            legend_name = f"{group_value}"
        
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
    element_config: Dict,
    qto_property: Optional[str] = None
) -> Tuple[Dict[str, List[Dict]], Dict[str, float]]:
    """Group spaces and calculate their total areas based on QTO property."""
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
            
            # Add to total area using the specified QTO property
            if qto_property:
                if qto_property in space:
                    try:
                        area = float(space[qto_property])
                        total_areas[group_value] += area
                    except (ValueError, TypeError):
                        pass
                elif 'properties' in space and qto_property in space['properties']:
                    try:
                        area = float(space['properties'][qto_property])
                        total_areas[group_value] += area
                    except (ValueError, TypeError):
                        pass
    
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
    # Normalize group_value for lookup
    norm_group_value = group_value.strip() if isinstance(group_value, str) else group_value
    # Build a normalized mapping for lookup
    norm_color_mapping = {k.strip() if isinstance(k, str) else k: v for k, v in (color_mapping or {}).items()}
    print(f"[DEBUG] group_value: '{group_value}' (normalized: '{norm_group_value}') | color_mapping keys: {list(norm_color_mapping.keys()) if norm_color_mapping else 'None'}")
    if norm_color_mapping and norm_group_value in norm_color_mapping:
        print(f"[DEBUG] Using config color for '{norm_group_value}': {norm_color_mapping[norm_group_value]}")
        return norm_color_mapping[norm_group_value]
    # Fallback
    available_colors = [
        'lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 
        'lightpink', 'lightskyblue', 'lightseagreen', 'lightsteelblue',
        'lightgoldenrodyellow', 'lightcyan', 'lightgray'
    ]
    unused_colors = [c for c in available_colors if c not in used_colors]
    if unused_colors:
        color = unused_colors[0]
    else:
        color = available_colors[hash(norm_group_value) % len(available_colors)]
    used_colors.add(color)
    if color_mapping is not None:
        color_mapping[group_value] = color
    print(f"[DEBUG] Fallback color for '{group_value}': {color}")
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
    
    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    z = [v[2] for v in vertices]
    
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
        # Get the outer polygon vertices
        if 'polygons' in geometry and geometry['polygons']:
            outer_polygon = geometry['polygons'][0]['outer']
            # Create x and y coordinates for the outer polygon
            poly_x = [vertices[i][0] for i in outer_polygon]
            poly_y = [vertices[i][1] for i in outer_polygon]
            # Close the polygon
            poly_x.append(poly_x[0])
            poly_y.append(poly_y[0])
            
            fig.add_trace(go.Scatter(
                x=poly_x,
                y=poly_y,
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
            
            # Add holes if any
            if 'holes' in geometry['polygons'][0]:
                for hole in geometry['polygons'][0]['holes']:
                    hole_x = [vertices[i][0] for i in hole]
                    hole_y = [vertices[i][1] for i in hole]
                    # Close the hole polygon
                    hole_x.append(hole_x[0])
                    hole_y.append(hole_y[0])
                    
                    fig.add_trace(go.Scatter(
                        x=hole_x,
                        y=hole_y,
                        fill='toself',
                        name=None,
                        fillcolor='white',
                        line=dict(
                            color='white',
                            width=0,
                            shape='linear'
                        ),
                        mode='none',
                        showlegend=False,
                        legendgroup=legendgroup
                    ))
    else:
        # For 3D view, create a mesh
        # Convert polygons to faces for 3D view
        faces = []
        if 'polygons' in geometry and geometry['polygons']:
            # Triangulate the outer polygon
            outer_polygon = geometry['polygons'][0]['outer']
            # Simple triangulation for convex polygons
            for i in range(1, len(outer_polygon) - 1):
                faces.append([outer_polygon[0], outer_polygon[i], outer_polygon[i + 1]])
            
            # Handle holes if any
            if 'holes' in geometry['polygons'][0]:
                for hole in geometry['polygons'][0]['holes']:
                    # Triangulate each hole
                    for i in range(1, len(hole) - 1):
                        faces.append([hole[0], hole[i], hole[i + 1]])
        
        i = [f[0] for f in faces]
        j = [f[1] for f in faces]
        k = [f[2] for f in faces]
        
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
        if 'polygons' in geometry and geometry['polygons']:
            outer_polygon = geometry['polygons'][0]['outer']
            vertices = geometry['vertices']
            
            # Get the outer polygon vertices
            poly_x = [vertices[i][0] for i in outer_polygon]
            poly_y = [vertices[i][1] for i in outer_polygon]
            # Close the polygon
            poly_x.append(poly_x[0])
            poly_y.append(poly_y[0])
            
            # Add the window rectangle with a thin black border
            fig.add_trace(go.Scatter(
                x=poly_x,
                y=poly_y,
                fill='toself',
                fillcolor='white',
                line=dict(color='black', width=1),  # Add thin black border
                mode='lines',
                showlegend=False,
                zorder=2
            ))
            
            # Calculate the center point and orientation for the center line
            center_x = sum(poly_x[:-1]) / len(poly_x[:-1])
            center_y = sum(poly_y[:-1]) / len(poly_y[:-1])
            
            # Find the longest edge to determine window orientation
            max_length = 0
            window_dir = [0, 0]
            for i in range(len(poly_x) - 1):
                dx = poly_x[i + 1] - poly_x[i]
                dy = poly_y[i + 1] - poly_y[i]
                length = math.sqrt(dx*dx + dy*dy)
                if length > max_length:
                    max_length = length
                    window_dir = [dx/length, dy/length]
            
            # Create center line
            line_x = [
                center_x - window_dir[0] * max_length * 0.5,
                center_x + window_dir[0] * max_length * 0.5
            ]
            line_y = [
                center_y - window_dir[1] * max_length * 0.5,
                center_y + window_dir[1] * max_length * 0.5
            ]
            
            # Add the center line representing the glass with higher z-order and thinner line
            fig.add_trace(go.Scatter(
                x=line_x,
                y=line_y,
                line=dict(color='black', width=1),  # Make line thinner
                mode='lines',
                showlegend=False,
                zorder=10  # Increase z-order to ensure visibility on top
            ))

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
        if 'polygons' in geometry and geometry['polygons']:
            outer_polygon = geometry['polygons'][0]['outer']
            vertices = geometry['vertices']
            
            # Get the outer polygon vertices
            poly_x = [vertices[i][0] for i in outer_polygon]
            poly_y = [vertices[i][1] for i in outer_polygon]
            # Close the polygon
            poly_x.append(poly_x[0])
            poly_y.append(poly_y[0])
            
            # Add the door rectangle without border
            fig.add_trace(go.Scatter(
                x=poly_x,
                y=poly_y,
                fill='toself',
                fillcolor='white',
                line=dict(width=0),  # Remove border
                mode='lines',
                showlegend=False,
                zorder=2
            ))
            
            # Calculate the center point and orientation for the perpendicular line
            center_x = sum(poly_x[:-1]) / len(poly_x[:-1])
            center_y = sum(poly_y[:-1]) / len(poly_y[:-1])
            
            # Find the longest edge to determine door orientation
            max_length = 0
            door_dir = [0, 0]
            for i in range(len(poly_x) - 1):
                dx = poly_x[i + 1] - poly_x[i]
                dy = poly_y[i + 1] - poly_y[i]
                length = math.sqrt(dx*dx + dy*dy)
                if length > max_length:
                    max_length = length
                    door_dir = [dx/length, dy/length]
            
            # Create perpendicular line
            perp_dir = [-door_dir[1], door_dir[0]]  # Rotate 90 degrees
            line_length = max_length * 0.5  # Make line half the door width
            
            line_x = [center_x, center_x + perp_dir[0] * line_length]
            line_y = [center_y, center_y + perp_dir[1] * line_length]
            
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
    wall_ids = loader.by_type_index.get('IfcWallStandardCase', [])
    print(f"Found {len(wall_ids)} walls in by_type_index")
    color_by = element_config.get('color_by')
    grouped_walls = {}
    for wall_id in wall_ids:
        print(f"Processing wall with ID {wall_id}")
        wall = loader.properties['elements'].get(str(wall_id))
        if not wall:
            print(f"No wall properties found for ID {wall_id}")
            continue
        geometry = loader.get_geometry(str(wall_id))
        if not geometry:
            print(f"No geometry found for wall {wall_id}")
            continue
        if 'vertices' not in geometry:
            print(f"No vertices found for wall {wall_id}")
            continue
        if storey_name:
            wall_storey = loader.get_storey_for_element(str(wall_id))
            if wall_storey and wall_storey != storey_name:
                print(f"Wall {wall_id} not in storey {storey_name}")
                continue
        group_value = None
        if color_by:
            print(f"\nProcessing wall {wall_id} with color_by: {color_by}")
            if color_by in wall.get('properties', {}):
                group_value = wall['properties'][color_by]
                print(f"Found {color_by} in properties: {group_value}")
            elif color_by in wall:
                group_value = wall[color_by]
                print(f"Found {color_by} in wall object: {group_value}")
            else:
                print(f"Could not find {color_by} in wall properties or object")
        else:
            group_value = element_config.get('name', 'Unknown')
            print(f"No color_by specified, using element name: {group_value}")
        if not group_value:
            group_value = 'Unknown'
            print(f"Using fallback group_value: {group_value}")
        # Normalize group_value for grouping
        norm_group_value = group_value.strip() if isinstance(group_value, str) else group_value
        if norm_group_value not in grouped_walls:
            grouped_walls[norm_group_value] = {
                'walls': [],
                'total_area': 0.0,
                'display_name': group_value  # Keep original for legend
            }
        area = 0.0
        if 'properties' in wall and 'Qto_WallBaseQuantities.NetSideArea' in wall['properties']:
            try:
                area = float(wall['properties']['Qto_WallBaseQuantities.NetSideArea'])
            except (ValueError, TypeError):
                pass
        grouped_walls[norm_group_value]['walls'].append((wall, geometry))
        grouped_walls[norm_group_value]['total_area'] += area
    for norm_group_value, group_data in grouped_walls.items():
        walls = group_data['walls']
        total_area = group_data['total_area']
        display_name = group_data['display_name']
        color = _get_color_for_group(norm_group_value, color_mapping, used_colors)
        legend_name = f"{display_name}"
        for i, (wall, geometry) in enumerate(walls):
            vertices = geometry['vertices']
            # Get the outer polygon vertices
            if 'polygons' in geometry and geometry['polygons']:
                outer_polygon = geometry['polygons'][0]['outer']
                # Create x and y coordinates for the outer polygon
                poly_x = [vertices[i][0] for i in outer_polygon]
                poly_y = [vertices[i][1] for i in outer_polygon]
                # Close the polygon
                poly_x.append(poly_x[0])
                poly_y.append(poly_y[0])
                
                fig.add_trace(go.Scatter(
                    x=poly_x,
                    y=poly_y,
                    fill='toself',
                    fillcolor=color,
                    line=dict(color='black', width=1),
                    mode='lines',
                    name=legend_name if i == 0 else None,
                    showlegend=i == 0,
                    legendgroup=norm_group_value,
                    zorder=1
                ))
                
                # Add holes if any
                if 'holes' in geometry['polygons'][0]:
                    for hole in geometry['polygons'][0]['holes']:
                        hole_x = [vertices[i][0] for i in hole]
                        hole_y = [vertices[i][1] for i in hole]
                        # Close the hole polygon
                        hole_x.append(hole_x[0])
                        hole_y.append(hole_y[0])
                        
                        fig.add_trace(go.Scatter(
                            x=hole_x,
                            y=hole_y,
                            fill='toself',
                            name=None,
                            fillcolor='white',
                            line=dict(color='black', width=1),
                            mode='lines',
                            showlegend=False,
                            legendgroup=norm_group_value,
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