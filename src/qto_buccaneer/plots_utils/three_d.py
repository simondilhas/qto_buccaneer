import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple
import yaml
from pathlib import Path
from datetime import datetime
import json

from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader
from qto_buccaneer.utils.plots_utils import apply_layout_settings

def create_3d_visualization(
    geometry_dir: str,
    properties_path: str,
    config_path: str,
    output_dir: str,
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

    Raises:
        FileNotFoundError: If required geometry files are missing
    """
    # Load data
    print(f"Loading geometry data from {geometry_dir}...")
    geometry_data = []
    
    # Check for required geometry files
    geometry_dir = Path(geometry_dir)
    required_files = {
        'IfcWindow.json': 'window',
        'IfcCovering.json': 'covering',
        'IfcSlab.json': 'slab',
        'IfcDoor.json': 'door'
    }
    
    missing_files = []
    for file_pattern, element_type in required_files.items():
        if not list(geometry_dir.glob(file_pattern)):
            missing_files.append(f"{file_pattern} (required for {element_type} visualization)")
    
    if missing_files:
        raise FileNotFoundError(
            f"Missing required geometry files in {geometry_dir}:\n" +
            "\n".join(f"- {file}" for file in missing_files)
        )
    
    # Load all geometry files in the directory
    for geometry_file in geometry_dir.glob("*.json"):
        if geometry_file.name in ['metadata.json', 'error.json']:
            continue
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

    # Create the 3D visualization
    print("\nCreating 3D visualization...")
    plots = create_single_plot(
        geometry_json=geometry_data,
        properties_json=properties_data,
        config=config,
        plot_name=plot_name,
        file_info=file_info
    )
    
    # Save the plot
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the plot name directly as the output file name
    output_path = output_dir / f"{plot_name}.html"
    plots['default'].write_html(str(output_path))
    plots['default'].write_json(str(output_path.with_suffix('.json')))
    plots['default'].write_image(str(output_path.with_suffix('.png')))
    print(f"Saved 3D visualization to {output_path}")
    
    return str(output_path)

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
        # Create single figure for 3D view
        fig = go.Figure()
        _process_plot_creation(
            fig, loader, plot_name, plot_config,
            config['plot_settings'], file_info
        )
        
        # Apply 3D view settings with completely hidden axes
        fig.update_layout(
            showlegend=False,  # Disable legend
            scene=dict(
                xaxis=dict(
                    visible=False,
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False,
                    showline=False,
                    showbackground=False,
                    showspikes=False,
                    showaxeslabels=False,
                ),
                yaxis=dict(
                    visible=False,
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False,
                    showline=False,
                    showbackground=False,
                    showspikes=False,
                    showaxeslabels=False,
                ),
                zaxis=dict(
                    visible=False,
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False,
                    showline=False,
                    showbackground=False,
                    showspikes=False,
                    showaxeslabels=False,
                ),
                camera=dict(
                    up=dict(x=0, y=0, z=1),
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=1.5, y=1.5, z=1.5)
                ),
                aspectmode='data',
                bgcolor='rgba(0,0,0,0)'
            ),
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
    file_info: Optional[Dict] = None
) -> None:
    """Process plot creation based on configuration."""
    # Apply layout settings
    apply_layout_settings(fig, plot_settings)
    
    # Process each element in the plot configuration
    for element_config in plot_config.get('elements', []):
        _process_element(fig, loader, element_config, plot_settings, plot_config)

def parse_filter_string(filter_str: str) -> Tuple[Optional[str], List[List[str]]]:
    """Parse a filter string into element type and conditions."""
    if not filter_str:
        return None, []
        
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

def _process_element(
    fig: go.Figure,
    loader: IfcJsonLoader,
    element_config: Dict,
    plot_settings: Dict,
    plot_config: Dict
) -> None:
    """Process a single element from the configuration."""
    filter_str = element_config.get('filter', '')
    element_type, conditions = parse_filter_string(filter_str)
    
    if not element_type:
        return
        
    # Get all elements of the specified type
    element_ids = loader.by_type_index.get(element_type, [])
    
    for element_id in element_ids:
        # Get the element using the numeric ID
        element = loader.properties['elements'].get(str(element_id))
        if not element:
            continue
            
        # Check if element matches filter conditions
        if not _element_matches_conditions(element, conditions):
            continue
            
        # Get geometry using the numeric ID
        geometry = loader.get_geometry(str(element_id))
        if not geometry or 'vertices' not in geometry:
            continue
            
        # Get vertices and faces
        vertices = geometry['vertices']
        faces = geometry['faces']
        
        x = [v[0] for v in vertices]
        y = [v[1] for v in vertices]
        z = [v[2] for v in vertices]
        
        i = [f[0] for f in faces]
        j = [f[1] for f in faces]
        k = [f[2] for f in faces]
        
        # Get color from config or use default
        color = element_config.get('color', 'lightgray')
        
        # Add mesh to plot with improved visibility settings
        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            name=element_config.get('name', element_type),
            color=color,
            opacity=1.0,  # Full opacity
            showlegend=False,  # Disable legend for each element
            lighting=dict(
                ambient=0.6,  # Increase ambient light
                diffuse=0.8,  # Increase diffuse light
                specular=0.2,  # Reduce specular highlights
                roughness=0.5  # Medium roughness
            ),
            flatshading=True,  # Enable flat shading for better visibility
            hoverinfo='name'
        ))

def _element_matches_conditions(element: Dict, conditions: List[List[str]]) -> bool:
    """Check if an element matches all filter conditions."""
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
                if key in element:
                    if str(element[key]).lower() == value.lower():
                        or_group_matched = True
                        break
        
        # If no condition in the OR group matched, the whole AND fails
        if not or_group_matched:
            return False
    
    # All conditions passed
    return True 