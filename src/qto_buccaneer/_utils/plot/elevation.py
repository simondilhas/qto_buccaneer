from typing import Union, Optional, Dict, List, Tuple
import math
from pathlib import Path
import plotly.graph_objects as go
from qto_buccaneer._utils.ifc_json_loader import IfcJsonLoader

def create_elevation_visualization(
    geometry_dir: Union[str, Path],
    properties_path: Union[str, Path],
    config_path: Union[str, Path],
    output_dir: Union[str, Path],
    plot_name: str,
    elevation_direction: str = 'north',  # 'north', 'south', 'east', 'west', or 'auto'
    facade_angle: Optional[float] = None  # Angle in degrees from north
) -> Dict[str, str]:
    """Create elevation visualizations for the building.
    
    Args:
        geometry_dir: Directory containing geometry JSON files
        properties_path: Path to properties JSON file
        config_path: Path to plot configuration YAML file
        output_dir: Output directory for the visualization
        plot_name: Name of the plot configuration to use
        elevation_direction: Direction of the elevation view ('north', 'south', 'east', 'west', 'auto')
        facade_angle: Angle in degrees from north for custom facade direction
        
    Returns:
        Dictionary mapping elevation names to their output file paths
    """
    # ... (previous initialization code remains the same)

    # If auto direction is selected, analyze the building to find main facades
    if elevation_direction == 'auto':
        facade_angles = _analyze_building_facades(loader, filtered_elements)
        output_paths = {}
        
        # Create elevation for each main facade
        for angle in facade_angles:
            direction_name = f"facade_{angle:.0f}"
            path = _create_single_elevation(
                fig, loader, filtered_elements, plot_config, plot_settings,
                color_mapping, used_colors, angle, direction_name
            )
            output_paths[direction_name] = path
            
        return output_paths
    
    # For specific direction or angle
    angle = _get_angle_from_direction(elevation_direction, facade_angle)
    return {
        elevation_direction: _create_single_elevation(
            fig, loader, filtered_elements, plot_config, plot_settings,
            color_mapping, used_colors, angle, elevation_direction
        )
    }

def _analyze_building_facades(
    loader: IfcJsonLoader,
    filtered_elements: Dict[str, Dict]
) -> List[float]:
    """Analyze the building to find main facade directions.
    
    Returns:
        List of angles (in degrees) for main facades
    """
    # Collect all wall vertices
    wall_vertices = []
    for elements in filtered_elements.values():
        for element in elements.values():
            if element.get('IfcEntity') == 'IfcWallStandardCase':
                geometry = loader.get_geometry(str(element['id']))
                if geometry and 'vertices' in geometry:
                    wall_vertices.extend(geometry['vertices'])
    
    if not wall_vertices:
        return [0, 90, 180, 270]  # Default to cardinal directions if no walls found
    
    # Calculate wall segment angles
    segment_angles = []
    for i in range(0, len(wall_vertices) - 1, 2):
        v1 = wall_vertices[i]
        v2 = wall_vertices[i + 1]
        dx = v2[0] - v1[0]
        dy = v2[1] - v1[1]
        angle = math.degrees(math.atan2(dy, dx))
        segment_angles.append(angle)
    
    # Group similar angles (within 10 degrees)
    angle_groups = {}
    for angle in segment_angles:
        normalized_angle = round(angle / 10) * 10
        if normalized_angle not in angle_groups:
            angle_groups[normalized_angle] = 0
        angle_groups[normalized_angle] += 1
    
    # Find the most common angles (main facades)
    main_angles = sorted(
        angle_groups.items(),
        key=lambda x: x[1],
        reverse=True
    )[:4]  # Take top 4 most common angles
    
    return [angle for angle, _ in main_angles]

def _get_angle_from_direction(direction: str, custom_angle: Optional[float]) -> float:
    """Convert direction string to angle in degrees."""
    if custom_angle is not None:
        return custom_angle
        
    direction_angles = {
        'north': 0,
        'east': 90,
        'south': 180,
        'west': 270
    }
    return direction_angles.get(direction.lower(), 0)

def _create_single_elevation(
    fig: go.Figure,
    loader: IfcJsonLoader,
    filtered_elements: Dict[str, Dict],
    plot_config: Dict,
    plot_settings: Dict,
    color_mapping: Dict[str, str],
    used_colors: set,
    angle: float,
    direction_name: str
) -> str:
    """Create a single elevation view at the specified angle."""
    # Create new figure
    fig = go.Figure()
    
    # Process each element type
    for element_config in plot_config.get('elements', []):
        _process_elevation_element(
            fig, loader, element_config, plot_settings,
            angle, color_mapping, used_colors
        )
    
    # Calculate bounds and set up layout
    bounds = _calculate_elevation_bounds(loader, filtered_elements, angle)
    
    # Update layout
    fig.update_layout(
        title=f"{plot_config.get('title', 'Elevation')} - {direction_name}",
        xaxis=dict(
            range=bounds['x_range'],
            title="Distance (m)",
            showgrid=True,
            zeroline=True
        ),
        yaxis=dict(
            range=bounds['y_range'],
            title="Elevation (m)",
            showgrid=True,
            zeroline=True
        ),
        showlegend=plot_config.get('show_legend', True),
        plot_bgcolor='white',
        paper_bgcolor='white',
        width=1123,
        height=794,
        autosize=False,
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=0.8,
            bgcolor='white'
        ),
        margin=dict(l=50, r=50, t=50, b=50, pad=0)
    )
    
    # Save figure
    output_path = output_dir / f"{plot_name}_{direction_name}.html"
    fig.write_html(str(output_path))
    fig.write_image(str(output_path.with_suffix('.png')))
    fig.write_json(str(output_path.with_suffix('.json')))
    
    return str(output_path)

def _process_elevation_element(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    angle: float,
    color_mapping: Dict[str, str],
    used_colors: set
) -> None:
    """Process a single element type for elevation visualization."""
    element_type = element_config.get('type', '')
    color_by = element_config.get('color_by')
    
    # Get elements of this type
    elements = loader.by_type_index.get(element_type, [])
    
    for element_id in elements:
        element = loader.properties['elements'].get(str(element_id))
        if not element:
            continue
            
        geometry = loader.get_geometry(str(element_id))
        if not geometry or 'vertices' not in geometry:
            continue
        
        # Get color based on element properties
        color = None
        if color_by and color_by in element:
            color = color_mapping.get(element[color_by])
        if not color:
            color = element_config.get('color', 'gray')
        
        # Project vertices based on angle
        vertices = geometry['vertices']
        x_coords, y_coords = _project_vertices(vertices, angle)
        
        # Add element to plot
        fig.add_trace(go.Scatter(
            x=x_coords,
            y=y_coords,
            fill='toself',
            fillcolor=color,
            line=dict(color='black', width=1),
            name=element.get('Name', element_type),
            showlegend=True
        ))

def _project_vertices(vertices: List[List[float]], angle: float) -> Tuple[List[float], List[float]]:
    """Project vertices onto a plane normal to the given angle."""
    # Convert angle to radians
    angle_rad = math.radians(angle)
    
    # Calculate rotation matrix
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    # Project vertices
    x_coords = []
    y_coords = []
    
    for vertex in vertices:
        # Rotate coordinates
        x = vertex[0] * cos_a + vertex[1] * sin_a
        y = vertex[2]  # Keep Z coordinate for elevation
        
        x_coords.append(x)
        y_coords.append(y)
    
    return x_coords, y_coords

def _calculate_elevation_bounds(
    loader: IfcJsonLoader,
    filtered_elements: Dict[str, Dict],
    angle: float
) -> Dict[str, List[float]]:
    """Calculate bounds for the elevation view."""
    x_coords = []
    y_coords = []
    
    for elements in filtered_elements.values():
        for element in elements.values():
            geometry = loader.get_geometry(str(element['id']))
            if geometry and 'vertices' in geometry:
                vertices = geometry['vertices']
                x, y = _project_vertices(vertices, angle)
                x_coords.extend(x)
                y_coords.extend(y)
    
    if not x_coords or not y_coords:
        return {'x_range': [0, 1], 'y_range': [0, 1]}
    
    # Calculate bounds with margin
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    margin = max(x_max - x_min, y_max - y_min) * 0.05
    x_min -= margin
    x_max += margin
    y_min -= margin
    y_max += margin
    
    return {
        'x_range': [x_min, x_max],
        'y_range': [y_min, y_max]
    } 