import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple
import yaml
from pathlib import Path
from datetime import datetime
import json

from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader

def create_floorplan_per_storey(
    space_geometry_path: str ,
    door_geometry_path: str ,
    properties_path: str,
    config_path: str,
    output_dir: str 
) -> Dict[str, str]:
    """Create floor plan visualizations for each storey.
    
    Args:
        space_geometry_path: Path to space geometry JSON file
        door_geometry_path: Path to door geometry JSON file
        properties_path: Path to properties JSON file
        config_path: Path to plot configuration YAML file
        output_dir: Output directory for the visualizations

    Returns:
        Dictionary mapping storey names to their output HTML file paths
    """
    # Load data
    print(f"Loading data from {space_geometry_path}, {door_geometry_path} and {properties_path}...")
    geometry_data = []
    
    # Load space geometry
    with open(space_geometry_path, 'r') as f:
        space_geometry = json.load(f)
        geometry_data.extend(space_geometry)
    
    # Load door geometry
    with open(door_geometry_path, 'r') as f:
        door_geometry = json.load(f)
        geometry_data.extend(door_geometry)
    
    # Load properties
    with open(properties_path, 'r') as f:
        properties_data = json.load(f)

    # Load plot configuration
    print(f"Loading plot configuration from {config_path}...")
    config = load_plot_config(config_path)

    # Create file info
    file_info = {
        "file_name": Path(properties_path).stem,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Create the floor plan plots
    print("\nCreating floor plan visualizations...")
    plots = create_single_plot(
        geometry_json=geometry_data,
        properties_json=properties_data,
        config=config,
        plot_name="floor_layout_by_name",
        file_info=file_info
    )
    
    # Save the plots
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    storey_to_output_path = {}
    for storey_name, plot in plots.items():
        output_path = output_dir / f"floor_layout_{storey_name}.html"
        plot.write_html(str(output_path))
        print(f"Saved {storey_name} plot to {output_path}")
        storey_to_output_path[storey_name] = str(output_path)

    print("\nVisualization complete!")

    return storey_to_output_path

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
    """Add a scale bar to the plot that scales with zooming."""
    # Calculate plot dimensions in real-world units
    plot_width = max(x_range) - min(x_range)
    
    # Calculate a nice round length for the scale bar (e.g., 5m or 10m)
    # Scale bar should be ~15% of the plot width
    desired_scale_length = plot_width * 0.15
    
    # Round to a nice number (1, 2, 5, 10, etc.)
    scale_lengths = [1, 2, 5, 10, 20, 50, 100]
    scale_length = next(l for l in scale_lengths if l > desired_scale_length)
    
    # Position in paper coordinates (bottom left)
    # Use fixed paper coordinates (0-1) for positioning
    paper_x = 0.05  # 5% from left edge
    paper_y = 0.05  # 5% from bottom edge
    paper_width = 0.1  # 10% of paper width
    paper_height = 0.01  # 1% of paper height
    
    # Add the scale bar line using paper coordinates
    fig.add_shape(
        type="line",
        x0=paper_x,
        x1=paper_x + paper_width,
        y0=paper_y,
        y1=paper_y,
        line=dict(color="black", width=2),
        layer="above",
        xref="paper",
        yref="paper"
    )
    
    # Add small vertical lines at ends
    for x in [paper_x, paper_x + paper_width]:
        fig.add_shape(
            type="line",
            x0=x,
            x1=x,
            y0=paper_y - paper_height/2,
            y1=paper_y + paper_height/2,
            line=dict(color="black", width=2),
            layer="above",
            xref="paper",
            yref="paper"
        )
    
    # Add text label
    fig.add_annotation(
        x=paper_x + paper_width/2,
        y=paper_y,
        text=f"{scale_length}m",
        showarrow=False,
        font=dict(size=12),
        yshift=-20,  # Shift text down by 20 pixels
        xref="paper",
        yref="paper"
    )

def _calculate_optimal_layout(x_coords: List[float], y_coords: List[float]) -> Dict:
    """Calculate optimal layout settings based on geometry."""
    # Calculate bounds
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    # Calculate dimensions
    width = x_max - x_min
    height = y_max - y_min
    
    # Fixed dimensions for A4-like size
    base_width = 1000  # pixels
    base_height = 600  # pixels
    
    # Calculate the aspect ratios
    content_ratio = width / height
    target_ratio = base_width / base_height
    
    # Calculate the scaling factor to fit the content
    if content_ratio > target_ratio:
        # Content is wider than target, scale to width
        scale = base_width / width
    else:
        # Content is taller than target, scale to height
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
    """Process plot creation based on configuration."""
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
            geometry = loader.get_geometry(str(space_id))
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
            if space and (not storey_name or loader.get_storey_for_space(str(space_id)) == storey_name):
                geometry = loader.get_geometry(str(space_id))
                if geometry:
                    current_x_coords.extend([v[0] for v in geometry['vertices']])
                    current_y_coords.extend([v[1] for v in geometry['vertices']])
    
    # Process each element in the plot configuration
    for i, element_config in enumerate(plot_config.get('elements', [])):
        filter_str = element_config.get('filter', '')
        if 'type=IfcSpace' in filter_str:
            _add_spaces_to_plot(fig, loader, element_config, plot_settings, storey_name, plot_config)
        elif 'type=IfcBuildingStorey' in filter_str:
            _add_storeys_to_plot(fig, loader, element_config, plot_settings)
        else:
            _add_geometry_to_plot(
                fig, loader, element_config, plot_settings, storey_name, plot_config, i, 'type=' in filter_str
            )
    
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
    # Get color settings from element config
    color_by = element_config.get('color_by')
    fixed_color = element_config.get('color')
    
    # Group spaces by their type for the current storey and calculate total areas
    grouped_spaces = {}
    total_areas = {}
    
    for space_id in loader.by_type_index.get('IfcSpace', []):
        space = loader.properties['elements'].get(str(space_id))
        if space:
            # Check storey filter if specified
            if storey_name:
                space_storey = loader.get_storey_for_space(str(space_id))
                if space_storey != storey_name:
                    continue
            
            # Get the value to group by if using color_by
            group_value = None
            if color_by:
                if color_by in space.get('properties', {}):
                    group_value = space['properties'][color_by]
                elif color_by in space:
                    group_value = space[color_by]
            else:
                # If not using color_by, use the element name as group
                group_value = element_config.get('name', 'Unknown')
            
            if group_value:
                if group_value not in grouped_spaces:
                    grouped_spaces[group_value] = []
                    total_areas[group_value] = 0.0
                grouped_spaces[group_value].append(space)
                
                # Add to total area for this group
                if 'properties' in space and 'Qto_SpaceBaseQuantities.NetFloorArea' in space['properties']:
                    area = space['properties']['Qto_SpaceBaseQuantities.NetFloorArea']
                    if isinstance(area, (int, float)):
                        total_areas[group_value] += area
    
    # Add each group of spaces with consistent coloring
    for group_value, space_group in grouped_spaces.items():
        # Get color from fixed color or create a consistent mapping
        if fixed_color:
            color = fixed_color
        else:
            # Create a consistent color mapping for space types
            colors = [
                'lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 
                'lightpink', 'lightskyblue', 'lightseagreen', 'lightsteelblue',
                'lightgoldenrodyellow', 'lightcyan', 'lightgray'
            ]
            color = colors[hash(group_value) % len(colors)]
        
        # Format the legend name with total area
        total_area = total_areas.get(group_value, 0.0)
        legend_name = f"{group_value} ({total_area:.1f} m²)"
        
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
                group_name=legend_name if i == 0 else None,  # Only show total area in first entry
                show_in_legend=(i == 0),  # Only show first space in legend
                legendgroup=group_value,  # Group legend items by space type
                element_index=i  # Pass element index
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
    legendgroup: Optional[str] = None,
    element_index: Optional[int] = None
) -> None:
    """Add a single space to the plot."""
    # Get geometry using the numeric ID
    geometry = loader.get_geometry(str(space.get('id')))
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
    if 'properties' in space:
        if 'LongName' in space['properties']:
            space_name = space['properties']['LongName']
        if 'Qto_SpaceBaseQuantities.NetFloorArea' in space['properties']:
            space_area = space['properties']['Qto_SpaceBaseQuantities.NetFloorArea']
    elif 'LongName' in space:
        space_name = space['LongName']
    elif 'name' in space:
        space_name = space['name']
    
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
            name=legend_name,
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
        
        # Build label text with individual space area
        label_text = [space_name]
        if space_area:
            label_text.append(f"{space_area:.1f} m²")
        
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

def _add_geometry_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None,
    element_index: Optional[int] = None,
    is_space: bool = False
) -> None:
    """Add doors and windows to the plot with special visualization."""
    # Get filter and color settings
    filter_str = element_config.get('filter', '')
    
    # Parse the filter to get the element type
    if 'type=' in filter_str:
        element_type = filter_str.split('type=')[1].split()[0]
    else:
        return  # No type specified in filter
    
    # Determine view type from plot config
    view = '2d'
    if plot_config and plot_config.get('mode') == '3d_view':
        view = '3d'
    
    # Special handling for doors and windows in 2D view
    if view == '2d' and element_type in ['IfcDoor', 'IfcWindow']:
        print(f"Processing {element_type} in 2D view")  # Debug log
        if element_type == 'IfcDoor':
            _add_door_to_plot(fig, loader, element_config, plot_settings, storey_name, plot_config)
        elif element_type == 'IfcWindow':
            pass
        # _add_window_to_plot(fig, loader, element_config, plot_settings, storey_name, plot_config)

def _group_spaces_by_type(
    loader: IfcJsonLoader,
    element_config: Dict,
    storey_name: Optional[str] = None
) -> Dict[str, List[Dict]]:
    """Group spaces by their type for consistent coloring."""
    grouped_spaces = {}
    total_areas = {}
    
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
            if element_config.get('color_by'):
                if element_config['color_by'] in space.get('properties', {}):
                    group_value = space['properties'][element_config['color_by']]
                elif element_config['color_by'] in space:
                    group_value = space[element_config['color_by']]
            else:
                group_value = element_config.get('name', 'Unknown')
            
            if group_value:
                if group_value not in grouped_spaces:
                    grouped_spaces[group_value] = []
                    total_areas[group_value] = 0.0
                grouped_spaces[group_value].append(space)
                
                # Add to total area for this group
                if 'properties' in space and 'Qto_SpaceBaseQuantities.NetFloorArea' in space['properties']:
                    area = space['properties']['Qto_SpaceBaseQuantities.NetFloorArea']
                    if isinstance(area, (int, float)):
                        total_areas[group_value] += area
    
    return grouped_spaces

def _extract_geometry_data(geometry: Dict, element_type: str) -> Tuple[List[List[float]], List[List[int]]]:
    """Extract vertices and faces from geometry data."""
    if element_type in ['IfcWindow', 'IfcDoor'] and 'outline' in geometry:
        vertices = geometry['outline']
        faces = [[i, i+1, i+2] for i in range(0, len(vertices)-2)]
    elif 'vertices' in geometry and 'faces' in geometry:
        vertices = geometry['vertices']
        faces = geometry['faces']
    else:
        return [], []
    
    return vertices, faces

def _calculate_zorder(element_type: str, element_index: Optional[int]) -> int:
    """Calculate zorder based on element type and config order."""
    zorder = 1  # Default zorder
    if element_type == 'IfcSpace':
        zorder = 0  # Spaces go to the bottom
    elif element_type == 'IfcWindow':
        zorder = 3  # Windows go on top
    elif element_type == 'IfcDoor':
        zorder = 2  # Doors go above spaces but below windows
    
    # Add config order to zorder to respect element order in config
    if element_index is not None:
        zorder += element_index * 10  # Use larger steps to avoid conflicts
    
    return zorder

def _create_legend_name(element: Dict, group_name: str, is_space: bool) -> Optional[str]:
    """Create the name to show in the legend."""
    if not is_space:
        return element.get('name', 'Unknown')
    
    # For spaces, include the total area in the group name
    total_area = 0.0
    if 'properties' in element and 'Qto_SpaceBaseQuantities.NetFloorArea' in element['properties']:
        area = element['properties']['Qto_SpaceBaseQuantities.NetFloorArea']
        if isinstance(area, (int, float)):
            total_area = area
    
    return f"{group_name} ({total_area:.1f} m²)"

def _add_geometry_trace(
    fig: go.Figure,
    vertices: List[List[float]],
    faces: List[List[int]],
    view: str,
    color: str,
    legend_name: Optional[str],
    show_legend: bool,
    legendgroup: str,
    zorder: int,
    line_width: float
) -> None:
    """Add a geometry trace to the plot."""
    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    z = [v[2] if len(v) > 2 else 0 for v in vertices]
    
    if view == '2d':
        # For 2D view, create a filled polygon
        x_outline = x + [x[0]]  # Close the polygon
        y_outline = y + [y[0]]  # Close the polygon
        
        fig.add_trace(go.Scatter(
            x=x_outline,
            y=y_outline,
            fill='toself',
            name=legend_name,
            fillcolor=color,
            line=dict(
                color=color,
                width=line_width
            ),
            mode='lines',
            opacity=0.8,
            showlegend=show_legend,
            legendgroup=legendgroup,
            zorder=zorder
        ))
    else:
        # For 3D view, create a mesh
        i = [f[0] for f in faces]
        j = [f[1] for f in faces]
        k = [f[2] for f in faces]
        
        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            name=legend_name,
            color=color,
            opacity=0.8,
            showlegend=show_legend,
            legendgroup=legendgroup,
            zorder=zorder
        ))

def _add_element_labels(
    fig: go.Figure,
    element: Dict,
    vertices: List[List[float]],
    view: str,
    plot_settings: Dict,
    element_config: Dict
) -> None:
    """Add labels to the element."""
    # Find a suitable position within the element
    x_coords = [v[0] for v in vertices]
    y_coords = [v[1] for v in vertices]
    center_x = sum(x_coords) / len(x_coords)
    center_y = sum(y_coords) / len(y_coords)
    
    # Build label text
    label_text = []
    for prop in element_config.get('labels', {}).get('properties', []):
        if prop in element.get('properties', {}):
            value = element['properties'][prop]
            if isinstance(value, (int, float)):
                label_text.append(f"{value:.1f}")
            else:
                label_text.append(str(value))
    
    if not label_text:
        return
    
    if view == '2d':
        fig.add_trace(go.Scatter(
            x=[center_x],
            y=[center_y],
            text=['\n'.join(label_text)],
            mode='text',
            showlegend=False,
            textfont=dict(
                size=plot_settings['defaults']['text_size'],
                family=plot_settings['defaults']['font_family']
            )
        ))
    else:
        center_z = sum([v[2] if len(v) > 2 else 0 for v in vertices]) / len(vertices)
        fig.add_trace(go.Scatter3d(
            x=[center_x],
            y=[center_y],
            z=[center_z],
            text=['\n'.join(label_text)],
            mode='text',
            showlegend=False,
            textfont=dict(
                size=plot_settings['defaults']['text_size'],
                family=plot_settings['defaults']['font_family']
            )
        ))

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

def _add_door_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None
) -> None:
    """Add doors to the plot as simple red dots."""
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
            
        # Calculate door center
        vertices = geometry['vertices']
        x_coords = [v[0] for v in vertices]
        y_coords = [v[1] for v in vertices]
        center_x = sum(x_coords) / len(x_coords)
        center_y = sum(y_coords) / len(y_coords)
        
        print(f"Adding door at ({center_x}, {center_y}) with vertices: {vertices}")
        
        # Add a red dot at the door location
        fig.add_trace(go.Scatter(
            x=[center_x],
            y=[center_y],
            mode='markers',
            marker=dict(
                color='red',
                size=10
            ),
            showlegend=False,
            zorder=2
        ))

#def _add_window_to_plot(
#    fig: go.Figure,
#    loader: IfcJsonLoader,
#    element_config: Dict,
#    plot_settings: Dict,
#    storey_name: Optional[str] = None,
#    plot_config: Optional[Dict] = None
#) -> None:
#    """Add windows to the plot as simple symbols with a cross."""
#    # Get all window elements
#    window_ids = loader.by_type_index.get('IfcWindow', [])
#    print(f"Found {len(window_ids)} windows to process")  # Debug log
#    
#    for window_id in window_ids:
#        window = loader.properties['elements'].get(str(window_id))
#        if not window:
#            print(f"No window properties found for ID {window_id}")  # Debug log
#            continue
#            
#        # Check storey filter if specified
#        if storey_name:
#            window_storey = loader.get_storey_for_element(window['ifc_global_id'])
#            if window_storey != storey_name:
#                print(f"Window {window['ifc_global_id']} not in storey {storey_name}")  # Debug log
#                continue
#        
#        # Get geometry
#        geometry = loader.get_geometry(window['ifc_global_id'])
#        if not geometry:
#            print(f"No geometry found for window {window['ifc_global_id']}")  # Debug log
#            continue
#        
#        # Extract vertices
#        vertices = geometry['vertices']
#        if not vertices:
#            print(f"No vertices found for window {window['ifc_global_id']}")  # Debug log
#            continue
#        
#        # Calculate window dimensions and position
#        x_coords = [v[0] for v in vertices]
#        y_coords = [v[1] for v in vertices]
#        z_coords = [v[2] for v in vertices]
#        
#        # Calculate window center and dimensions
#        center_x = sum(x_coords) / len(x_coords)
#        center_y = sum(y_coords) / len(y_coords)
#        window_width = max(x_coords) - min(x_coords)
#        window_height = max(z_coords) - min(z_coords)
#        
#        print(f"Adding window at ({center_x}, {center_y}) with size {window_width}x{window_height}")  # Debug log
#        
#        # Create window symbol (rectangle with cross)
#        # Scale the symbol to match the window size
#        symbol_width = window_width * 0.8  # 80% of window width
#        symbol_height = window_height * 0.8  # 80% of window height
#        
#        # Create rectangle vertices
#        rect_x = [
#            center_x - symbol_width/2,
#            center_x + symbol_width/2,
#            center_x + symbol_width/2,
#            center_x - symbol_width/2,
#            center_x - symbol_width/2  # Close the rectangle
#        ]
#        rect_y = [
#            center_y - symbol_height/2,
#            center_y - symbol_height/2,
#            center_y + symbol_height/2,
#            center_y + symbol_height/2,
#            center_y - symbol_height/2  # Close the rectangle
#        ]
#        
#        # Add the window rectangle
#        fig.add_trace(go.Scatter(
#            x=rect_x,
#            y=rect_y,
#            fill='toself',
#            fillcolor='white',
#            line=dict(color='black', width=1),
#            mode='lines',
#            showlegend=False,
#            zorder=3  # Ensure windows are above doors
#        ))
#        
#        # Add cross lines
#        fig.add_trace(go.Scatter(
#            x=[center_x - symbol_width/2, center_x + symbol_width/2],
#            y=[center_y - symbol_height/2, center_y + symbol_height/2],
#            line=dict(color='black', width=1),
#            mode='lines',
#            showlegend=False,
#            zorder=4  # Above the rectangle
#        ))
#        
#        fig.add_trace(go.Scatter(
#            x=[center_x - symbol_width/2, center_x + symbol_width/2],
#            y=[center_y + symbol_height/2, center_y - symbol_height/2],
#            line=dict(color='black', width=1),
#            mode='lines',
#            showlegend=False,
#            zorder=4  # Above the rectangle
#        )) 