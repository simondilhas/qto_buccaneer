import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple
import yaml
from pathlib import Path
from datetime import datetime
import json
import math

from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader
from qto_buccaneer.utils.plots_utils import (
    parse_filter,
    element_matches_conditions,
    apply_layout_settings
)
from qto_buccaneer.plots_utils.filter_parser import FilterParser

def create_floorplan_per_storey(
    geometry_dir: str,
    properties_path: str,
    config_path: str,
    output_dir: str,
    plot_name: str,
) -> Dict[str, str]:
    """Create floor plan visualizations for each storey.
    
    Args:
        geometry_dir: Directory containing geometry JSON files (e.g., IfcSpace.json, IfcDoor.json)
        properties_path: Path to properties JSON file
        config_path: Path to plot configuration YAML file
        output_dir: Output directory for the visualizations
        plot_name: Name of the plot to create

    Returns:
        Dictionary mapping storey names to their output HTML, png, and json file paths

    Raises:
        FileNotFoundError: If required geometry files are missing
    """
    # Load data
    print(f"Loading geometry data from {geometry_dir}...")
    geometry_data = []
    
    # Check for required geometry files
    geometry_dir = Path(geometry_dir)
    required_files = {
        'IfcSpace.json': 'space',
        'IfcDoor.json': 'door',
        'IfcWindow.json': 'window'
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
    for geometry_file in geometry_dir.glob("*.json"):
        if geometry_file.name != 'metadata.json' and geometry_file.name != 'error.json':
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
        plot_name=plot_name,
        file_info=file_info
    )
    
    # Save the plots
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    storey_to_output_path = {}
    for storey_name, plot in plots.items():
        output_path = output_dir / f"{plot_name}_{storey_name}.html"
        plot.write_html(str(output_path))
        plot.write_json(str(output_path.with_suffix('.json')))
        plot.write_image(str(output_path.with_suffix('.png')))
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
    print(f"\nProcessing plot creation for storey: {storey_name}")
    
    # Apply layout settings
    apply_layout_settings(fig, plot_settings)
    
    # Get coordinates for current storey
    current_x_coords, current_y_coords = _get_current_storey_coordinates(loader, storey_name, plot_config)
    
    print(f"Found {len(current_x_coords)} coordinates for current storey")
    
    # Update layout with calculated bounds
    if current_x_coords and current_y_coords:
        optimal_layout = _calculate_optimal_layout(current_x_coords, current_y_coords)
        fig.update_layout(**optimal_layout)
    
    # Process each element in the plot configuration
    for element_config in plot_config.get('elements', []):
        print(f"\nProcessing element: {element_config.get('name', 'unnamed')}")
        _process_element(fig, loader, element_config, plot_settings, storey_name, plot_config)
    
    # Add scale bar for 2D plots
    if plot_config.get('mode') == 'floor_plan' and current_x_coords and current_y_coords:
        _add_scale_bar(fig, [min(current_x_coords), max(current_x_coords)], [min(current_y_coords), max(current_y_coords)])

def _get_current_storey_coordinates(
    loader: IfcJsonLoader,
    storey_name: Optional[str],
    plot_config: Dict
) -> Tuple[List[float], List[float]]:
    """Get coordinates from current storey for scale bar."""
    x_coords = []
    y_coords = []
    if plot_config.get('mode') == 'floor_plan':
        # Get all spaces in the current storey
        space_ids = loader.get_spaces_in_storey(storey_name) if storey_name else []
        print(f"Found {len(space_ids)} spaces in storey {storey_name}")
        
        for space_id in space_ids:
            # Ensure space_id is a string
            space_id_str = str(space_id)
            geometry = loader.get_geometry(space_id_str)
            if geometry and 'vertices' in geometry:
                x_coords.extend([v[0] for v in geometry['vertices']])
                y_coords.extend([v[1] for v in geometry['vertices']])
    return x_coords, y_coords

def _process_element(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    storey_name: Optional[str],
    plot_config: Dict
) -> None:
    """Process a single element from the configuration."""
    filter_str = element_config.get('filter', '')
    element_type, conditions = parse_filter(filter_str)
    
    if element_type == 'IfcSpace':
        _add_spaces_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
    elif element_type == 'IfcDoor':
        _add_door_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
    elif element_type == 'IfcWindow':
        _add_window_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
    elif element_type == 'IfcBuildingStorey':
        pass  # Storey visualization not implemented
    elif element_type == 'IfcWallStandardCase':
        print("Starting wall visualization")  # Debug log
        _add_wall_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
        print("Wall visualization completed")  # Debug log
    else:
        _add_geometry_to_plot(
            fig, loader, element_config, element_type, conditions, plot_settings,
            storey_name, plot_config, element_type == 'IfcSpace'
        )

def _add_spaces_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    element_type: Optional[str],
    conditions: List[List[str]],
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None
) -> None:
    """Add spaces to the plot with consistent coloring."""
    # Get color settings
    color_by = element_config.get('color_by')
    fixed_color = element_config.get('color')
    
    # Get spaces that match the filter conditions and are in the current storey
    space_ids = loader.get_spaces_in_storey(storey_name) if storey_name else []
    matching_spaces = []
    
    for space_id in space_ids:
        # Ensure space_id is a string
        space_id_str = str(space_id)
        space = loader.properties['elements'].get(space_id_str)
        if space and _space_matches_conditions(space, element_type, conditions):
            matching_spaces.append(space)
    
    # Group spaces and calculate areas
    grouped_spaces, total_areas = _group_spaces(matching_spaces, color_by, element_config)
    
    # Add each group to the plot
    for group_value, space_group in grouped_spaces.items():
        color = fixed_color or _get_color_for_group(group_value)
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

def _get_color_for_group(group_value: str) -> str:
    """Get a consistent color for a group value."""
    colors = [
        'lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 
        'lightpink', 'lightskyblue', 'lightseagreen', 'lightsteelblue',
        'lightgoldenrodyellow', 'lightcyan', 'lightgray'
    ]
    return colors[hash(group_value) % len(colors)]

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
    is_gfa = False
    if 'LongName' in space:
        space_name = space['LongName']
    elif 'Name' in space:
        space_name = space['Name']
    if 'Qto_SpaceBaseQuantities.NetFloorArea' in space:
        space_area = space['Qto_SpaceBaseQuantities.NetFloorArea']
        is_gfa = True
    
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
        
        # Calculate room dimensions
        min_x, max_x = min(x), max(x)
        min_y, max_y = min(y), max(y)
        room_width = max_x - min_x
        room_height = max_y - min_y
        
        # Build label text with individual space area
        label_text = [space_name]
        if space_area:
            label_text.append(f"{space_area:.1f} m²")
        
        # Estimate text dimensions based on character count and font size
        text = '\n'.join(label_text)
        char_count = max(len(line) for line in label_text)
        line_count = len(label_text)
        font_size = plot_settings['defaults']['text_size']
        
        # More realistic text dimension estimation
        # Assuming each character is ~0.5 units wide and line height is ~1.2 units
        text_width = char_count * 0.5
        text_height = line_count * 1.2
        
        # First check if room is long enough to consider rotation
        is_long_room = room_height > room_width * 1.5
        
        # Then check if text would fit better rotated
        fits_horizontally = text_width < room_width * 0.8
        fits_vertically = text_height < room_width * 0.8
        
        # Only rotate if:
        # 1. Room is long enough AND
        # 2. Text fits better vertically than horizontally
        needs_rotation = is_long_room and (not fits_horizontally or fits_vertically)
        
        # Debug information
        print(f"Room dimensions: {room_width:.1f}x{room_height:.1f}")
        print(f"Text dimensions: {text_width:.1f}x{text_height:.1f}")
        print(f"Is long room: {is_long_room}")
        print(f"Fits horizontally: {fits_horizontally}")
        print(f"Fits vertically: {fits_vertically}")
        print(f"Rotation needed: {needs_rotation}")
        print(f"Height/Width ratio: {room_height/room_width:.2f}")
        print(f"Text width/room width: {text_width/room_width:.2f}")
        print(f"Text height/room width: {text_height/room_width:.2f}")
        
        if view == '2d':
            # For 2D view, position text at the guaranteed inside point
            rotation = -90 if needs_rotation else 0  # Rotate text by 180 degrees if room is longer than wide
            fig.add_annotation(
                x=text_x,
                y=text_y,
                text=text,
                showarrow=False,
                font=dict(
                    size=plot_settings['defaults']['text_size'],
                    family=plot_settings['defaults']['font_family']
                ),
                textangle=rotation,
                xanchor='center',
                yanchor='middle'
            )
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
    element_type: Optional[str],
    conditions: List[List[str]],
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None,
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
            _add_door_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
        elif element_type == 'IfcWindow':
            print("Starting window visualization")  # Debug log
            _add_window_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
            print("Window visualization completed")  # Debug log
        elif element_type == 'IfcWallStandardCase':
            print("Starting wall visualization")  # Debug log
            _add_wall_to_plot(fig, loader, element_config, element_type, conditions, plot_settings, storey_name, plot_config)
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
    plot_config: Optional[Dict] = None
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
        color = _get_color_for_group(group_value)
        
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

def _space_matches_conditions(space: Dict, element_type: Optional[str], conditions: List[List[str]]) -> bool:
    """Check if a space matches the filter conditions."""
    return FilterParser.element_matches_conditions(space, element_type, conditions)

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

def _add_scale_bar(
    fig: go.Figure,
    x_range: List[float],
    y_range: List[float]
) -> None:
    """Add a scale bar to the floor plan visualization.
    
    Args:
        fig: The plotly figure to add the scale bar to
        x_range: List of [min_x, max_x] coordinates
        y_range: List of [min_y, max_y] coordinates
    """
    # Calculate the size of the plot
    x_size = x_range[1] - x_range[0]
    y_size = y_range[1] - y_range[0]
    
    # Determine a reasonable scale bar length (10% of the smaller dimension)
    scale_length = min(x_size, y_size) * 0.1
    
    # Round the scale length to a nice number
    nice_length = _round_to_nice_number(scale_length)
    
    # Position the scale bar in the bottom right corner
    # Leave some margin (5% of the respective dimension)
    x_margin = x_size * 0.05
    y_margin = y_size * 0.05
    
    # Calculate the position
    x_start = x_range[1] - x_margin - nice_length
    x_end = x_range[1] - x_margin
    y_pos = y_range[0] + y_margin
    
    # Add the scale bar line
    fig.add_trace(go.Scatter(
        x=[x_start, x_end],
        y=[y_pos, y_pos],
        mode='lines',
        line=dict(color='black', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Add tick marks
    tick_length = y_size * 0.01  # 1% of y dimension
    fig.add_trace(go.Scatter(
        x=[x_start, x_start],
        y=[y_pos - tick_length/2, y_pos + tick_length/2],
        mode='lines',
        line=dict(color='black', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=[x_end, x_end],
        y=[y_pos - tick_length/2, y_pos + tick_length/2],
        mode='lines',
        line=dict(color='black', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Add the scale label
    fig.add_annotation(
        x=(x_start + x_end) / 2,
        y=y_pos + tick_length,
        text=f"{nice_length:.1f} m",
        showarrow=False,
        font=dict(size=12),
        xanchor='center',
        yanchor='bottom'
    )

def _round_to_nice_number(value: float) -> float:
    """Round a number to a nice, human-readable value.
    
    Args:
        value: The value to round
        
    Returns:
        A rounded value that is a multiple of 1, 2, or 5 times a power of 10
    """
    # Find the order of magnitude
    magnitude = 10 ** math.floor(math.log10(value))
    
    # Normalize the value
    normalized = value / magnitude
    
    # Round to the nearest nice number
    if normalized < 1.5:
        nice = 1
    elif normalized < 3:
        nice = 2
    elif normalized < 7:
        nice = 5
    else:
        nice = 10
    
    return nice * magnitude