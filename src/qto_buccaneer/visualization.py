import plotly.graph_objects as go
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path
from datetime import datetime

from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader

def load_plot_config(config_path: str) -> Dict:
    """Load plot configuration from YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing plot configuration
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def create_single_plot(
    geometry_json: List[Dict[str, Any]],
    properties_json: Dict[str, Any],
    config: Dict,
    plot_name: str,
    file_info: Optional[Dict] = None
) -> Dict[str, go.Figure]:
    """Create a single plot based on the configuration.
    
    Args:
        geometry_json: List of geometry objects
        properties_json: Dictionary of properties
        config: Plot configuration dictionary
        plot_name: Name of the plot to create
        file_info: Optional dictionary with file information
        
    Returns:
        Dictionary mapping storey names to Plotly Figure objects (or single figure if not a floor plan)
    """
    if plot_name not in config.get('plots', {}):
        raise ValueError(f"Plot '{plot_name}' not found in configuration")
    
    loader = IfcJsonLoader(geometry_json, properties_json)
    plot_config = config['plots'][plot_name]
    
    try:
        # For floor plans, create separate figures for each storey
        if plot_config.get('mode') == 'floor_plan':
            # Get all storeys
            storey_ids = loader.by_type_index.get('IfcBuildingStorey', [])
            storey_figures = {}
            
            for storey_id in storey_ids:
                storey = loader.properties['elements'].get(str(storey_id))
                if not storey:
                    continue
                    
                storey_name = storey.get('name', 'Unknown')
                
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

def create_all_plots(
    geometry_json: List[Dict[str, Any]],
    properties_json: Dict[str, Any],
    config: Dict,
    file_info: Optional[Dict] = None
) -> Dict[str, go.Figure]:
    """Create all plots defined in the configuration.
    
    Args:
        geometry_json: List of geometry objects
        properties_json: Dictionary of properties
        config: Plot configuration dictionary
        file_info: Optional dictionary with file information
        
    Returns:
        Dictionary mapping plot names to Plotly Figure objects
    """
    plots = {}
    
    for plot_name in config.get('plots', {}).keys():
        try:
            fig = create_single_plot(
                geometry_json=geometry_json,
                properties_json=properties_json,
                config=config,
                plot_name=plot_name,
                file_info=file_info
            )
            plots[plot_name] = fig
        except Exception as e:
            print(f"Error creating plot '{plot_name}': {str(e)}")
    
    return plots

def _add_scale_bar(fig: go.Figure, x_range: List[float], y_range: List[float]) -> None:
    """Add a scale bar to the plot."""
    # Calculate a nice round length for the scale bar (e.g., 5m or 10m)
    plot_width = max(x_range) - min(x_range)
    desired_scale_length = plot_width * 0.15  # Scale bar should be ~15% of plot width
    
    # Round to a nice number (1, 2, 5, 10, etc.)
    scale_lengths = [1, 2, 5, 10, 20, 50, 100]
    scale_length = next(l for l in scale_lengths if l > desired_scale_length)
    
    # Position the scale bar at the absolute bottom
    padding = plot_width * 0.03
    scale_x_start = max(x_range) - scale_length - padding
    scale_y = min(y_range) - padding * 3  # Move scale bar further down
    
    # Add the scale bar line
    fig.add_trace(go.Scatter(
        x=[scale_x_start, scale_x_start + scale_length],
        y=[scale_y, scale_y],
        mode='lines',
        line=dict(color='black', width=1),  # Thinner line
        showlegend=False
    ))
    
    # Add small vertical lines at ends
    tick_height = padding * 0.3  # Smaller ticks
    for x in [scale_x_start, scale_x_start + scale_length]:
        fig.add_trace(go.Scatter(
            x=[x, x],
            y=[scale_y - tick_height/2, scale_y + tick_height/2],
            mode='lines',
            line=dict(color='black', width=1),  # Thinner line
            showlegend=False
        ))
    
    # Add text label below the scale bar
    fig.add_trace(go.Scatter(
        x=[scale_x_start + scale_length/2],
        y=[scale_y - tick_height],
        text=[f"{scale_length}m"],
        mode='text',
        textposition='bottom center',
        showlegend=False
    ))

def _calculate_optimal_layout(x_coords: List[float], y_coords: List[float], max_size: int = 1200) -> Dict:
    """Calculate optimal layout settings based on geometry."""
    # Calculate bounds
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    # Calculate dimensions
    width = x_max - x_min
    height = y_max - y_min
    
    # Fixed dimensions for A4 landscape (297x210mm)
    base_width = 1000  # pixels
    base_height = int(base_width / 1.414)  # A4 proportion (1.414 is √2)
    
    # Calculate the aspect ratios
    content_ratio = width / height
    a4_ratio = base_width / base_height
    
    # Calculate the scaling factor to fill the space
    if content_ratio > a4_ratio:
        # Content is wider than A4, scale to width
        scale = base_width / width
    else:
        # Content is taller than A4, scale to height
        scale = base_height / height
    
    # Calculate the centered ranges
    center_x = (x_max + x_min) / 2
    center_y = (y_max + y_min) / 2
    
    # Calculate the range that will fill the space
    half_width = (base_width / scale) / 2
    half_height = (base_height / scale) / 2
    
    x_range = [center_x - half_width, center_x + half_width]
    y_range = [center_y - half_height, center_y + half_height]
    
    return {
        'width': base_width,
        'height': base_height,
        'xaxis': {
            'range': x_range,
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
            'showline': False,
            'scaleanchor': 'y',
            'scaleratio': 1,
            'domain': [0.01, 0.99]  # Use 98% of the width
        },
        'yaxis': {
            'range': y_range,
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
            'showline': False,
            'scaleanchor': 'x',
            'scaleratio': 1,
            'domain': [0.01, 0.99]  # Use 98% of the height
        }
    }

def _process_plot_creation(
    fig: go.Figure,
    loader: IfcJsonLoader,
    plot_name: str,
    plot_config: Dict,
    plot_settings: Dict,
    file_info: Optional[Dict] = None,
    storey_name: Optional[str] = None
) -> None:
    """Process plot creation based on configuration.
    
    Args:
        fig: Plotly Figure to update
        loader: IfcJsonLoader instance
        plot_name: Name of the plot
        plot_config: Configuration for this specific plot
        plot_settings: General plot settings
        file_info: Optional file information
        storey_name: Optional storey name for filtering
    """
    # Apply general layout settings
    defaults = plot_settings['defaults']
    
    # Convert font settings to Plotly format with minimal margins
    layout_settings = {
        'font': {
            'family': defaults.get('font_family', 'Arial'),
            'size': defaults.get('text_size', 12)
        },
        'showlegend': True,  # Force legend to be shown
        'legend': {
            'x': 0.98,  # Position at the right edge
            'y': 0.98,  # Position at the top
            'xanchor': 'right',  # Anchor to right side
            'yanchor': 'top',  # Anchor to top
            'bgcolor': 'rgba(255, 255, 255, 0.8)',  # Semi-transparent white background
            'bordercolor': 'rgba(0, 0, 0, 0)',  # No border
            'borderwidth': 0,  # No border width
            'orientation': 'v',  # Vertical orientation
            'traceorder': 'normal',  # Keep original order
            'itemwidth': 30,  # Width of legend items
            'itemsizing': 'constant',  # Keep items same size
            'tracegroupgap': 0  # Remove gaps between legend items
        },
        'paper_bgcolor': defaults.get('background_color', 'white'),
        'plot_bgcolor': defaults.get('background_color', 'white'),
        'margin': {
            'l': 5,  # Minimal left margin
            'r': 5,  # Minimal right margin
            't': 5,  # Minimal top margin
            'b': 25,  # Small bottom margin for scale bar
            'pad': 0  # Remove padding
        },
        'autosize': False
    }
    
    # First find the bounds of ALL storeys to maintain consistent scale
    all_x_coords = []
    all_y_coords = []
    
    # Collect coordinates from all spaces in all storeys
    for space_id in loader.by_type_index.get('IfcSpace', []):
        space = loader.properties['elements'].get(str(space_id))
        if space:
            geometry = loader.get_geometry(space['ifc_global_id'])
            if geometry:
                all_x_coords.extend([v[0] for v in geometry['vertices']])
                all_y_coords.extend([v[1] for v in geometry['vertices']])
    
    if all_x_coords and all_y_coords:
        # Calculate layout based on ALL storeys
        optimal_layout = _calculate_optimal_layout(all_x_coords, all_y_coords)
        layout_settings.update(optimal_layout)
    
    fig.update_layout(**layout_settings)
    
    # Now collect coordinates for the current storey (for scale bar)
    current_x_coords = []
    current_y_coords = []
    
    if plot_config.get('mode') == 'floor_plan':
        for space_id in loader.by_type_index.get('IfcSpace', []):
            space = loader.properties['elements'].get(str(space_id))
            if space and (not storey_name or loader.get_storey_for_space(space['ifc_global_id']) == storey_name):
                geometry = loader.get_geometry(space['ifc_global_id'])
                if geometry:
                    current_x_coords.extend([v[0] for v in geometry['vertices']])
                    current_y_coords.extend([v[1] for v in geometry['vertices']])
    
    # Process each element in the plot configuration
    for element_config in plot_config.get('elements', []):
        filter_str = element_config.get('filter', '')
        if 'type=IfcSpace' in filter_str:
            _add_spaces_to_plot(fig, loader, element_config, plot_settings, storey_name, plot_config)
        elif 'type=IfcBuildingStorey' in filter_str:
            _add_storeys_to_plot(fig, loader, element_config, plot_settings)
        else:
            _add_elements_to_plot(fig, loader, element_config, plot_settings)
    
    # Add scale bar for 2D plots using current storey bounds for positioning
    if plot_config.get('mode') == 'floor_plan' and current_x_coords and current_y_coords:
        _add_scale_bar(fig, [min(current_x_coords), max(current_x_coords)], [min(current_y_coords), max(current_y_coords)])

def _add_spaces_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None
) -> None:
    """Add spaces to the plot with consistent coloring."""
    # Get color_by setting from element config
    color_by = element_config.get('color_by', 'LongName')
    
    # First collect all unique space types across ALL storeys
    all_space_types = set()
    for space_id in loader.by_type_index.get('IfcSpace', []):
        space = loader.properties['elements'].get(str(space_id))
        if space:
            # Get the value to group by
            group_value = None
            if color_by in space.get('properties', {}):
                group_value = space['properties'][color_by]
            elif color_by in space:
                group_value = space[color_by]
            
            if group_value:
                all_space_types.add(group_value)
    
    # Create a consistent color mapping for ALL space types
    colors = [
        'lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 
        'lightpink', 'lightskyblue', 'lightseagreen', 'lightsteelblue',
        'lightgoldenrodyellow', 'lightcyan', 'lightgray'
    ]
    color_mapping = {space_type: colors[i % len(colors)] 
                    for i, space_type in enumerate(sorted(all_space_types))}
    
    # Group spaces by their type for the current storey
    grouped_spaces = {}
    for space_id in loader.by_type_index.get('IfcSpace', []):
        space = loader.properties['elements'].get(str(space_id))
        if space:
            # Check storey filter if specified
            if storey_name:
                space_storey = loader.get_storey_for_space(space['ifc_global_id'])
                if space_storey != storey_name:
                    continue
            
            # Get the value to group by
            group_value = None
            if color_by in space.get('properties', {}):
                group_value = space['properties'][color_by]
            elif color_by in space:
                group_value = space[color_by]
            
            if group_value:
                if group_value not in grouped_spaces:
                    grouped_spaces[group_value] = []
                grouped_spaces[group_value].append(space)
    
    # Add each group of spaces with consistent coloring
    for group_value, space_group in grouped_spaces.items():
        # Get color from our consistent mapping
        color = color_mapping.get(group_value, 'lightgray')
        
        # Add all spaces in this group with the same color
        for i, space in enumerate(space_group):
            _add_single_space_to_plot(
                fig=fig,
                loader=loader,
                space=space,
                storey_name=storey_name,
                color=color,
                view='2d' if plot_config and plot_config.get('mode') == 'floor_plan' else '3d',
                plot_settings=plot_settings,
                group_name=group_value,
                show_in_legend=(i == 0),  # Only show first space in legend
                legendgroup=group_value  # Group legend items by space type
            )

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
    legendgroup: Optional[str] = None
) -> None:
    """Add a single space to the plot.
    
    Args:
        fig: Plotly Figure to add space to
        loader: IfcJsonLoader instance
        space: Space properties dictionary
        storey_name: Optional storey name for grouping
        color: Color for the space
        view: View type ('2d' or '3d')
        plot_settings: General plot settings
        group_name: Optional name for the group in the legend
        show_in_legend: Whether to show this trace in the legend
        legendgroup: Optional group name for legend grouping
    """
    # Get geometry
    geometry = loader.get_geometry(space['ifc_global_id'])
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
    
    # Get the space name from properties or direct attributes
    space_name = None
    if 'properties' in space and 'LongName' in space['properties']:
        space_name = space['properties']['LongName']
    elif 'LongName' in space:
        space_name = space['LongName']
    elif 'name' in space:
        space_name = space['name']
    
    if view == '2d':
        # For 2D view, create a filled polygon with sharp corners
        fig.add_trace(go.Scatter(
            x=x + [x[0]],  # Close the polygon
            y=y + [y[0]],  # Close the polygon
            fill='toself',
            name=group_name if group_name else space_name,
            fillcolor=color,
            line=dict(
                color=color,  # Use same color as fill for the line
                width=0,  # Set line width to 0 to hide it
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
            name=group_name if group_name else space_name,
            color=color,
            opacity=0.8,
            showlegend=show_in_legend,
            legendgroup=legendgroup
        ))
    
    if space_name:
        # Find a suitable position within the space
        # Create a list of polygon vertices
        poly = list(zip(x, y))
        
        # Find a point that is guaranteed to be inside the space
        point_inside = _find_point_inside_polygon(poly)
        text_x, text_y = point_inside
        
        # Build label text from properties
        label_text = []
        for prop in ['LongName']:
            if prop in space.get('properties', {}):
                label_text.append(space['properties'][prop])
            elif prop in space:
                label_text.append(space[prop])
            label_text.append('')  # Add extra newline after LongName
        
        if view == '2d':
            # For 2D view, position text at the guaranteed inside point
            fig.add_trace(go.Scatter(
                x=[text_x],
                y=[text_y],
                text=['\n'.join(label_text)],
                mode='text',
                showlegend=False,
                textfont=dict(
                    size=plot_settings['defaults']['text_size'],
                    family=plot_settings['defaults']['font_family']
                )
            ))
        else:
            # For 3D view, use the same x,y coordinates and the average z
            center_z = sum(z) / len(z)
            fig.add_trace(go.Scatter3d(
                x=[text_x],
                y=[text_y],
                z=[center_z],
                text=['\n'.join(label_text)],
                mode='text',
                showlegend=False,
                textfont=dict(
                    size=plot_settings['defaults']['text_size'],
                    family=plot_settings['defaults']['font_family']
                )
            ))

def _add_storeys_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict
) -> None:
    """Add storeys to the plot.
    
    Args:
        fig: Plotly Figure to add storeys to
        loader: IfcJsonLoader instance
        element_config: Configuration for storey visualization
        plot_settings: General plot settings
    """
    # Implementation for storey visualization
    pass

def _add_elements_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict
) -> None:
    """Add building elements to the plot.
    
    Args:
        fig: Plotly Figure to add elements to
        loader: IfcJsonLoader instance
        element_config: Configuration for element visualization
        plot_settings: General plot settings
    """
    # Implementation for element visualization
    pass

def _point_inside_polygon(x: float, y: float, poly: List[List[float]]) -> bool:
    """Check if a point is inside a polygon using ray casting algorithm."""
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def _find_point_inside_polygon(poly: List[List[float]]) -> List[float]:
    """Find a point that is guaranteed to be inside the polygon."""
    # First try the center of the bounding box
    x_coords = [p[0] for p in poly]
    y_coords = [p[1] for p in poly]
    center_x = sum(x_coords) / len(x_coords)
    center_y = sum(y_coords) / len(y_coords)
    
    if _point_inside_polygon(center_x, center_y, poly):
        return [center_x, center_y]
    
    # If center is outside, try points along a grid
    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)
    
    # Try points in a 3x3 grid
    for x in [min_x + (max_x - min_x) * i/4 for i in range(1, 4)]:
        for y in [min_y + (max_y - min_y) * i/4 for i in range(1, 4)]:
            if _point_inside_polygon(x, y, poly):
                return [x, y]
    
    # If no point found in grid, return the first vertex
    return poly[0] 