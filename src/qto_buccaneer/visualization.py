import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple
import yaml
from pathlib import Path
from datetime import datetime
import json

from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader

def create_floorplan_per_storey(
    geometry_dir: str,
    properties_path: str,
    config_path: str,
    output_dir: str
) -> Dict[str, str]:
    """Create floor plan visualizations for each storey.
    
    Args:
        geometry_dir: Directory containing geometry JSON files (e.g., IfcSpace_geometry.json, IfcDoor_geometry.json)
        properties_path: Path to properties JSON file
        config_path: Path to plot configuration YAML file
        output_dir: Output directory for the visualizations
        
    Returns:
        Dictionary mapping storey names to their output HTML file paths

    Raises:
        FileNotFoundError: If required geometry files are missing
    """
    # Load data
    print(f"Loading geometry data from {geometry_dir}...")
    geometry_data = []
    
    # Check for required geometry files
    geometry_dir = Path(geometry_dir)
    required_files = {
        'IfcSpace_geometry.json': 'space',
        'IfcDoor_geometry.json': 'door',
        'IfcWindow_geometry.json': 'window'
    }
    
    missing_files = []
    for file_name, element_type in required_files.items():
        if not (geometry_dir / file_name).exists():
            missing_files.append(f"{file_name} (required for {element_type} visualization)")
    
    if missing_files:
        raise FileNotFoundError(
            f"Missing required geometry files in {geometry_dir}:\n" +
            "\n".join(f"- {file}" for file in missing_files)
        )
    
    # Load all geometry files in the directory
    for geometry_file in geometry_dir.glob("*_geometry.json"):
        print(f"Loading geometry from {geometry_file}")
        with open(geometry_file, 'r') as f:
            geometry = json.load(f)
            geometry_data.extend(geometry)
    
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
            pass  # Storey visualization not implemented
        else:
            _add_geometry_to_plot(
                fig, loader, element_config, plot_settings, storey_name, plot_config, i, 'type=' in filter_str
            )
    
    # Add scale bar for 2D plots using current storey bounds for positioning
    if plot_config.get('mode') == 'floor_plan' and current_x_coords and current_y_coords:
        _add_scale_bar(fig, [min(current_x_coords), max(current_x_coords)], [min(current_y_coords), max(current_y_coords)])

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
    is_gfa = False
    if 'properties' in space:
        if 'LongName' in space['properties']:
            space_name = space['properties']['LongName']
        if 'Qto_SpaceBaseQuantities.NetFloorArea' in space['properties']:
            space_area = space['properties']['Qto_SpaceBaseQuantities.NetFloorArea']
            is_gfa = True
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
                color='black' if is_gfa else color,  # Black border only for GFA spaces
                width=1 if is_gfa else 0,  # Border width only for GFA spaces
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
            _add_door_to_plot(fig, loader, element_config, plot_settings, storey_name, plot_config)
        elif element_type == 'IfcWindow':
            print("Starting window visualization")  # Debug log
            _add_window_to_plot(fig, loader, element_config, plot_settings, storey_name, plot_config)
            print("Window visualization completed")  # Debug log

def _create_door_symbol(
    width: float,
    height: float,
    center_x: float,
    center_y: float,
    line_width: float = 1,
    line_extension: float = 2.5
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Create coordinates for a door symbol with a white square and a perpendicular line.
    
    Args:
        width: Width of the door
        height: Height of the door
        center_x: X coordinate of the door center
        center_y: Y coordinate of the door center
        line_width: Width of the line (default: 1)
        line_extension: Factor to extend the line beyond the door (default: 2.5)
        
    Returns:
        Tuple of (rect_x, rect_y, line_x, line_y) coordinates
    """
    # Create square vertices
    rect_x = [
        center_x - width/2,
        center_x + width/2,
        center_x + width/2,
        center_x - width/2,
        center_x - width/2
    ]
    rect_y = [
        center_y - height/2,
        center_y - height/2,
        center_y + height/2,
        center_y + height/2,
        center_y - height/2
    ]
    
    # Create perpendicular line coordinates
    if width > height:
        # Horizontal door - draw vertical line
        line_length = height * line_extension
        line_x = [center_x, center_x]
        line_y = [center_y - line_length/2, center_y + line_length/2]
    else:
        # Vertical door - draw horizontal line
        line_length = width * line_extension
        line_x = [center_x - line_length/2, center_x + line_length/2]
        line_y = [center_y, center_y]
    
    return rect_x, rect_y, line_x, line_y

def _add_door_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
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
            
        # Get door vertices and calculate dimensions
        vertices = geometry['vertices']
        x_coords = [v[0] for v in vertices]
        y_coords = [v[1] for v in vertices]
        
        # Calculate door center and dimensions
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        width = max_x - min_x
        height = max_y - min_y
        
        # Calculate center point
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Create door symbol
        rect_x, rect_y, line_x, line_y = _create_door_symbol(width, height, center_x, center_y)
        
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

def _create_window_symbol(
    width: float,
    height: float,
    center_x: float,
    center_y: float,
    line_width: float = 2
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Create coordinates for a window symbol with a white rectangle and a centered line.
    
    Args:
        width: Width of the window
        height: Height of the window
        center_x: X coordinate of the window center
        center_y: Y coordinate of the window center
        line_width: Width of the line (default: 2)
        
    Returns:
        Tuple of (rect_x, rect_y, line_x, line_y) coordinates
    """
    # Create rectangle vertices
    rect_x = [
        center_x - width/2,
        center_x + width/2,
        center_x + width/2,
        center_x - width/2,
        center_x - width/2
    ]
    rect_y = [
        center_y - height/2,
        center_y - height/2,
        center_y + height/2,
        center_y + height/2,
        center_y - height/2
    ]
    
    # Create line coordinates
    if width > height:
        # Horizontal window - draw horizontal line
        line_x = [center_x - width/2, center_x + width/2]
        line_y = [center_y, center_y]
    else:
        # Vertical window - draw vertical line
        line_x = [center_x, center_x]
        line_y = [center_y - height/2, center_y + height/2]
    
    return rect_x, rect_y, line_x, line_y

def _add_window_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None
) -> None:
    """Add windows to the plot as white squares with a single thick line inside."""
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
            if window_storey and window_storey != storey_name:
                print(f"Window {window_id} not in storey {storey_name}")
                continue
            
        # Get window vertices and calculate dimensions
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
            print(f"No valid 2D vertices found for window {window_id}")
            continue
            
        # Calculate window center and dimensions
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        width = max_x - min_x
        height = max_y - min_y
        
        # Calculate center point
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Create window symbol
        rect_x, rect_y, line_x, line_y = _create_window_symbol(width, height, center_x, center_y)
        
        # Add the window rectangle without border
        fig.add_trace(go.Scatter(
            x=rect_x,
            y=rect_y,
            fill='toself',
            fillcolor='white',
            line=dict(width=0),  # No border
            mode='lines',
            showlegend=False,
            zorder=2
        ))
        
        # Add the line
        fig.add_trace(go.Scatter(
            x=line_x,
            y=line_y,
            line=dict(color='black', width=2),  # Thicker line
            mode='lines',
            showlegend=False,
            zorder=2
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