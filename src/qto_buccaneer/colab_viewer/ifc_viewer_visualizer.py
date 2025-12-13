"""
3D Visualization Module for qto_buccaneer Viewer
Handles creation and configuration of 3D mesh visualizations.
"""

import json
import numpy as np
import plotly.graph_objects as go
from .ifc_viewer_geometry import GeometryExtractor


class Visualizer3D:
    """Creates and manages 3D visualizations of IFC elements."""
    
    def __init__(self, geometry_extractor=None):
        """
        Initialize 3D visualizer.
        
        Parameters:
        -----------
        geometry_extractor : GeometryExtractor, optional
            Instance of GeometryExtractor with color configuration
        """
        self.fig = go.Figure()
        self.mesh_dict = {}
        self.original_colors = {}
        self.visibility = {}
        self.properties = {}
        self.selected_mesh = [None]
        self.geometry_extractor = geometry_extractor or GeometryExtractor()

    def add_mesh_from_element(self, element, mesh_json, hierarchy_path, qto_props):
        """
        Add a mesh to the visualization from an IFC element.
        
        Parameters:
        -----------
        element : IFC element
            The IFC element to visualize
        mesh_json : str
            JSON string containing mesh geometry data
        hierarchy_path : str
            Path in hierarchy (e.g., "Storey_01/IfcWall")
        qto_props : dict
            Quantity takeoff properties
        """
        try:
            mesh_data = json.loads(mesh_json)
            for element_data in mesh_data["elements"]:
                mesh_id = element_data["mesh_id"]
                mesh_info = next((m for m in mesh_data["meshes"] if m["mesh_id"] == mesh_id), None)
                if not mesh_info:
                    continue
                
                vertices = GeometryExtractor.transform_coordinates(
                    mesh_info["coordinates"],
                    element_data["rotation"],
                    element_data["vector"]
                )
                indices = np.array(mesh_info["indices"], dtype=np.uint32)
                element_name = element.Name or f"{element.is_a()}_{element.GlobalId[:8]}"
                full_name = f"{hierarchy_path}/{element_name}"
                
                # Try to get color from YAML config first, fall back to mesh data
                config_color = self.geometry_extractor.get_color_for_element(element)
                
                if config_color:
                    # Use color from YAML config
                    if config_color.startswith('#'):
                        hex_color = config_color
                    else:
                        # Convert named color to hex (simplified - plotly handles this)
                        hex_color = config_color
                else:
                    # Fall back to color from mesh data
                    r, g, b = element_data["color"]["r"], element_data["color"]["g"], element_data["color"]["b"]
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                
                mesh = go.Mesh3d(
                    x=vertices[:, 0],
                    y=vertices[:, 1],
                    z=vertices[:, 2],
                    i=indices[0::3],
                    j=indices[1::3],
                    k=indices[2::3],
                    color=hex_color,
                    opacity=element_data["color"]["a"] / 255,
                    name=full_name,
                    visible=True
                )
                self.fig.add_trace(mesh)
                self.mesh_dict[full_name] = mesh
                self.original_colors[full_name] = hex_color
                self.visibility[full_name] = True
                self.properties[full_name] = {
                    "Name": element_name,
                    "Type": element.is_a(),
                    "GUID": element.GlobalId,
                    "Hierarchy": hierarchy_path,
                    **element_data["info"],
                    **qto_props
                }
        except Exception as e:
            print(f"⚠️ Error processing mesh for {element.GlobalId}: {e}")

    def configure_layout(self):
        """Configure the layout of the 3D visualization."""
        self.fig.update_layout(
            scene=dict(
                xaxis=dict(title="X"),
                yaxis=dict(title="Y (Vertical)"),
                zaxis=dict(title="Z"),
                aspectmode="data",
                camera=dict(
                    up=dict(x=0, y=1, z=0),
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            showlegend=False,
            width=800,
            height=600,
            margin=dict(l=0, r=0, t=0, b=0)
        )
