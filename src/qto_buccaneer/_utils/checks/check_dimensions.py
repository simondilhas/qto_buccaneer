import math
from typing import Dict, List, Tuple, Any

def get_bounding_box(vertices: List[List[float]]) -> Tuple[float, float, float, float]:
    """Calculate the bounding box of a set of vertices."""
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    return (min(xs), max(xs), min(ys), max(ys))

def bounding_boxes_overlap(bbox1: Tuple[float, float, float, float], 
                         bbox2: Tuple[float, float, float, float], 
                         tolerance: float = 0.2) -> bool:
    """Check if two bounding boxes overlap."""
    x1_min, x1_max, y1_min, y1_max = bbox1
    x2_min, x2_max, y2_min, y2_max = bbox2
    
    overlap_x = (x1_min - tolerance <= x2_max) and (x2_min - tolerance <= x1_max)
    overlap_y = (y1_min - tolerance <= y2_max) and (y2_min - tolerance <= y1_max)
    
    return overlap_x and overlap_y

def analyze_space(space: Dict[str, Any], min_length: float, min_width: float, 
                 min_height: float = 0, min_area_ratio: float = 0.9, 
                 max_aspect_ratio: float = 2.5) -> Dict[str, Any]:
    """Analyze a space's dimensions and validate against requirements."""
    # Extract vertices and faces from the space geometry
    vertices = space.get("vertices", [])
    faces = space.get("faces", [])
    
    # Create volumes from faces
    volumes = []
    for face in faces:
        face_vertices = [vertices[i] for i in face]
        volumes.append({
            "vertices": face_vertices,
            "edges": [[i, (i + 1) % len(face)] for i in range(len(face))]
        })
    
    # Classify volumes as ground or airspace based on z-coordinate
    ground_volumes = []
    airspace_volumes = []
    
    for vol in volumes:
        # Check if this is a ground volume (z-coordinate close to 0)
        z_coords = [v[2] for v in vol["vertices"]]
        if all(abs(z) < 0.1 for z in z_coords):
            ground_volumes.append(vol)
        else:
            airspace_volumes.append(vol)
    
    if not ground_volumes:
        raise ValueError(f"No ground volume found in space {space.get('id')}")
    
    # Merge ground + matching airspace volumes
    merged_vertices = []
    ground_bboxes = []
    
    # Collect ground volumes
    for ground in ground_volumes:
        merged_vertices.extend(ground["vertices"])
        ground_bboxes.append(get_bounding_box(ground["vertices"]))
    
    # Check airspace volumes
    for airspace in airspace_volumes:
        air_bbox = get_bounding_box(airspace["vertices"])
        if any(bounding_boxes_overlap(ground_bbox, air_bbox) for ground_bbox in ground_bboxes):
            merged_vertices.extend(airspace["vertices"])
    
    # Calculate perimeter (only ground floor edges)
    perimeter = 0
    for ground in ground_volumes:
        for edge in ground["edges"]:
            v1 = ground["vertices"][edge[0]]
            v2 = ground["vertices"][edge[1]]
            dx = v2[0] - v1[0]
            dy = v2[1] - v1[1]
            perimeter += math.hypot(dx, dy)
    
    # Calculate area (only from ground volumes)
    area = 0
    for ground in ground_volumes:
        vertices = ground["vertices"]
        n = len(vertices)
        for i in range(n):
            x1, y1 = vertices[i][0], vertices[i][1]
            x2, y2 = vertices[(i + 1) % n][0], vertices[(i + 1) % n][1]
            area += (x1 * y2) - (x2 * y1)
    area = abs(area) / 2
    
    # Calculate bounding box dimensions (only ground)
    xs = []
    ys = []
    for ground in ground_volumes:
        for v in ground["vertices"]:
            xs.append(v[0])
            ys.append(v[1])
    width = max(xs) - min(xs)
    length = max(ys) - min(ys)
    
    bounding_box_area = width * length
    
    # Calculate height from merged ground + airspace
    zs = [v[2] for v in merged_vertices]
    height = max(zs) - min(zs) if zs else 0
    
    # Calculate final dimensions and ratios
    long_side = max(length, width)
    short_side = min(length, width)
    
    area_ratio = area / bounding_box_area if bounding_box_area > 0 else 0
    aspect_ratio = long_side / short_side if short_side > 0 else float('inf')
    
    # Validate dimensions
    valid = (
        long_side >= min_length and
        short_side >= min_width and
        height >= min_height and
        area_ratio >= min_area_ratio and
        aspect_ratio <= max_aspect_ratio
    )
    
    return {
        "id": space.get("id"),
        "length": long_side,
        "width": short_side,
        "height": height,
        "area": area,
        "perimeter": perimeter,
        "bounding_box_area": bounding_box_area,
        "area_ratio": area_ratio,
        "aspect_ratio": aspect_ratio,
        "valid": valid
    }

def check_dimensions(config: dict, metadata: dict, geometry: dict) -> dict:
    """
    Check the room dimensions against minimum requirements.
    
    Args:
        config: Configuration dictionary containing minimal room dimensions
        metadata: Metadata dictionary containing room information
        geometry: Geometry dictionary containing room dimensions
        
    Returns:
        Dictionary containing check results with actual dimensions and pass/fail status
    """
    # Get the minimal room dimensions from config
    minimal_room_dimensions = config.get("minimal_room_dimensions", {})
    filter_str = minimal_room_dimensions.get("config", {}).get("filter", "")
    min_dims = minimal_room_dimensions.get("config", {}).get("keys", {}).get("minimal_dimensions", [{}])[0]
    
    # Extract minimum dimensions
    min_length = min_dims.get("length", 0)
    min_width = min_dims.get("width", 0)
    min_height = min_dims.get("height", 0)
    
    # Analyze the space using the provided geometry
    try:
        analysis_result = analyze_space(
            space=geometry,
            min_length=min_length,
            min_width=min_width,
            min_height=min_height
        )
        
        # Create the result dictionary
        result = {
            "actual_dimensions": {
                "width": analysis_result["width"],
                "length": analysis_result["length"],
                "height": analysis_result["height"]
            },
            "minimal_dimensions": min_dims,
            "pass": analysis_result["valid"],
            "additional_metrics": {
                "area": analysis_result["area"],
                "perimeter": analysis_result["perimeter"],
                "area_ratio": analysis_result["area_ratio"],
                "aspect_ratio": analysis_result["aspect_ratio"]
            }
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "actual_dimensions": {
                "width": 0,
                "length": 0,
                "height": 0
            },
            "minimal_dimensions": min_dims,
            "pass": False
        }
    
config = {
  "minimal_room_dimensions": {
    "description": "Check the minimal room dimensions",
    "config": {
      "filter": "IfcEntity=IfcSpace AND (LongName=LUF OR LongName=SPH)",
      "keys": {
        "minimal_dimensions": [
          {
            "width": 16,
            "length": 28,
            "height": 8
          }
        ]
      }
    }
  }
}
