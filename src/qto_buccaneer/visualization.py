"""
IFC Geometry Parameter Parser
Extrage parametrii geometrici din IFC fără a genera mesh-uri (nu folosește OCC).
Citește profile, extruziuni, vertecși, poziții, etc.
Generează mesh-uri cu trimesh și vizualizează cu plotly.
"""

import ifcopenshell
import requests
import numpy as np
import trimesh
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.spatial.transform import Rotation
from shapely.geometry import Polygon
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class IFCGeometryParameterParser:
    """
    Parser pentru parametrii geometrici IFC fără Open CASCADE.
    Extrage date parametrice: profile, extruziuni, poziții, dimensiuni.
    """
    
    def __init__(self, ifc_file_path: str):
        """
        Inițializează parser-ul cu un fișier IFC.
        
        Args:
            ifc_file_path: Path local sau URL către fișierul IFC
        """
        if ifc_file_path.startswith('http'):
            # Download from URL
            print(f"📥 Downloading IFC from: {ifc_file_path}")
            response = requests.get(ifc_file_path)
            response.raise_for_status()
            with open('temp_model.ifc', 'wb') as f:
                f.write(response.content)
            self.model = ifcopenshell.open('temp_model.ifc')
            print(f"✅ Downloaded {len(response.content)} bytes")
        else:
            self.model = ifcopenshell.open(ifc_file_path)
        
        print(f"📊 IFC Schema: {self.model.schema}")
        print(f"📊 Total entities: {len(list(self.model))}\n")
    
    def extract_cartesian_point(self, point) -> Tuple[float, float, float]:
        """Extrage coordonatele unui IfcCartesianPoint."""
        if point is None:
            return (0.0, 0.0, 0.0)
        coords = point.Coordinates
        if len(coords) == 2:
            return (coords[0], coords[1], 0.0)
        elif len(coords) == 3:
            return (coords[0], coords[1], coords[2])
        return (0.0, 0.0, 0.0)
    
    def extract_direction(self, direction) -> Tuple[float, float, float]:
        """Extrage un vector direcție."""
        if direction is None:
            return (0.0, 0.0, 1.0)
        ratios = direction.DirectionRatios
        if len(ratios) == 2:
            return (ratios[0], ratios[1], 0.0)
        elif len(ratios) == 3:
            return (ratios[0], ratios[1], ratios[2])
        return (0.0, 0.0, 1.0)
    
    def extract_polyline(self, polyline) -> List[Tuple[float, float, float]]:
        """Extrage punctele unei IfcPolyline."""
        if polyline is None or not hasattr(polyline, 'Points'):
            return []
        
        points = []
        for point in polyline.Points:
            coords = self.extract_cartesian_point(point)
            points.append(coords)
        return points
    
    def extract_profile_def(self, profile) -> Dict[str, Any]:
        """
        Extrage datele unui profil (IfcProfileDef).
        
        Returns:
            Dict cu tip profil și parametri
        """
        if profile is None:
            return {}
        
        result = {
            'type': profile.is_a(),
            'name': profile.ProfileName if hasattr(profile, 'ProfileName') else None
        }
        
        # IfcRectangleProfileDef
        if profile.is_a('IfcRectangleProfileDef'):
            result['width'] = profile.XDim
            result['height'] = profile.YDim
            result['profile_vertices'] = [
                (-profile.XDim/2, -profile.YDim/2, 0),
                (profile.XDim/2, -profile.YDim/2, 0),
                (profile.XDim/2, profile.YDim/2, 0),
                (-profile.XDim/2, profile.YDim/2, 0),
                (-profile.XDim/2, -profile.YDim/2, 0)  # Close polygon
            ]
        
        # IfcCircleProfileDef
        elif profile.is_a('IfcCircleProfileDef'):
            result['radius'] = profile.Radius
            # Generate circle points
            num_points = 32
            points = []
            for i in range(num_points + 1):
                angle = 2 * np.pi * i / num_points
                x = profile.Radius * np.cos(angle)
                y = profile.Radius * np.sin(angle)
                points.append((x, y, 0))
            result['profile_vertices'] = points
        
        # IfcArbitraryClosedProfileDef
        elif profile.is_a('IfcArbitraryClosedProfileDef'):
            if hasattr(profile, 'OuterCurve'):
                outer_curve = profile.OuterCurve
                if outer_curve.is_a('IfcPolyline'):
                    result['profile_vertices'] = self.extract_polyline(outer_curve)
                elif outer_curve.is_a('IfcIndexedPolyCurve'):
                    result['profile_vertices'] = self.extract_indexed_poly_curve(outer_curve)
        
        # IfcIShapeProfileDef (I-beam)
        elif profile.is_a('IfcIShapeProfileDef'):
            result['overall_width'] = profile.OverallWidth
            result['overall_depth'] = profile.OverallDepth
            result['web_thickness'] = profile.WebThickness
            result['flange_thickness'] = profile.FlangeThickness
            # Could generate I-shape vertices here if needed
        
        return result
    
    def extract_indexed_poly_curve(self, curve) -> List[Tuple[float, float, float]]:
        """Extrage punctele dintr-un IfcIndexedPolyCurve."""
        if not hasattr(curve, 'Points'):
            return []
        
        point_list = curve.Points
        if hasattr(point_list, 'CoordList'):
            coords = point_list.CoordList
            points = [(coord[0], coord[1], coord[2] if len(coord) > 2 else 0.0) 
                     for coord in coords]
            return points
        return []
    
    def extract_axis2_placement_3d(self, placement) -> Dict[str, Any]:
        """Extrage poziția și orientarea dintr-un IfcAxis2Placement3D."""
        if placement is None:
            return {
                'location': (0, 0, 0),
                'axis': (0, 0, 1),
                'ref_direction': (1, 0, 0)
            }
        
        result = {}
        
        # Location
        if hasattr(placement, 'Location'):
            result['location'] = self.extract_cartesian_point(placement.Location)
        else:
            result['location'] = (0, 0, 0)
        
        # Axis (Z direction)
        if hasattr(placement, 'Axis') and placement.Axis:
            result['axis'] = self.extract_direction(placement.Axis)
        else:
            result['axis'] = (0, 0, 1)
        
        # RefDirection (X direction)
        if hasattr(placement, 'RefDirection') and placement.RefDirection:
            result['ref_direction'] = self.extract_direction(placement.RefDirection)
        else:
            result['ref_direction'] = (1, 0, 0)
        
        return result
    
    def get_placement_matrix(self, placement_data: Dict[str, Any]) -> np.ndarray:
        """Creează o matrice de transformare 4x4 din datele de poziționare."""
        location = np.array(placement_data.get('location', (0, 0, 0)))
        axis = np.array(placement_data.get('axis', (0, 0, 1)))
        ref_direction = np.array(placement_data.get('ref_direction', (1, 0, 0)))
        
        # Normalizează vectorii
        axis = axis / np.linalg.norm(axis) if np.linalg.norm(axis) > 0 else np.array([0, 0, 1])
        ref_direction = ref_direction / np.linalg.norm(ref_direction) if np.linalg.norm(ref_direction) > 0 else np.array([1, 0, 0])
        
        # Calculează Y direction (cross product)
        y_direction = np.cross(axis, ref_direction)
        if np.linalg.norm(y_direction) > 0:
            y_direction = y_direction / np.linalg.norm(y_direction)
        else:
            y_direction = np.array([0, 1, 0])
        
        # Re-calculează ref_direction pentru a fi ortogonal
        ref_direction = np.cross(y_direction, axis)
        
        # Creează matricea de rotație (coloanele sunt X, Y, Z directions)
        matrix = np.eye(4)
        matrix[0:3, 0] = ref_direction  # X
        matrix[0:3, 1] = y_direction     # Y
        matrix[0:3, 2] = axis            # Z
        matrix[0:3, 3] = location        # Translation
        
        return matrix
    
    def extract_object_placement(self, element) -> np.ndarray:
        """
        Extrage matricea completă de transformare pentru un element,
        urmărind lanțul de PlacementRelTo până la origine.
        
        Aceasta include transformări de la:
        - Element
        - IfcBuildingStorey (elevația etajului)
        - IfcBuilding
        - IfcSite
        
        Returns:
            Matrice 4x4 de transformare completă
        """
        if not hasattr(element, 'ObjectPlacement') or element.ObjectPlacement is None:
            return np.eye(4)
        
        placement = element.ObjectPlacement
        
        # Acumulează transformările recursiv
        total_matrix = np.eye(4)
        
        while placement is not None:
            if placement.is_a('IfcLocalPlacement'):
                # Extrage poziția relativă
                if hasattr(placement, 'RelativePlacement') and placement.RelativePlacement:
                    rel_placement = placement.RelativePlacement
                    
                    if rel_placement.is_a('IfcAxis2Placement3D'):
                        placement_data = self.extract_axis2_placement_3d(rel_placement)
                        local_matrix = self.get_placement_matrix(placement_data)
                        # Multiply în ordinea corectă: parent * child
                        total_matrix = local_matrix @ total_matrix
                    
                    elif rel_placement.is_a('IfcAxis2Placement2D'):
                        # 2D placement - extrage doar X, Y
                        location = (0, 0, 0)
                        if hasattr(rel_placement, 'Location') and rel_placement.Location:
                            coords = rel_placement.Location.Coordinates
                            location = (coords[0], coords[1], 0.0)
                        
                        local_matrix = np.eye(4)
                        local_matrix[0:3, 3] = location
                        total_matrix = local_matrix @ total_matrix
                
                # Continuă cu placement-ul părinte
                placement = placement.PlacementRelTo if hasattr(placement, 'PlacementRelTo') else None
            else:
                break
        
        return total_matrix
    
    def extract_extruded_area_solid(self, solid) -> Dict[str, Any]:
        """
        Extrage parametrii dintr-un IfcExtrudedAreaSolid.
        
        Returns:
            Dict cu profil, poziție, direcție extruziune, adâncime
        """
        if solid is None or not solid.is_a('IfcExtrudedAreaSolid'):
            return {}
        
        result = {
            'type': 'IfcExtrudedAreaSolid'
        }
        
        # 1. Profile
        if hasattr(solid, 'SweptArea'):
            result['profile'] = self.extract_profile_def(solid.SweptArea)
        
        # 2. Position (IfcAxis2Placement3D)
        if hasattr(solid, 'Position'):
            result['position'] = self.extract_axis2_placement_3d(solid.Position)
        
        # 3. Extrusion direction
        if hasattr(solid, 'ExtrudedDirection'):
            result['extrusion_direction'] = self.extract_direction(solid.ExtrudedDirection)
        
        # 4. Depth
        if hasattr(solid, 'Depth'):
            result['depth'] = solid.Depth
        
        return result
    
    def get_element_shape_representation(self, element) -> Optional[Any]:
        """Găsește reprezentarea geometrică a unui element."""
        if not hasattr(element, 'Representation'):
            return None
        
        representation = element.Representation
        if representation is None:
            return None
        
        # Caută în Representations
        if hasattr(representation, 'Representations'):
            for rep in representation.Representations:
                # Caută Body sau Model representation
                if hasattr(rep, 'RepresentationIdentifier'):
                    if rep.RepresentationIdentifier in ['Body', 'Model', 'Axis']:
                        return rep
        
        return None
    
    def extract_element_geometry(self, element) -> Dict[str, Any]:
        """
        Extrage toți parametrii geometrici pentru un element IFC.
        
        Returns:
            Dict cu toate datele geometrice parametrice
        """
        result = {
            'element_type': element.is_a(),
            'global_id': element.GlobalId,
            'name': element.Name if hasattr(element, 'Name') else None,
            'geometry': [],
            'object_placement': self.extract_object_placement(element)  # Matricea completă de poziționare
        }
        
        # Găsește reprezentarea geometrică
        shape_rep = self.get_element_shape_representation(element)
        if shape_rep is None:
            return result
        
        # Parcurge Items-urile (geometric items)
        if hasattr(shape_rep, 'Items'):
            for item in shape_rep.Items:
                if item.is_a('IfcExtrudedAreaSolid'):
                    geom_data = self.extract_extruded_area_solid(item)
                    result['geometry'].append(geom_data)
                
                elif item.is_a('IfcBooleanClippingResult'):
                    # Operație booleană - extrage first operand
                    if hasattr(item, 'FirstOperand'):
                        if item.FirstOperand.is_a('IfcExtrudedAreaSolid'):
                            geom_data = self.extract_extruded_area_solid(item.FirstOperand)
                            geom_data['has_boolean'] = True
                            result['geometry'].append(geom_data)
                
                elif item.is_a('IfcFacetedBrep'):
                    # Boundary representation - ar trebui să extragem fețele
                    result['geometry'].append({
                        'type': 'IfcFacetedBrep',
                        'note': 'Complex BREP geometry'
                    })
        
        # Extrage IfcOpeningElements care taie acest element (IfcRelVoidsElement)
        result['openings'] = self.get_openings_for_element(element)
        
        return result
    
    def get_openings_for_element(self, element) -> List[Dict[str, Any]]:
        """
        Găsește toate IfcOpeningElement care taie un element (perete, covering, etc).
        Folosește relația IfcRelVoidsElement.
        
        Returns:
            Lista de geometrii pentru opening-uri
        """
        openings = []
        
        # Verifică dacă elementul are HasOpenings
        if hasattr(element, 'HasOpenings'):
            for rel in element.HasOpenings:
                if rel.is_a('IfcRelVoidsElement'):
                    opening_element = rel.RelatedOpeningElement
                    if opening_element:
                        # Extrage geometria opening-ului
                        opening_data = {
                            'global_id': opening_element.GlobalId,
                            'name': opening_element.Name if hasattr(opening_element, 'Name') else None,
                            'object_placement': self.extract_object_placement(opening_element),
                            'geometry': []
                        }
                        
                        # Extrage reprezentarea geometrică
                        shape_rep = self.get_element_shape_representation(opening_element)
                        if shape_rep and hasattr(shape_rep, 'Items'):
                            for item in shape_rep.Items:
                                if item.is_a('IfcExtrudedAreaSolid'):
                                    geom_data = self.extract_extruded_area_solid(item)
                                    opening_data['geometry'].append(geom_data)
                        
                        if opening_data['geometry']:
                            openings.append(opening_data)
        
        return openings
    
    def parse_all_elements_with_geometry(self) -> List[Dict[str, Any]]:
        """
        Parcurge toate elementele IFC cu geometrie și extrage parametrii.
        
        Returns:
            List de dict-uri cu date geometrice pentru fiecare element
        """
        elements_data = []
        
        # Tipuri IFC de interes
        ifc_types = [
            'IfcWall', 'IfcWallStandardCase',
            'IfcSlab', 
            'IfcColumn',
            'IfcBeam',
            'IfcDoor',
            'IfcWindow',
            'IfcRoof',
            'IfcStair',
            'IfcRailing',
            'IfcCurtainWall',
            'IfcCovering',
            'IfcFooting'
        ]
        
        print("🔍 Extracting geometric parameters...\n")
        
        for ifc_type in ifc_types:
            elements = self.model.by_type(ifc_type)
            if elements:
                print(f"📦 Found {len(elements)} {ifc_type} elements")
                
                for element in elements:
                    geom_data = self.extract_element_geometry(element)
                    if geom_data['geometry']:  # Only add if has geometry
                        elements_data.append(geom_data)
        
        return elements_data
    
    def print_geometry_summary(self, elements_data: List[Dict[str, Any]]):
        """Printează un rezumat al geometriei extrase."""
        print("\n" + "="*80)
        print("GEOMETRIC PARAMETERS SUMMARY")
        print("="*80 + "\n")
        
        for elem_data in elements_data:
            print(f"🏗️  {elem_data['element_type']}")
            print(f"   GlobalId: {elem_data['global_id']}")
            if elem_data['name']:
                print(f"   Name: {elem_data['name']}")
            
            for i, geom in enumerate(elem_data['geometry'], 1):
                if geom.get('type') == 'IfcExtrudedAreaSolid':
                    print(f"\n   📐 Geometry {i}: EXTRUSION")
                    
                    # Profile info
                    profile = geom.get('profile', {})
                    print(f"      Profile Type: {profile.get('type', 'Unknown')}")
                    
                    if profile.get('type') == 'IfcRectangleProfileDef':
                        print(f"      Width: {profile.get('width', 0):.2f} mm")
                        print(f"      Height: {profile.get('height', 0):.2f} mm")
                    
                    elif profile.get('type') == 'IfcCircleProfileDef':
                        print(f"      Radius: {profile.get('radius', 0):.2f} mm")
                    
                    elif profile.get('type') == 'IfcArbitraryClosedProfileDef':
                        vertices = profile.get('profile_vertices', [])
                        print(f"      Vertices: {len(vertices)} points")
                        if vertices:
                            print(f"      First 3 vertices:")
                            for j, v in enumerate(vertices[:3], 1):
                                print(f"         {j}. ({v[0]:.2f}, {v[1]:.2f}, {v[2]:.2f})")
                    
                    # Position
                    position = geom.get('position', {})
                    loc = position.get('location', (0, 0, 0))
                    print(f"      Position: ({loc[0]:.2f}, {loc[1]:.2f}, {loc[2]:.2f})")
                    
                    axis = position.get('axis', (0, 0, 1))
                    print(f"      Z-Axis: ({axis[0]:.3f}, {axis[1]:.3f}, {axis[2]:.3f})")
                    
                    # Extrusion
                    ext_dir = geom.get('extrusion_direction', (0, 0, 1))
                    print(f"      Extrusion Direction: ({ext_dir[0]:.3f}, {ext_dir[1]:.3f}, {ext_dir[2]:.3f})")
                    print(f"      Extrusion Depth: {geom.get('depth', 0):.2f} mm")
                    
                    if geom.get('has_boolean'):
                        print(f"      ⚠️  Has Boolean Operation")
                
                elif geom.get('type') == 'IfcFacetedBrep':
                    print(f"\n   📐 Geometry {i}: BREP (Boundary Representation)")
            
            print("\n" + "-"*80 + "\n")


def main():
    """Funcția principală - parseaza fișierul IFC și printează parametrii."""
    
    # URL-ul fișierului IFC
    ifc_url = "https://raw.githubusercontent.com/ionuting/qto_test/refs/heads/main/tutorial/Intro/simple_model_abstractBIM.ifc"
    
    print("🚀 IFC Geometry Parameter Parser")
    print("="*80 + "\n")
    
    # Creează parser-ul
    parser = IFCGeometryParameterParser(ifc_url)
    
    # Extrage parametrii geometrici
    elements_data = parser.parse_all_elements_with_geometry()
    
    print(f"\n✅ Extracted geometry from {len(elements_data)} elements\n")
    
    # Printează rezumatul
    parser.print_geometry_summary(elements_data)
    
    # Statistici
    print("\n📊 STATISTICS:")
    print(f"   Total elements with geometry: {len(elements_data)}")
    
    by_type = {}
    for elem in elements_data:
        elem_type = elem['element_type']
        by_type[elem_type] = by_type.get(elem_type, 0) + 1
    
    print("\n   Elements by type:")
    for elem_type, count in sorted(by_type.items()):
        print(f"      {elem_type}: {count}")


class MeshGenerator:
    """Generează mesh-uri 3D din parametrii geometrici folosind trimesh."""
    
    @staticmethod
    def create_rotation_matrix(axis: Tuple[float, float, float], 
                              ref_direction: Tuple[float, float, float]) -> np.ndarray:
        """
        Creează o matrice de rotație din axis (Z) și ref_direction (X).
        
        Args:
            axis: Vector Z (sus)
            ref_direction: Vector X (direcție de referință)
            
        Returns:
            Matrice de rotație 4x4
        """
        # Normalizează vectorii
        z_axis = np.array(axis)
        z_axis = z_axis / np.linalg.norm(z_axis)
        
        x_axis = np.array(ref_direction)
        x_axis = x_axis / np.linalg.norm(x_axis)
        
        # Y axis = Z cross X
        y_axis = np.cross(z_axis, x_axis)
        y_axis = y_axis / np.linalg.norm(y_axis)
        
        # Recalculează X pentru ortogonalitate perfectă
        x_axis = np.cross(y_axis, z_axis)
        
        # Construiește matricea de rotație
        rotation_matrix = np.eye(4)
        rotation_matrix[0:3, 0] = x_axis
        rotation_matrix[0:3, 1] = y_axis
        rotation_matrix[0:3, 2] = z_axis
        
        return rotation_matrix
    
    @staticmethod
    def extrude_profile(profile_vertices: List[Tuple[float, float, float]], 
                       depth: float,
                       position: Dict[str, Any],
                       extrusion_direction: Tuple[float, float, float]) -> trimesh.Trimesh:
        """
        Creează un mesh 3D prin extruziunea unui profil 2D.
        
        Args:
            profile_vertices: Lista de vertecși ai profilului (în plan XY local)
            depth: Adâncimea extruziunii
            position: Dict cu 'location', 'axis', 'ref_direction'
            extrusion_direction: Direcția extruziunii
            
        Returns:
            trimesh.Trimesh object
        """
        if not profile_vertices or len(profile_vertices) < 3:
            return None
        
        # Convertește profile la numpy array
        profile_2d = np.array([(v[0], v[1]) for v in profile_vertices])
        
        # NU inversăm ordinea - lăsăm trimesh să creeze normalele corect
        # și vom gestiona double-sided în vizualizare
        
        # Creează un Polygon Shapely din profile
        try:
            polygon = Polygon(profile_2d)
        except Exception as e:
            print(f"⚠️  Invalid polygon: {e}")
            return None
        
        # Creează path pentru extruziune (linia de extruziune)
        extrusion_vec = np.array(extrusion_direction) * depth
        
        try:
            # Creează mesh-ul prin extruziune
            # trimesh.creation.extrude_polygon necesită Shapely Polygon și înălțime
            mesh = trimesh.creation.extrude_polygon(
                polygon=polygon,
                height=depth
            )
            
            # Aplică transformarea de poziție și orientare
            # 1. Rotație conform axis și ref_direction
            rotation_matrix = MeshGenerator.create_rotation_matrix(
                position.get('axis', (0, 0, 1)),
                position.get('ref_direction', (1, 0, 0))
            )
            
            # 2. Translație la poziția finală
            location = position.get('location', (0, 0, 0))
            translation_matrix = np.eye(4)
            translation_matrix[0:3, 3] = location
            
            # Combină transformările
            transform = translation_matrix @ rotation_matrix
            mesh.apply_transform(transform)
            
            return mesh
            
        except Exception as e:
            print(f"⚠️  Error creating mesh: {e}")
            return None
    
    @staticmethod
    def create_mesh_from_geometry_data(geom_data: Dict[str, Any]) -> trimesh.Trimesh:
        """
        Creează un mesh din datele geometrice extrase.
        
        Args:
            geom_data: Dict cu 'profile', 'position', 'extrusion_direction', 'depth'
            
        Returns:
            trimesh.Trimesh sau None
        """
        if geom_data.get('type') != 'IfcExtrudedAreaSolid':
            return None
        
        profile = geom_data.get('profile', {})
        profile_vertices = profile.get('profile_vertices', [])
        
        if not profile_vertices:
            return None
        
        return MeshGenerator.extrude_profile(
            profile_vertices=profile_vertices,
            depth=geom_data.get('depth', 0),
            position=geom_data.get('position', {}),
            extrusion_direction=geom_data.get('extrusion_direction', (0, 0, 1))
        )


class PlotlyVisualizer:
    """Vizualizare 3D cu Plotly."""
    
    def __init__(self, ifc_model=None):
        self.fig = go.Figure()
        self.ifc_model = ifc_model
        self.elements_by_storey = {}  # Stocare elemente per nivel
        self.storeys = []  # Lista de IfcBuildingStorey
        self.elements_data_for_export = []  # Date pentru export Parquet
        self.trace_metadata = []  # Metadata pentru fiecare trace (pentru filtrare)
        self.colors = {
            'IfcWallStandardCase': '#8B4513',  # Brown
            'IfcWall': '#8B4513',
            'IfcSlab': '#808080',  # Gray
            'IfcWindow': '#87CEEB',  # Sky blue
            'IfcDoor': '#CD853F',  # Peru
            'IfcCovering': '#D3D3D3',  # Light gray
            'IfcRoof': '#8B0000',  # Dark red
            'IfcColumn': '#696969',  # Dim gray
            'IfcBeam': '#A9A9A9',  # Dark gray
        }
        
        # Extrage storeys dacă avem modelul IFC
        if self.ifc_model:
            self._extract_storeys()
    
    def _extract_storeys(self):
        """Extrage toate IfcBuildingStorey din model și le sortează după elevație."""
        if not self.ifc_model:
            return
        
        storeys = self.ifc_model.by_type('IfcBuildingStorey')
        
        # Sortează după elevație
        storeys_data = []
        for storey in storeys:
            elevation = storey.Elevation if hasattr(storey, 'Elevation') and storey.Elevation else 0.0
            storeys_data.append({
                'entity': storey,
                'name': storey.Name if hasattr(storey, 'Name') else f"Level {elevation:.1f}",
                'elevation': elevation
            })
        
        self.storeys = sorted(storeys_data, key=lambda x: x['elevation'])
        
        # Inițializează dicționarele pentru fiecare nivel
        for storey_data in self.storeys:
            storey_name = storey_data['name']
            self.elements_by_storey[storey_name] = {}
    
    def _get_element_storey(self, element) -> str:
        """Determină nivelul (storey) pentru un element."""
        if not self.ifc_model or not self.storeys:
            return "Unknown"
        
        # Caută în relația ContainedInStructure
        if hasattr(element, 'ContainedInStructure'):
            for rel in element.ContainedInStructure:
                if hasattr(rel, 'RelatingStructure'):
                    relating_structure = rel.RelatingStructure
                    if relating_structure.is_a('IfcBuildingStorey'):
                        return relating_structure.Name if hasattr(relating_structure, 'Name') else "Unknown"
        
        # Fallback: găsește cel mai apropiat nivel pe baza elevației
        if hasattr(element, 'ObjectPlacement') and element.ObjectPlacement:
            parser = IFCGeometryParameterParser.__new__(IFCGeometryParameterParser)
            parser.model = self.ifc_model
            placement_matrix = parser.extract_object_placement(element)
            element_z = placement_matrix[2, 3]
            
            # Găsește cel mai apropiat storey
            closest_storey = None
            min_distance = float('inf')
            
            for storey_data in self.storeys:
                distance = abs(element_z - storey_data['elevation'])
                if distance < min_distance:
                    min_distance = distance
                    closest_storey = storey_data['name']
            
            return closest_storey if closest_storey else "Unknown"
        
        return "Unknown"
    
    def _extract_ifc_properties(self, ifc_element) -> Dict[str, Any]:
        """Extrage proprietăți relevante dintr-un element IFC."""
        props = {
            'GlobalId': ifc_element.GlobalId,
            'Name': ifc_element.Name if hasattr(ifc_element, 'Name') else None,
            'Description': ifc_element.Description if hasattr(ifc_element, 'Description') else None,
            'ObjectType': ifc_element.ObjectType if hasattr(ifc_element, 'ObjectType') else None,
            'Tag': ifc_element.Tag if hasattr(ifc_element, 'Tag') else None,
        }
        
        # Extrage property sets
        if hasattr(ifc_element, 'IsDefinedBy'):
            for definition in ifc_element.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    property_set = definition.RelatingPropertyDefinition
                    if property_set.is_a('IfcPropertySet'):
                        pset_name = property_set.Name
                        if hasattr(property_set, 'HasProperties'):
                            for prop in property_set.HasProperties:
                                if prop.is_a('IfcPropertySingleValue'):
                                    prop_name = f"{pset_name}.{prop.Name}"
                                    if hasattr(prop, 'NominalValue') and prop.NominalValue:
                                        props[prop_name] = prop.NominalValue.wrappedValue
        
        return props
    
    def add_trimesh(self, mesh: trimesh.Trimesh, name: str, color: str = None, opacity: float = 1.0,
                    element_type: str = None, storey: str = None, global_id: str = None):
        """
        Adaugă un trimesh la vizualizarea plotly.
        
        Args:
            mesh: trimesh.Trimesh object
            name: Numele elementului
            color: Culoarea (hex)
            opacity: Opacitate (0-1)
            element_type: Tipul IFC al elementului
            storey: Nivelul elementului
            global_id: GlobalId al elementului
        """
        if mesh is None:
            return
        
        vertices = mesh.vertices.copy()
        faces = mesh.faces
        
        # Fix normals pentru consistență
        mesh.fix_normals()
        
        # Calculăm normalele per vertex pentru offset
        vertex_normals = mesh.vertex_normals
        
        # Creăm două seturi de vertecși - unul ușor deplasați în direcția normalei
        # Aceasta previne z-fighting când fețele sunt edge-on
        offset = 0.005  # 5mm offset
        vertices_front = vertices + vertex_normals * offset
        vertices_back = vertices - vertex_normals * offset
        
        # Combinăm vertecșii
        all_vertices = np.vstack([vertices_front, vertices_back])
        
        # Fețele front folosesc primii vertecși, back folosesc vertecșii offsetați
        n_verts = len(vertices)
        faces_front = faces.copy()
        faces_back = faces[:, [0, 2, 1]] + n_verts  # Offset indices + inversare ordine
        
        all_faces = np.vstack([faces_front, faces_back])
        
        # Salvează metadata pentru filtrare
        trace_index = len(self.fig.data)
        self.trace_metadata.append({
            'trace_index': trace_index,
            'element_type': element_type or 'Unknown',
            'storey': storey or 'Unknown',
            'global_id': global_id or 'Unknown',
            'name': name
        })
        
        # Adaugă mesh-ul cu culoare directă
        self.fig.add_trace(go.Mesh3d(
            x=all_vertices[:, 0],
            y=all_vertices[:, 1],
            z=all_vertices[:, 2],
            i=all_faces[:, 0],
            j=all_faces[:, 1],
            k=all_faces[:, 2],
            color=color or '#808080',
            opacity=opacity,
            name=name,
            flatshading=True,
            lighting=dict(
                ambient=0.6,
                diffuse=0.6,
                specular=0.2,
                roughness=0.8,
                fresnel=0.1
            ),
            lightposition=dict(
                x=1000,
                y=1000,
                z=1000
            ),
            # Customdata pentru filtrare
            customdata=[[element_type, storey]] * len(all_vertices),
            visible=True  # Inițial vizibil
        ))
    
    def add_element(self, elem_data: Dict[str, Any], ifc_element=None):
        """
        Adaugă un element IFC la vizualizare.
        Aplică operații boolean pentru opening-uri (tăieturi pentru uși/ferestre).
        
        Args:
            elem_data: Dict cu date element (element_type, name, geometry, object_placement, openings)
            ifc_element: Entitatea IFC originală (pentru mapare la storey)
        """
        element_type = elem_data.get('element_type', 'Unknown')
        element_name = elem_data.get('name', 'Unnamed')
        global_id = elem_data.get('global_id', 'Unknown')
        color = self.colors.get(element_type, '#808080')
        
        # Determină storey-ul elementului pentru statistici
        storey_name = "Unknown"
        if ifc_element and self.storeys:
            storey_name = self._get_element_storey(ifc_element)
            if storey_name in self.elements_by_storey:
                if element_type not in self.elements_by_storey[storey_name]:
                    self.elements_by_storey[storey_name][element_type] = 0
                self.elements_by_storey[storey_name][element_type] += 1
        
        # Extrage proprietăți IFC pentru export
        properties = {}
        if ifc_element:
            properties = self._extract_ifc_properties(ifc_element)
        
        # Obține matricea de plasare globală (include elevația etajului)
        object_placement = elem_data.get('object_placement', np.eye(4))
        
        # Obține openings (găuri pentru uși/ferestre)
        openings = elem_data.get('openings', [])
        
        # Creează mesh-uri pentru openings
        opening_meshes = []
        for opening in openings:
            opening_placement = opening.get('object_placement', np.eye(4))
            for opening_geom in opening.get('geometry', []):
                opening_mesh = MeshGenerator.create_mesh_from_geometry_data(opening_geom)
                if opening_mesh:
                    opening_mesh.apply_transform(opening_placement)
                    opening_meshes.append(opening_mesh)
        
        # Procesează fiecare geometrie a elementului
        for geom in elem_data.get('geometry', []):
            mesh = MeshGenerator.create_mesh_from_geometry_data(geom)
            if mesh:
                # Aplică transformarea globală (object placement)
                mesh.apply_transform(object_placement)
                
                # Aplică operații boolean pentru openings (scădere)
                if opening_meshes:
                    mesh = self.apply_boolean_difference(mesh, opening_meshes)
                
                if mesh:
                    full_name = f"{element_type}: {element_name}"
                    
                    # Adaugă la date pentru export Parquet
                    self.elements_data_for_export.append({
                        'GlobalId': global_id,
                        'Name': element_name,
                        'Type': element_type,
                        'Storey': storey_name,
                        'NumVertices': len(mesh.vertices),
                        'NumFaces': len(mesh.faces),
                        'Volume': mesh.volume if mesh.is_watertight else None,
                        'BoundsMin': mesh.bounds[0].tolist(),
                        'BoundsMax': mesh.bounds[1].tolist(),
                        **properties
                    })
                    
                    self.add_trimesh(mesh, full_name, color, opacity=1.0,
                                   element_type=element_type, storey=storey_name, global_id=global_id)
    
    def apply_boolean_difference(self, base_mesh: trimesh.Trimesh, 
                                  tool_meshes: List[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """
        Aplică operații boolean de scădere (difference) pentru a crea găuri.
        
        Args:
            base_mesh: Mesh-ul de bază (perete)
            tool_meshes: Lista de mesh-uri de scăzut (openings)
            
        Returns:
            Mesh-ul rezultat sau mesh-ul original dacă operația eșuează
        """
        result_mesh = base_mesh
        
        for tool_mesh in tool_meshes:
            try:
                # Încearcă operația boolean cu trimesh
                # Trimesh folosește 'manifold' sau 'blender' ca engine
                result = result_mesh.difference(tool_mesh, engine='manifold')
                if result is not None and len(result.vertices) > 0:
                    result_mesh = result
            except Exception as e:
                # Dacă boolean difference eșuează, continuă cu mesh-ul curent
                # Aceasta se poate întâmpla când mesh-urile nu sunt watertight
                pass
        
        return result_mesh
    
    def export_to_parquet(self, output_path: str = "ifc_elements.parquet"):
        """Exportă datele elementelor în format Parquet."""
        if not self.elements_data_for_export:
            print("⚠️  No data to export")
            return
        
        df = pd.DataFrame(self.elements_data_for_export)
        df.to_parquet(output_path, engine='pyarrow', compression='snappy')
        print(f"✅ Exported {len(df)} elements to {output_path}")
        print(f"   File size: {pd.io.common.file_exists(output_path)}")
        return df
    
    def create_statistics_charts(self) -> List[go.Figure]:
        """Creează grafice pie cu statistici per nivel."""
        figures = []
        
        for storey_data in self.storeys:
            storey_name = storey_data['name']
            stats = self.elements_by_storey.get(storey_name, {})
            
            if not stats:
                continue
            
            # Pregătește datele pentru pie chart
            labels = list(stats.keys())
            values = list(stats.values())
            colors_list = [self.colors.get(label, '#808080') for label in labels]
            
            # Creează pie chart
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors_list),
                textinfo='label+value',
                textposition='auto',
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
            )])
            
            elevation = storey_data['elevation']
            fig.update_layout(
                title=f"{storey_name} (Elevation: {elevation:.2f}m)",
                showlegend=True,
                width=400,
                height=400,
                margin=dict(t=50, b=20, l=20, r=20)
            )
            
            figures.append(fig)
        
        return figures
    
    def show_with_statistics(self):
        """Afișează vizualizarea 3D împreună cu graficele statistice într-un singur layout."""
        if not self.storeys or not any(self.elements_by_storey.values()):
            print("\n⚠️  No statistics data available (storeys not extracted)")
            self.show(title="IFC Model - 3D Visualization")
            return
        
        # Calculează numărul de pie charts
        num_charts = len([s for s in self.storeys if self.elements_by_storey.get(s['name'])])
        
        if num_charts == 0:
            self.show(title="IFC Model - 3D Visualization")
            return
        
        # Calculează layout-ul grid pentru pie charts
        # 3D va ocupa 75% width, pie charts 25%
        # Pie charts vor fi stacked vertical
        
        # Creează subplot-uri: 1 coloană largă pentru 3D, 1 coloană îngustă pentru pie charts
        fig = make_subplots(
            rows=num_charts,
            cols=2,
            specs=[[{"type": "scene", "rowspan": num_charts}, {"type": "domain"}]] +
                  [[None, {"type": "domain"}] for _ in range(num_charts - 1)],
            subplot_titles=["3D Model"] + [
                f"{s['name']} ({s['elevation']:.1f}m)" 
                for s in self.storeys 
                if self.elements_by_storey.get(s['name'])
            ],
            column_widths=[0.75, 0.25],  # 3D: 75%, pie charts: 25%
            horizontal_spacing=0.02,
            vertical_spacing=0.05
        )
        
        # Adaugă toate trace-urile 3D la primul subplot
        for trace in self.fig.data:
            fig.add_trace(trace, row=1, col=1)
        
        # Adaugă pie charts
        chart_idx = 0
        for storey_data in self.storeys:
            storey_name = storey_data['name']
            stats = self.elements_by_storey.get(storey_name, {})
            
            if not stats:
                continue
            
            # Pregătește datele pentru pie chart
            labels = list(stats.keys())
            values = list(stats.values())
            colors_list = [self.colors.get(label, '#808080') for label in labels]
            
            row = chart_idx + 1
            
            # Creează pie chart
            pie_trace = go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors_list),
                textinfo='value',
                textposition='inside',
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
                showlegend=True,
                legendgroup=f"storey_{chart_idx}"
            )
            
            fig.add_trace(pie_trace, row=row, col=2)
            chart_idx += 1
        
        # Creează filtre interactive combinate (logică AND)
        all_storeys = sorted(list(set([meta['storey'] for meta in self.trace_metadata])))
        all_types = sorted(list(set([meta['element_type'] for meta in self.trace_metadata])))
        
        # Funcție helper pentru a calcula visibility bazat pe filtre combinate
        def get_visibility(selected_storey='All', selected_type='All'):
            """Returnează lista de visibility pentru toate trace-urile (logică AND)."""
            visible = []
            for i, trace in enumerate(fig.data):
                if i < len(self.trace_metadata):
                    meta = self.trace_metadata[i]
                    show = True
                    
                    # Aplică filtrul de storey (AND logic)
                    if selected_storey != 'All':
                        show = show and (meta['storey'] == selected_storey)
                    
                    # Aplică filtrul de tip (AND logic)
                    if selected_type != 'All':
                        show = show and (meta['element_type'] == selected_type)
                    
                    visible.append(show)
                else:
                    # Pie charts rămân vizibile
                    visible.append(True)
            return visible
        
        # Creează un singur dropdown organizat cu toate combinațiile
        buttons_filter = []
        
        # Opțiunea implicită: toate elementele
        buttons_filter.append({
            'label': '📋 All Levels & All Types',
            'method': 'update',
            'args': [
                {'visible': get_visibility('All', 'All')},
                {'title.text': 'IFC Model - All Levels & All Types'}
            ]
        })
        
        # Separator vizual
        buttons_filter.append({
            'label': '─────── By Level ───────',
            'method': 'skip'
        })
        
        # Pentru fiecare nivel, adaugă opțiunea "All Types" pe acel nivel + fiecare tip
        for storey in all_storeys:
            # Găsește tipurile prezente pe acest nivel
            storey_types = sorted(set([meta['element_type'] for meta in self.trace_metadata 
                                      if meta['storey'] == storey]))
            
            # Opțiune pentru toate tipurile pe acest nivel
            buttons_filter.append({
                'label': f'🏢 {storey} (All Types)',
                'method': 'update',
                'args': [
                    {'visible': get_visibility(storey, 'All')},
                    {'title.text': f'IFC Model - Level: {storey} (All Types)'}
                ]
            })
            
            # Opțiuni pentru fiecare tip pe acest nivel
            for elem_type in storey_types:
                count = sum(1 for meta in self.trace_metadata 
                           if meta['storey'] == storey and meta['element_type'] == elem_type)
                buttons_filter.append({
                    'label': f'  └─ {elem_type.replace("Ifc", "")} ({count})',
                    'method': 'update',
                    'args': [
                        {'visible': get_visibility(storey, elem_type)},
                        {'title.text': f'IFC Model - {storey} - {elem_type}'}
                    ]
                })
        
        # Separator
        buttons_filter.append({
            'label': '─────── By Type ────────',
            'method': 'skip'
        })
        
        # Pentru fiecare tip, adaugă opțiunea "All Levels" pentru acel tip
        for elem_type in all_types:
            count = sum(1 for meta in self.trace_metadata if meta['element_type'] == elem_type)
            buttons_filter.append({
                'label': f'🔧 {elem_type.replace("Ifc", "")} - All Levels ({count})',
                'method': 'update',
                'args': [
                    {'visible': get_visibility('All', elem_type)},
                    {'title.text': f'IFC Model - Type: {elem_type} (All Levels)'}
                ]
            })
        
        # Update layout pentru 3D scene
        fig.update_scenes(
            xaxis=dict(title='X', backgroundcolor="rgb(230, 230,230)", gridcolor="white"),
            yaxis=dict(title='Y', backgroundcolor="rgb(230, 230,230)", gridcolor="white"),
            zaxis=dict(title='Z', backgroundcolor="rgb(230, 230,230)", gridcolor="white"),
            aspectmode='data',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
        )
        
        # Update general layout cu un singur dropdown organizat
        fig.update_layout(
            title="IFC Model - All Levels & All Types",
            height=max(800, num_charts * 250),
            width=1800,
            showlegend=True,
            margin=dict(l=0, r=0, t=140, b=0),
            updatemenus=[
                {
                    'buttons': buttons_filter,
                    'direction': 'down',
                    'showactive': True,
                    'x': 0.15,
                    'xanchor': 'left',
                    'y': 1.13,
                    'yanchor': 'top',
                    'bgcolor': '#f0f0f0',
                    'bordercolor': '#666',
                    'borderwidth': 2,
                    'font': {'size': 11, 'family': 'Courier New, monospace'}
                }
            ],
            annotations=[
                {'text': '🎛️ Combined Filter (Level AND Type):', 
                 'x': 0.01, 'y': 1.11, 'xref': 'paper', 'yref': 'paper',
                 'showarrow': False, 
                 'font': {'size': 14, 'color': '#333', 'family': 'Arial, sans-serif', 'weight': 'bold'}}
            ]
        )
        
        print(f"\n📊 Displaying 3D model with statistics for {num_charts} levels...")
        print(f"🎛️  Single combined filter with AND logic:")
        print(f"   • Select level → see all types on that level")
        print(f"   • Select level + type → see ONLY that combination")
        print(f"   • Filter works with AND logic (both criteria must match)")
        fig.show()
    
    def show(self, title: str = "IFC Model Visualization"):
        """Afișează vizualizarea."""
        self.fig.update_layout(
            title=title,
            scene=dict(
                xaxis=dict(title='X', backgroundcolor="rgb(230, 230,230)", gridcolor="white"),
                yaxis=dict(title='Y', backgroundcolor="rgb(230, 230,230)", gridcolor="white"),
                zaxis=dict(title='Z', backgroundcolor="rgb(230, 230,230)", gridcolor="white"),
                aspectmode='data',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            showlegend=True,
            width=1200,
            height=800,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        self.fig.show()


def visualize_ifc_with_trimesh(ifc_url: str, element_types: List[str] = None, max_elements: int = None, show_statistics: bool = True):
    """
    Vizualizează un model IFC folosind trimesh + plotly.
    
    Args:
        ifc_url: URL sau path către fișierul IFC
        element_types: Lista de tipuri IFC de vizualizat (None = toate)
        max_elements: Număr maxim de elemente de vizualizat
        show_statistics: Dacă True, afișează și grafice statistice per nivel
    """
    print("🚀 IFC Visualization with Trimesh + Plotly")
    print("="*80 + "\n")
    
    # Parse fișierul IFC
    parser = IFCGeometryParameterParser(ifc_url)
    elements_data = parser.parse_all_elements_with_geometry()
    
    # Filtrează după tipuri dacă este specificat
    if element_types:
        elements_data = [e for e in elements_data if e['element_type'] in element_types]
    
    # Limitează numărul de elemente
    if max_elements:
        elements_data = elements_data[:max_elements]
    
    print(f"\n📊 Visualizing {len(elements_data)} elements...")
    
    # Creează vizualizarea (cu modelul IFC pentru a extrage storeys)
    visualizer = PlotlyVisualizer(ifc_model=parser.model if show_statistics else None)
    
    # Mapare GlobalId -> element IFC pentru a putea accesa relațiile
    elements_map = {}
    if show_statistics:
        for elem_type in ['IfcWall', 'IfcWallStandardCase', 'IfcSlab', 'IfcColumn', 'IfcBeam',
                          'IfcDoor', 'IfcWindow', 'IfcRoof', 'IfcStair', 'IfcRailing',
                          'IfcCurtainWall', 'IfcCovering', 'IfcFooting']:
            for elem in parser.model.by_type(elem_type):
                elements_map[elem.GlobalId] = elem
    
    for i, elem_data in enumerate(elements_data, 1):
        if i % 10 == 0:
            print(f"   Processing element {i}/{len(elements_data)}...")
        
        # Găsește entitatea IFC originală pentru mapare la storey
        ifc_element = elements_map.get(elem_data.get('global_id')) if show_statistics else None
        visualizer.add_element(elem_data, ifc_element=ifc_element)
    
    print(f"\n✅ Visualization ready!")
    
    # Afișează cu sau fără statistici
    if show_statistics:
        visualizer.show_with_statistics()
        
        # Export la Parquet
        export_choice = input("\nExport data to Parquet? (y/n): ").strip().lower()
        if export_choice == 'y':
            output_file = input("Output filename (default: ifc_elements.parquet): ").strip()
            if not output_file:
                output_file = "ifc_elements.parquet"
            visualizer.export_to_parquet(output_file)
    else:
        visualizer.show()


__all__ = ['visualize_ifc_with_trimesh', 'IFCGeometryParameterParser', 'MeshGenerator', 'PlotlyVisualizer']

# Alias pentru backwards compatibility
visualize_ifc = visualize_ifc_with_trimesh
