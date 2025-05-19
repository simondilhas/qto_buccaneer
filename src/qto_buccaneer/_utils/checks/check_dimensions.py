import math
import numpy as np
from typing import Dict, List, Tuple, Any

def get_bounding_box(vertices: List[List[float]]) -> Tuple[float, float, float, float, float, float]:
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def bounding_boxes_xy_overlap(bbox1: Tuple[float, float, float, float, float, float], 
                            bbox2: Tuple[float, float, float, float, float, float], 
                            tolerance: float = 0.05) -> bool:
    x1_min, x1_max, y1_min, y1_max, _, _ = bbox1
    x2_min, x2_max, y2_min, y2_max, _, _ = bbox2
    
    overlap_x = (x1_min - tolerance <= x2_max) and (x2_min - tolerance <= x1_max)
    overlap_y = (y1_min - tolerance <= y2_max) and (y2_min - tolerance <= y1_max)
    
    return overlap_x and overlap_y

def get_oriented_bounding_box(vertices: List[List[float]]) -> Tuple[float, float, float, np.ndarray]:
    # Convert vertices to numpy array
    points = np.array(vertices)
    
    # Center the points
    centroid = np.mean(points, axis=0)
    centered_points = points - centroid
    
    # Calculate covariance matrix
    cov_matrix = np.cov(centered_points.T)
    
    # Get eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    
    # Sort eigenvalues and eigenvectors in descending order
    idx = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # Project points onto the principal axes
    projected_points = np.dot(centered_points, eigenvectors)
    
    # Calculate min and max along each principal axis
    min_coords = np.min(projected_points, axis=0)
    max_coords = np.max(projected_points, axis=0)
    
    # Calculate dimensions
    dimensions = max_coords - min_coords
    
    return dimensions[0], dimensions[1], dimensions[2], eigenvectors

def process_check_dimensions(input_dict: Dict[str, Dict[str, Any]], 
                           config: Dict[str, Any], 
                           xy_tolerance: float = 0.05) -> List[Dict[str, Any]]:
    minimal_config = config["config"]["minimal_dimensions"][0]
    min_width = minimal_config["width"]
    min_length = minimal_config["length"]
    min_height = minimal_config["height"]

    matching_config = config["config"]["matching"]
    lower_field = matching_config["lower_space"]["field"]
    lower_value = matching_config["lower_space"]["value"].upper()
    upper_field = matching_config["upper_space"]["field"]
    upper_value = matching_config["upper_space"]["value"].upper()

    results = []

    # Filter lower (SPA) and upper (LUF) spaces based on matching config
    spa_spaces = {
        sid: s for sid, s in input_dict.items()
        if lower_value in str(s.get(lower_field, "")).upper()
    }
    luf_spaces = {
        sid: s for sid, s in input_dict.items()
        if upper_value in str(s.get(upper_field, "")).upper()
    }

    for spa_id, spa_space in spa_spaces.items():
        geometry = spa_space.get("geometry", {})
        vertices = geometry.get("vertices", [])

        if not vertices:
            print(f"Warning: No vertices found for space {spa_id}")
            continue

        # Get oriented bounding box dimensions
        dim_x, dim_y, dim_z, _ = get_oriented_bounding_box(vertices)

        # Check all possible combinations of dimensions
        valid = False
        # Try all possible combinations of dimensions
        for dim1, dim2 in [(dim_x, dim_y), (dim_y, dim_x)]:
            if (dim1 >= min_width and dim2 >= min_length) or (dim1 >= min_length and dim2 >= min_width):
                valid = True
                break

        # Height check remains the same
        valid = valid and (dim_z >= min_height)

        results.append({
            "valid": valid,
            "LongName": spa_space.get("LongName", ""),
            "dim_x": dim_x,
            "dim_y": dim_y,
            "dim_z": dim_z
        })

    return results


