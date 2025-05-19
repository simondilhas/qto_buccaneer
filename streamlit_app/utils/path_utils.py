import os
import re
import json
import io
from PIL import Image
from azure_config import get_base_project_path, is_azure_environment
from file_utils import join_paths, list_files, read_file, exists, is_dir
import streamlit as st
from pathlib import Path

def get_project_paths(building):
    """Get all relevant paths for a building"""
    paths = {}
    
    # Base paths
    paths['building'] = f"buildings/{building}"
    paths['graph'] = f"{paths['building']}/11_abstractbim_plots"
    paths['visualizations'] = f"{paths['building']}/09_check_building_inside_envelop/visualizations"
    paths['check'] = f"{paths['building']}/09_building_inside_envelope"
    paths['metrics'] = f"{paths['building']}/metrics"
    
    return paths

def get_title_picture_path():
    """Get the path to the title picture"""
    if is_azure_environment():
        return 'assets/title_picture.png'
    else:
        return os.path.join(get_base_project_path(), 'assets', 'title_picture.png')

def load_title_picture():
    """Load the title picture from the first building's graph folder"""
    try:
        if is_azure_environment():
            # Use 02_flugge specifically
            building = '02_flugge'
            paths = get_project_paths(building)
            # Look for title picture in the graph folder
            graph_files = list_files(get_base_project_path(), paths['graph'])
            # Look specifically for the title picture
            title_picture = 'buildings/02_flugge/11_abstractbim_plots/titel_picture.png'
            if title_picture in graph_files:
                # Use the full path for reading the file
                image_data = read_file(get_base_project_path(), title_picture)
                return Image.open(io.BytesIO(image_data))
            else:
                print(f"Debug - Title picture not found in {paths['graph']}")
                print(f"Debug - Available files: {graph_files}")
        else:
            # For local environment
            buildings_path = os.path.join(get_base_project_path(), "buildings")
            if os.path.exists(buildings_path):
                # Use 02_flugge specifically
                building = '02_flugge'
                paths = get_project_paths(building)
                if os.path.exists(paths['graph']):
                    title_picture = os.path.join(paths['graph'], 'titel_picture.png')
                    if os.path.exists(title_picture):
                        return Image.open(title_picture)
        return None
    except Exception as e:
        print(f"Error loading title picture: {str(e)}")
        return None

def get_storey_files(graph_path, prefix):
    """Get all files for each storey with a specific prefix"""
    storey_files = {}
    
    if is_azure_environment():
        if not is_dir(get_base_project_path(), graph_path):
            return storey_files
        files = list_files(get_base_project_path(), graph_path)
    else:
        if not os.path.exists(graph_path):
            return storey_files
        files = [os.path.join(graph_path, f) for f in os.listdir(graph_path)]
    
    for file in files:
        # Get just the filename from the full path
        filename = os.path.basename(file)
        if filename.startswith(f"floor_layout_by_{prefix}_"):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.json')):
                # Extract storey from filename
                match = re.search(r'floor_layout_by_' + prefix + r'_(.+?)(?:\.\w+)?$', filename)
                if match:
                    storey = match.group(1)
                    if storey not in storey_files:
                        storey_files[storey] = {'png': None, 'json': None}
                    
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        storey_files[storey]['png'] = file  # Keep full path
                    elif filename.endswith('.json'):
                        storey_files[storey]['json'] = file  # Keep full path
    
    # Custom sorting function to handle both numeric and text storeys
    def storey_sort_key(storey):
        if storey == 'UG':
            return -1  # Put UG first
        if storey == 'EG':
            return 0   # Put EG second
        try:
            # Extract number from O1, O2, etc.
            num = int(storey[1:]) if storey.startswith('O') else int(storey)
            return num
        except ValueError:
            return float('inf')  # Put other text storeys at the end
    
    return dict(sorted(storey_files.items(), key=lambda x: storey_sort_key(x[0])))

def get_floor_layouts(graph_path, pattern):
    """Get floor layouts from the graph path"""
    if is_azure_environment():
        files = list_files(get_base_project_path(), graph_path)
        return [f for f in files if re.search(pattern, f)]
    else:
        if not os.path.exists(graph_path):
            return []
        return [f for f in os.listdir(graph_path) if re.search(pattern, f)]

def load_image(image_path):
    """Load an image from either filesystem or Azure Blob Storage"""
    if is_azure_environment():
        image_data = read_file(get_base_project_path(), image_path)
        return Image.open(io.BytesIO(image_data))
    else:
        return Image.open(image_path)

def load_json(json_path):
    """Load a JSON file from either filesystem or Azure Blob Storage"""
    if is_azure_environment():
        json_data = read_file(get_base_project_path(), json_path)
        return json.loads(json_data.decode('utf-8'))
    else:
        with open(json_path, 'r') as f:
            return json.load(f)

def display_floor_layouts(graph_path, pattern, title):
    """Display floor layouts in a grid"""
    layouts = get_floor_layouts(graph_path, pattern)
    if not layouts:
        st.warning(f"No {pattern} layouts found")
        return

    st.subheader(title)
    cols = st.columns(3)
    for i, layout in enumerate(layouts):
        col = cols[i % 3]
        with col:
            try:
                image = load_image(join_paths(graph_path, layout))
                st.image(image, use_container_width=True)
            except Exception as e:
                st.error(f"Error loading image {layout}: {str(e)}") 