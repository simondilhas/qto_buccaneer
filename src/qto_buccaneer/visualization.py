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
    
    # Convert font settings to Plotly format
    layout_settings = {
        'title': {
            'text': defaults.get('title', ''),
            'font': {
                'family': defaults.get('font_family', 'Arial'),
                'size': defaults.get('title_size', 24)
            }
        },
        'font': {
            'family': defaults.get('font_family', 'Arial'),
            'size': defaults.get('text_size', 12)
        },
        'showlegend': defaults.get('show_legend', True),
        'paper_bgcolor': defaults.get('background_color', 'white'),
        'plot_bgcolor': defaults.get('background_color', 'white'),  # Add plot background color
        'margin': {
            'l': defaults.get('margin', {}).get('left', 50),
            'r': defaults.get('margin', {}).get('right', 50),
            't': defaults.get('margin', {}).get('top', 50),
            'b': defaults.get('margin', {}).get('bottom', 50)
        }
    }
    
    # For 2D plots, ensure proper 2D layout
    if plot_config.get('mode') == 'floor_plan':
        layout_settings.update({
            'scene': None,  # Remove 3D scene
            'xaxis': {
                'showgrid': False,
                'zeroline': False,
                'showticklabels': False,
                'showline': False,
                'scaleanchor': 'y',  # Keep aspect ratio
                'scaleratio': 1,  # 1:1 ratio
                'constrain': 'domain'  # Constrain the domain
            },
            'yaxis': {
                'showgrid': False,
                'zeroline': False,
                'showticklabels': False,
                'showline': False,
                'scaleanchor': 'x',  # Keep aspect ratio
                'scaleratio': 1,  # 1:1 ratio
                'constrain': 'domain'  # Constrain the domain
            },
            'width': 1000,  # Set a fixed width
            'height': 1000,  # Set a fixed height
            'autosize': False  # Disable autosize to maintain scale
        })
    
    fig.update_layout(**layout_settings)
    
    # Process each element in the plot configuration
    for element_config in plot_config.get('elements', []):
        # Determine element type from filter
        filter_str = element_config.get('filter', '')
        if 'type=IfcSpace' in filter_str:
            _add_spaces_to_plot(fig, loader, element_config, plot_settings, storey_name, plot_config)
        elif 'type=IfcBuildingStorey' in filter_str:
            _add_storeys_to_plot(fig, loader, element_config, plot_settings)
        else:
            _add_elements_to_plot(fig, loader, element_config, plot_settings)

def _add_spaces_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    storey_name: Optional[str] = None,
    plot_config: Optional[Dict] = None
) -> None:
    """Add spaces to the plot.
    
    Args:
        fig: Plotly Figure to add spaces to
        loader: IfcJsonLoader instance
        element_config: Configuration for space visualization
        plot_settings: General plot settings
        storey_name: Optional storey name for filtering
        plot_config: Configuration for the entire plot
    """
    # Parse filter string
    filter_str = element_config.get('filter', '')
    predefined_types = []
    if 'PredefinedType=' in filter_str:
        predefined_types = [t.strip() for t in filter_str.split('PredefinedType=')[1].split(')')[0].split('OR')]
    
    # Get label settings
    label_config = element_config.get('labels', {})
    show_labels = label_config.get('show', False)
    label_properties = label_config.get('properties', [])
    label_size = label_config.get('size', 10)
    
    # Get color settings
    color_by = element_config.get('color_by', None)
    
    # Get all spaces using the by_type index
    space_ids = loader.by_type_index.get('IfcSpace', [])
    
    # First collect all spaces and calculate totals
    spaces_by_group = {}
    for space_id in space_ids:
        space = loader.properties['elements'].get(str(space_id))
        if not space:
            continue
            
        # Check predefined type filter
        space_type = space.get('properties', {}).get('PredefinedType', '')
        if predefined_types and space_type not in predefined_types:
            continue
            
        # Check storey filter if specified
        if storey_name:
            space_storey = loader.get_storey_for_space(space['ifc_global_id'])
            if space_storey != storey_name:
                continue
        
        # Get group value
        group_value = None
        if color_by:
            if color_by in space.get('properties', {}):
                group_value = space['properties'][color_by]
            elif color_by in space:
                group_value = space[color_by]
        
        if group_value is None:
            group_value = 'Unknown'
            
        # Calculate area
        area = 0.0
        if 'Qto_SpaceBaseQuantities.NetFloorArea' in space.get('properties', {}):
            area = float(space['properties']['Qto_SpaceBaseQuantities.NetFloorArea'])
        elif 'Qto_SpaceBaseQuantities.NetFloorArea' in space:
            area = float(space['Qto_SpaceBaseQuantities.NetFloorArea'])
        
        # Add to group
        if group_value not in spaces_by_group:
            spaces_by_group[group_value] = {
                'spaces': [],
                'total_area': 0.0
            }
        spaces_by_group[group_value]['spaces'].append(space)
        spaces_by_group[group_value]['total_area'] += area
    
    # Create color map
    colors = ['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink', 'lightskyblue']
    color_map = {group: colors[i % len(colors)] for i, group in enumerate(sorted(spaces_by_group.keys()))}
    
    # Now add traces for each group
    for group_value, group_data in spaces_by_group.items():
        # Add each space in the group
        for i, space in enumerate(group_data['spaces']):
            _add_single_space_to_plot(
                fig, loader, space, storey_name,
                show_labels, label_properties, label_size,
                color_by, plot_settings, element_config,
                is_2d=plot_config.get('mode') == 'floor_plan' if plot_config else False,
                group_name=f"{group_value} ({group_data['total_area']:.2f} m²)",
                color=color_map[group_value],
                legendgroup=group_value,
                show_in_legend=(i == 0)  # Only show the first space in legend
            )

def _add_single_space_to_plot(
    fig: go.Figure,
    loader: IfcJsonLoader,
    space: Dict,
    storey_name: Optional[str],
    show_labels: bool,
    label_properties: List[str],
    label_size: int,
    color_by: Optional[str],
    plot_settings: Dict,
    element_config: Dict,
    is_2d: bool = False,
    group_name: Optional[str] = None,
    color: Optional[str] = None,
    legendgroup: Optional[str] = None,
    show_in_legend: bool = True
) -> None:
    """Add a single space to the plot.
    
    Args:
        fig: Plotly Figure to add space to
        loader: IfcJsonLoader instance
        space: Space properties dictionary
        storey_name: Optional storey name for grouping
        show_labels: Whether to show labels
        label_properties: List of properties to show in labels
        label_size: Size of label text
        color_by: Property to color by
        plot_settings: General plot settings
        element_config: Configuration for this element type
        is_2d: Whether this is a 2D floor plan view
        group_name: Optional name for the group in the legend
        color: Optional color for the space
        legendgroup: Optional group name for legend grouping
        show_in_legend: Whether to show this trace in the legend
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
    
    if is_2d:
        # For 2D view, create a filled polygon with sharp corners
        fig.add_trace(go.Scatter(
            x=x + [x[0]],  # Close the polygon
            y=y + [y[0]],  # Close the polygon
            fill='toself',
            name=group_name,
            fillcolor=color,
            line=dict(
                color='black',
                width=1,
                shape='linear'  # This ensures sharp corners
            ),
            mode='lines',  # Only show lines, no markers
            opacity=0.8,
            showlegend=show_in_legend,
            legendgroup=legendgroup
        ))
    else:
        # For 3D view, create a mesh
        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            name=group_name,
            color=color,
            opacity=0.8,
            showlegend=show_in_legend,
            legendgroup=legendgroup
        ))
    
    if show_labels:
        # Add text at the center of the space
        center_x = sum(x) / len(x)
        center_y = sum(y) / len(y)
        center_z = sum(z) / len(z) if not is_2d else 0
        
        # Build label text from properties
        label_text = []
        for prop in label_properties:
            if prop == 'LongName':
                if prop in space.get('properties', {}):
                    label_text.append(space['properties'][prop])
                elif prop in space:
                    label_text.append(space[prop])
                label_text.append('')  # Add extra newline after LongName
            elif prop == 'Qto_SpaceBaseQuantities.NetFloorArea':
                if prop in space.get('properties', {}):
                    area = float(space['properties'][prop])
                    label_text.append(f"{area:.2f} m²")
                elif prop in space:
                    area = float(space[prop])
                    label_text.append(f"{area:.2f} m²")
        
        if is_2d:
            fig.add_trace(go.Scatter(
                x=[center_x],
                y=[center_y],
                text=['\n'.join(label_text)],
                mode='text',
                showlegend=False,
                textfont=dict(
                    size=label_size,
                    family=plot_settings['defaults']['font_family']
                )
            ))
        else:
            fig.add_trace(go.Scatter3d(
                x=[center_x],
                y=[center_y],
                z=[center_z],
                text=['\n'.join(label_text)],
                mode='text',
                showlegend=False,
                textfont=dict(
                    size=label_size,
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