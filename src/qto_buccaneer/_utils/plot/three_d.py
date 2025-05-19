import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple, Union
import yaml
from pathlib import Path
from datetime import datetime
import json
import math
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt

from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader
from qto_buccaneer._utils.plot.plots_utils import (
    parse_filter,
    element_matches_conditions
)
from qto_buccaneer.utils.metadata_filter import MetadataFilter

# NOT working

def order_ring(vertices, indices):
    # Get the 2D coordinates (X, Y) of the ring
    pts = np.array([vertices[i][:2] for i in indices])
    center = pts.mean(axis=0)
    angles = np.arctan2(pts[:,1] - center[1], pts[:,0] - center[0])
    order = np.argsort(angles)
    return [indices[i] for i in order]

def create_3d_visualization(
    geometry_dir: Union[str, Path],
    properties_path: Union[str, Path],
    config_path: Union[str, Path],
    output_dir: Union[str, Path],
    plot_name: str = "exterior_elements"
) -> str:
    """Create a 3D visualization of the building model.
    
    Args:
        geometry_dir: Directory containing geometry JSON files
        properties_path: Path to properties JSON file
        config_path: Path to plot configuration YAML file
        output_dir: Output directory for the visualization
        plot_name: Name of the plot configuration to use (default: "exterior_elements")
        
    Returns:
        Path to the generated HTML file
    """
    # Convert all paths to Path objects
    geometry_dir = Path(geometry_dir)
    properties_path = Path(properties_path)
    config_path = Path(config_path)
    output_dir = Path(output_dir)
    
    # Load plot configuration
    print(f"Loading plot configuration from {config_path}...")
    config = load_plot_config(config_path)
    
    # Create file info
    file_info = {
        "file_name": properties_path.stem,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Create the 3D visualization
    print("\nCreating 3D visualization...")
    plots = create_single_plot(
        geometry_dir=geometry_dir,
        properties_path=properties_path,
        config=config,
        plot_name=plot_name,
        file_info=file_info
    )
    
    # Save the plot
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the plot name directly as the output file name
    output_path = output_dir / f"{plot_name}.html"
    plots['default'].write_html(str(output_path))
    plots['default'].write_json(str(output_path.with_suffix('.json')))
    plots['default'].write_image(str(output_path.with_suffix('.png')))
    print(f"Saved 3D visualization to {output_path}")
    
    return str(output_path)

def load_plot_config(config_path: Union[str, Path]) -> Dict:
    """Load plot configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def create_single_plot(
    geometry_dir: Union[str, Path],
    properties_path: Union[str, Path],
    config: Dict,
    plot_name: str,
    file_info: Optional[Dict] = None
) -> Dict[str, go.Figure]:
    """Create a single plot based on the configuration."""
    if plot_name not in config.get('plots', {}):
        raise ValueError(f"Plot '{plot_name}' not found in configuration")
    
    # Initialize loader with the geometry directory and properties file
    loader = IfcJsonLoader(properties_path, geometry_dir)
    
    # Get plot configuration and settings
    plot_config = config['plots'][plot_name]
    plot_settings = config.get('plot_settings', {})
    
    # Initialize color mapping from config and used colors set
    color_mapping = plot_settings.get('color_mapping', {})
    used_colors = set(color_mapping.values())
    
    try:
        # Create single figure for 3D view
        fig = go.Figure()
        _process_plot_creation(
            fig, loader, plot_name, plot_config,
            plot_settings, file_info, color_mapping, used_colors
        )
        
        # Get 3D view settings from config
        view_mode = plot_settings.get('modes', {}).get('3d_view', {})
        scene_settings = view_mode.get('scene', {})
        
        # Apply 3D view settings
        fig.update_layout(
            showlegend=True,  # Enable legend for 3D view
            scene=scene_settings,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0, pad=0)
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
    color_mapping: Dict[str, str] = None,
    used_colors: set = None
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
        _process_element(fig, loader, element_config, plot_settings, plot_config, color_mapping, used_colors)

def _process_element(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    plot_config: Dict,
    color_mapping: Dict[str, str] = None,
    used_colors: set = None
) -> None:
    """Process a single element from the configuration."""
    filter_str = element_config.get('filter', '')
    element_type, conditions = parse_filter(filter_str)
    
    if not element_type:
        return
        
    print(f"\nProcessing elements of type: {element_type}")
    print(f"Filter string: {filter_str}")
    print(f"Conditions: {conditions}")
    
    # Get filtered elements using the loader's filter method
    filtered_elements = loader.get_elements_by_filter(filter_str)
    print(f"Found {len(filtered_elements)} elements matching filter")
    
    # Group elements by color_by property if specified
    color_by = element_config.get('color_by')
    grouped_elements = {}
    
    elements_with_geometry = 0
    
    for element_id, element in filtered_elements.items():
        # Get geometry using the numeric ID
        geometry = loader.get_geometry(str(element_id))
        if not geometry:
            print(f"Warning: No geometry found for element {element_id}")
            continue
        if 'vertices' not in geometry:
            print(f"Warning: No vertices found for element {element_id}")
            continue
            
        elements_with_geometry += 1
        
        # Get the color group value
        group_value = None
        if color_by:
            if color_by in element.get('properties', {}):
                group_value = element['properties'][color_by]
            elif color_by in element:
                group_value = element[color_by]
        else:
            group_value = element_config.get('name', 'Unknown')
        
        if not group_value:
            group_value = 'Unknown'
            
        if group_value not in grouped_elements:
            grouped_elements[group_value] = []
            
        grouped_elements[group_value].append((element, geometry))
    
    print(f"Elements with valid geometry: {elements_with_geometry}")
    print(f"Number of groups: {len(grouped_elements)}")
    
    # Check if labels should be shown
    show_labels = element_config.get('label', True)  # Default to True if not specified
    
    # Add each group of elements to the plot
    for group_value, elements in grouped_elements.items():
        print(f"Processing group: {group_value} with {len(elements)} elements")
        # Get color for this group
        color = element_config.get('color_map', {}).get(group_value) or \
                element_config.get('color') or \
                _get_color_for_group(group_value, color_mapping, used_colors)
        
        # Only add dummy trace for legend if labels are enabled
        if show_labels:
            fig.add_trace(go.Mesh3d(
                x=[None], y=[None], z=[None],
                i=[None], j=[None], k=[None],
                name=group_value,
                color=color,
                showlegend=True,
                legendgroup=group_value
            ))
        
        # Add each element as a separate trace but with the same legend name
        for element, geometry in elements:
            vertices = geometry['vertices']
            polygons = geometry.get('polygons', [])
            if element.get('ifc_type', '').lower() in ['ifcspace', 'ifcslab', 'ifcwallstandardcase']:
                # Only plot the lower polygon as a flat surface, using the correct order from 'outer'
                if len(vertices) >= 3 and polygons:
                    _add_flat_base_polygon(fig, vertices, polygons, color=color, opacity=1.0, show_labels=show_labels)
                continue
            # if element.get('ifc_type', '').lower() in ['ifcwindow', 'ifcdoor']:
            #     # Render as surface (use first polygon)
            #     if len(geometry.get('polygons', [])) >= 1:
            #         print("I want a box not a mesh")
            #         #X_add_surface_mesh(fig, vertices, geometry['polygons'][0]['outer'], color=color, opacity=1.0, show_labels=show_labels)
            #     continue
            # Default: original logic for other elements
            x = [v[0] for v in vertices]
            y = [v[1] for v in vertices]
            z = [v[2] for v in vertices]
            faces = []
            if 'polygons' in geometry and geometry['polygons']:
                for polygon in geometry['polygons']:
                    outer = polygon['outer']
                    for i in range(1, len(outer) - 1):
                        ia, ib, ic = outer[0], outer[i], outer[i+1]
                        faces.append([ia, ib, ic])
            if not faces:
                print(f"Warning: No faces generated for element {element_id}")
                continue
            i = [f[0] for f in faces]
            j = [f[1] for f in faces]
            k = [f[2] for f in faces]
            fig.add_trace(go.Mesh3d(
                x=x, y=y, z=z,
                i=i, j=j, k=k,
                name=None,  # No name for actual elements
                color=color,
                opacity=1.0,  # Full opacity
                showlegend=False,  # Don't show in legend
                legendgroup=group_value if show_labels else None,  # Only group if labels are enabled
                lighting=dict(
                    ambient=0.4,  # More contrast
                    diffuse=0.9,
                    specular=0.4,
                    roughness=0.7
                ),
                flatshading=True,  # Enable flat shading for better visibility
                hoverinfo='name' if show_labels else 'none'  # Only show hover info if labels are enabled
            ))

def _add_flat_base_polygon(fig, vertices, polygons, color='white', opacity=1.0, show_labels=False):
    # Use the outer polygon indices for correct order
    if not polygons or 'outer' not in polygons[0]:
        return
    outer = polygons[0]['outer']
    base_points = [vertices[i] for i in outer]
    n = len(base_points)
    if n < 3:
        return
    # Fan triangulation
    faces = []
    for i in range(1, n - 1):
        faces.append([0, i, i + 1])
    x, y, z = zip(*base_points)
    i_idx = [f[0] for f in faces]
    j_idx = [f[1] for f in faces]
    k_idx = [f[2] for f in faces]
    fig.add_trace(go.Mesh3d(
        x=x, y=y, z=z,
        i=i_idx, j=j_idx, k=k_idx,
        name=None,
        color=color,
        opacity=opacity,
        showlegend=False,
        legendgroup=None,
        lighting=dict(
            ambient=0.4,
            diffuse=0.9,
            specular=0.4,
            roughness=0.7
        ),
        flatshading=True,
        hoverinfo='name' if show_labels else 'none'
    ))
    print('outer indices:', outer)
    print('base_points:', base_points)
    xy = np.array(base_points)
    plt.plot(xy[:,0], xy[:,1], marker='o')
    plt.show()

# def X_add_surface_mesh(fig, vertices, outer, color='white', opacity=1.0, show_labels=False):
#     z_flat = sum(vertices[i][2] for i in outer) / len(outer)
#     x = [vertices[i][0] for i in outer]
#     y = [vertices[i][1] for i in outer]
#     z = [z_flat for _ in outer]
#     faces = []
#     for i in range(1, len(outer) - 1):
#         faces.append([0, i, i+1])
#     i_idx = [f[0] for f in faces]
#     j_idx = [f[1] for f in faces]
#     k_idx = [f[2] for f in faces]
#     fig.add_trace(go.Mesh3d(
#         x=x, y=y, z=z,
#         i=i_idx, j=j_idx, k=k_idx,
#         color=color,
#         opacity=opacity,
#         showlegend=False,
#         flatshading=True,
#         hoverinfo='name' if show_labels else 'none'
#     ))

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