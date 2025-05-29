import plotly.graph_objects as go
import json
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
from qto_buccaneer.utils.metadata_filter import MetadataFilter
import mapbox_earcut as earcut
import numpy as np
import trimesh

class MetricVisualizer:
    """A class for visualizing BIM metrics in 3D using Plotly.
    
    This class provides functionality to load BIM geometry and metadata,
    and create 3D visualizations of different metric components using Plotly.
    
    Args:
        project_path: Path to the project directory containing geometry and metadata files
    """
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.geometry_path = self.project_path / "05_abstractbim_geometry_json"
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> pd.DataFrame:
        """Load and convert metadata to DataFrame"""
        with open(self.geometry_path / "ifc_model_metadata.json", 'r') as f:
            metadata = json.load(f)
        # Convert to DataFrame format
        return pd.DataFrame.from_dict(metadata['elements'], orient='index')
    
    def _load_geometry(self, element_type: str) -> List[Dict]:
        """Load geometry data for a specific IFC element type"""
        file_path = self.geometry_path / f"{element_type}.json"
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _create_mesh3d(self, element: Dict, color: str) -> go.Mesh3d:
        """Create a Plotly Mesh3d object from element geometry."""
        vertices = element['vertices']
        polygons = element['polygons']
        element_type = element.get('ifc_type', None)  # Get the IFC type

        x = [v[0] for v in vertices]
        y = [v[1] for v in vertices]
        z = [v[2] for v in vertices]

        i, j, k = [], [], []

        for polygon in polygons:
            outer = polygon['outer']
            holes = polygon.get('holes', [])
            # Pass element_type to triangulation
            tris = self.triangulate_3d_polygon(vertices, outer, holes, element_type)
            for a, b, c in tris:
                i.append(a)
                j.append(b)
                k.append(c)

        return go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            color=color,
            opacity=0.7,
            hoverinfo='text',
            hovertext=f"ID: {element['id']}<br>Type: {element['ifc_type']}"
        )
    
    def project_polygon_to_2d(self, vertices, element_type=None):
        """Project 3D vertices to 2D, respecting element orientation."""
        verts = np.array(vertices)
        centroid = verts.mean(axis=0)
        verts_centered = verts - centroid

        # Get normal vector using SVD
        _, _, vh = np.linalg.svd(verts_centered)
        
        # For vertical elements (windows, walls), prefer vertical orientation
        if element_type in ['IfcWindow', 'IfcWall', 'IfcDoor']:
            # Find the most horizontal normal (perpendicular to Z)
            up = np.array([0, 0, 1])
            normals = vh
            horizontal_scores = [1 - abs(np.dot(n, up)) for n in normals]
            best_normal_idx = np.argmax(horizontal_scores)
            normal = vh[best_normal_idx]
            
            # Create a coordinate system in the wall's plane
            # First basis vector is vertical (Z)
            v = np.array([0, 0, 1])
            # Second basis vector is horizontal in the wall's plane
            u = np.cross(v, normal)
            u = u / np.linalg.norm(u)
        else:
            # For horizontal elements, use the vertical normal
            normal = vh[2]
            u = vh[0]
            v = vh[1]

        # Project to 2D, maintaining proper orientation
        coords_2d = []
        for vert in verts_centered:
            # For vertical elements, use the wall's plane coordinates
            if element_type in ['IfcWindow', 'IfcWall', 'IfcDoor']:
                x = np.dot(vert, u)  # horizontal distance in wall's plane
                y = np.dot(vert, v)  # height (Z coordinate)
            else:
                # For horizontal elements, use regular projection
                x = np.dot(vert, u)
                y = np.dot(vert, v)
            coords_2d.append([x, y])
        
        return coords_2d

    def is_ccw(self, vertices):
        """Check if vertices are in counter-clockwise order."""
        area = 0.0
        for i in range(len(vertices)):
            j = (i + 1) % len(vertices)
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]
        return area > 0

    def ensure_winding_order(self, vertices_2d, indices, is_hole=False):
        """Ensure correct winding order for polygon loops."""
        # Get vertices for this loop
        loop_verts = [vertices_2d[i] for i in indices]
        
        # Check current winding order
        is_ccw_current = self.is_ccw(loop_verts)
        
        # Holes should be CW, outer loops CCW
        if is_hole:
            if is_ccw_current:
                return indices[::-1]  # Reverse if hole is CCW
        else:
            if not is_ccw_current:
                return indices[::-1]  # Reverse if outer is CW
        
        return indices

    def triangulate_3d_polygon(self, vertices, outer, holes=None, element_type=None):
        """Simple triangulation of 3D polygon using fan triangulation."""
        # If polygon has less than 3 vertices, can't triangulate
        if len(outer) < 3:
            return []
        
        # For simple triangular face
        if len(outer) == 3:
            return [(outer[0], outer[1], outer[2])]
        
        # For quad face (most common in BIM)
        if len(outer) == 4:
            # Split quad into two triangles
            return [
                (outer[0], outer[1], outer[2]),
                (outer[0], outer[2], outer[3])
            ]
        
        # For polygons with more vertices, use fan triangulation
        tris = []
        for i in range(1, len(outer) - 1):
            tris.append((outer[0], outer[i], outer[i+1]))
        return tris
    
    def visualize_metric(self, metric_name: str, metric_config: Dict[str, Dict[str, Any]]) -> go.Figure:
        """Create a 3D visualization for a specific metric"""
        if 'config' not in metric_config:
            raise ValueError(f"Metric configuration for '{metric_name}' is missing 'config' key")
        if 'components' not in metric_config['config']:
            raise ValueError(f"Metric configuration for '{metric_name}' is missing 'components' key in config")
        
        fig = go.Figure()
        
        # Define color scheme for different components
        colors = {
            'HNF': 'blue',
            'NNF': 'green',
            'VF': 'red',
            'FF': 'yellow',
            'GF': 'purple',
            'LUF': 'gray'
        }
        
        # Process each component in the metric
        for component_name, component_config in metric_config['config']['components'].items():
            # Parse filter conditions
            filter_str = component_config['filter']
            
            # Apply filter to metadata first to get matching elements
            try:
                filtered_metadata = MetadataFilter.filter_df_from_str(self.metadata, filter_str)
                
                # Group by IfcEntity to load geometry files efficiently
                for ifc_entity, group in filtered_metadata.groupby('IfcEntity'):
                    try:
                        # Load geometry data for this entity type
                        geometry_data = self._load_geometry(ifc_entity)
                        
                        # Convert geometry data to DataFrame
                        geometry_df = pd.DataFrame(geometry_data)
                        
                        # Convert id to string in geometry_df to match metadata
                        geometry_df['id'] = geometry_df['id'].astype(str)
                        
                        # Filter geometry to only include elements that match our metadata filter
                        matching_geometry = geometry_df[geometry_df['id'].isin(group.index)]
                        
                        # Add matching elements to the plot
                        for _, element in matching_geometry.iterrows():
                            mesh = self._create_mesh3d(element, colors.get(component_name, 'gray'))
                            fig.add_trace(mesh)
                            
                    except FileNotFoundError:
                        print(f"Info: No geometry data available for {ifc_entity}")
                        continue
                    
            except KeyError as e:
                print(f"Info: No elements matching filter for {component_name}")
                continue  # Skip to next component
        
        # Update layout
        fig.update_layout(
            title=metric_config['name'],
            scene=dict(
                aspectmode='data',
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z'
            ),
            showlegend=True
        )
        
        return fig
    
    def visualize_all_metrics(self, config_path: str):
        """Create visualizations for all metrics in the config file"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Create visualizations directory in the project root
        output_dir = Path("projects/Seefeld__private/visualizations")
        print(f"Creating output directory: {output_dir.absolute()}")
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Process each metric only once
        for metric_name, metric_config in config['metrics'].items():
            print(f"Processing metric: {metric_name}")
            fig = self.visualize_metric(metric_name, metric_config)
            output_file = output_dir / f"{metric_name}.html"
            print(f"Saving visualization to: {output_file.absolute()}")
            fig.write_html(str(output_file.absolute()))
            print(f"Saved visualization to: {output_file.absolute()}")

    def set_color_scheme(self, color_scheme: Dict[str, str]) -> None:
        """Set custom color scheme for components
        
        Args:
            color_scheme: Dictionary mapping component names to colors
        """
        self.colors = color_scheme

# Usage example:
if __name__ == "__main__":
    visualizer = MetricVisualizer("projects/Seefeld__private/buildings/09_hornbi")
    visualizer.visualize_all_metrics("projects/Seefeld__private/00_workflow_config.yaml")