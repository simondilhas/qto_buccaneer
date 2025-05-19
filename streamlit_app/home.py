import streamlit as st
import os
from pathlib import Path
import base64
from PIL import Image
import io
from azure_config import get_base_project_path, is_azure_environment
from file_utils import list_files, read_file, join_paths, exists
from utils.path_utils import get_project_paths, get_floor_layouts, load_image, load_json, display_floor_layouts, load_title_picture
import plotly.graph_objects as go
import json
import re

# Page config
st.set_page_config(
    page_title="Projektübersicht",
    page_icon="📁",
    layout="wide"
)

# Configure base path using environment-aware configuration
BASE_PROJECT_FOLDER = get_base_project_path()

# Debug: Print available secrets
#st.write("Available secrets:", list(st.secrets.keys()))

def get_project_paths(building_name):
    """Get the paths for a specific building"""
    if is_azure_environment():
        # For Azure, we just need the relative paths
        return {
            'project': join_paths('buildings', building_name),
            'graph': join_paths('buildings', building_name, "11_abstractbim_plots"),
            'check': join_paths('buildings', building_name, "09_building_inside_envelope")
        }
    else:
        # For local environment, we need full paths
        return {
            'project': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name),
            'graph': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "11_abstractbim_plots"),
            'check': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "09_building_inside_envelope")
        }

def get_floor_layouts(graph_path, pattern):
    """Get floor layouts from the graph path"""
    if is_azure_environment():
        files = list_files(BASE_PROJECT_FOLDER, graph_path)
        return [f for f in files if re.search(pattern, f)]
    else:
        if not os.path.exists(graph_path):
            return []
        return [f for f in os.listdir(graph_path) if re.search(pattern, f)]

def load_image(image_path):
    """Load an image from either filesystem or Azure Blob Storage"""
    if is_azure_environment():
        image_data = read_file(BASE_PROJECT_FOLDER, image_path)
        return Image.open(io.BytesIO(image_data))
    else:
        return Image.open(image_path)

def load_json(json_path):
    """Load a JSON file from either filesystem or Azure Blob Storage"""
    if is_azure_environment():
        json_data = read_file(BASE_PROJECT_FOLDER, json_path)
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
                st.image(image, use_column_width=True)
            except Exception as e:
                st.error(f"Error loading image {layout}: {str(e)}")

def create_3d_view(graph_path):
    """Create a 3D view of the building"""
    try:
        # Load the 3D view data
        json_path = join_paths(graph_path, "3d_view.json")
        if not exists(BASE_PROJECT_FOLDER, json_path):
            st.warning("No 3D view data found")
            return

        data = load_json(json_path)
        
        # Create the 3D plot
        fig = go.Figure()
        
        # Add the building geometry
        for geometry in data.get('geometries', []):
            fig.add_trace(go.Mesh3d(
                x=geometry['x'],
                y=geometry['y'],
                z=geometry['z'],
                i=geometry['i'],
                j=geometry['j'],
                k=geometry['k'],
                color=geometry.get('color', 'lightblue'),
                opacity=0.8
            ))
        
        # Update layout
        fig.update_layout(
            title="3D Building View",
            scene=dict(
                aspectmode='data',
                camera=dict(
                    up=dict(x=0, y=0, z=1),
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error creating 3D view: {str(e)}")

def display_check_tab(check_path):
    """Display check results"""
    try:
        # Load check results
        json_path = join_paths(check_path, "check_results.json")
        if not exists(BASE_PROJECT_FOLDER, json_path):
            st.warning("No check results found")
            return

        data = load_json(json_path)
        
        # Display check results
        st.subheader("Check Results")
        
        # Create a table for the results
        results = []
        for check in data.get('checks', []):
            results.append({
                'Check': check['name'],
                'Status': check['status'],
                'Message': check.get('message', '')
            })
        
        if results:
            st.table(results)
        else:
            st.info("No check results available")
            
    except Exception as e:
        st.error(f"Error displaying check results: {str(e)}")

def display_sia416_tab(graph_path):
    """Display SIA416 related content"""
    #st.header("SIA416 Floor Layouts")
    display_floor_layouts(graph_path, "sia", "SIA416 Floor Layouts")

def display_zones_tab(graph_path):
    """Display zones related content"""
    #st.header("Zone Floor Layouts")
    display_floor_layouts(graph_path, "zone", "Zone Floor Layouts")

def display_room_types_tab(graph_path):
    """Display room types related content"""
    #st.header("Room Type Floor Layouts")
    display_floor_layouts(graph_path, "name", "Room Type Floor Layouts")

def display_sidebar():
    """Display the navigation sidebar"""
    with st.sidebar:
        st.title("Navigation")
        
        # Add navigation buttons
        if st.button("🏠 Projektübersicht"):
            if 'selected_building' in st.session_state:
                del st.session_state['selected_building']
            if 'selected_page' in st.session_state:
                del st.session_state['selected_page']
            st.experimental_rerun()
            
        if 'selected_building' in st.session_state:
            st.subheader("Pages")
            if st.button("3D View"):
                st.session_state['selected_page'] = '3d'
                st.experimental_rerun()
            if st.button("SIA416"):
                st.session_state['selected_page'] = 'sia'
                st.experimental_rerun()
            if st.button("Zonen"):
                st.session_state['selected_page'] = 'zone'
                st.experimental_rerun()
            if st.button("Check"):
                st.session_state['selected_page'] = 'check'
                st.experimental_rerun()

def display_project_page(building_name):
    st.title(f"Building: {building_name}")
    
    paths = get_project_paths(building_name)
    
    # Get the current page from session state
    current_page = st.session_state.get('selected_page', '3d')
    
    if current_page == '3d':
        st.header("3D Visualization")
        create_3d_view(paths['graph'])
    elif current_page == 'sia':
        display_sia416_tab(paths['graph'])
    elif current_page == 'zone':
        display_zones_tab(paths['graph'])
    elif current_page == 'check':
        display_check_tab(paths['check'])

def load_title_picture(graph_path):
    """Load the title picture with height closest to zero, only if -1 <= height <= 1."""
    def extract_height(filename):
        try:
            base = os.path.basename(filename)
            if base.startswith('titel_picture_') and base.endswith('.png'):
                height_str = base[len('titel_picture_'):-len('.png')]
                return float(height_str)
        except Exception:
            return None
        return None

    images = {}
    if is_azure_environment():
        files = list_files(BASE_PROJECT_FOLDER, graph_path)
        for file in files:
            base = os.path.basename(file)
            height = extract_height(base)
            if height is not None and -1 <= height <= 1:
                images[file] = height
        if images:
            best = min(images.items(), key=lambda x: abs(x[1]))
            return best[0]
        return None
    else:
        if not os.path.exists(graph_path):
            return None
        for file in os.listdir(graph_path):
            height = extract_height(file)
            if height is not None and -1 <= height <= 1:
                images[file] = height
        if images:
            best = min(images.items(), key=lambda x: abs(x[1]))
            return os.path.join(graph_path, best[0])
        return None

def display_index():
    st.title("Projektübersicht")
    
    # Get list of buildings
    buildings_with_content = []
    if is_azure_environment():
        try:
            # List all blobs to see the actual structure
            all_blobs = list_files(BASE_PROJECT_FOLDER, '')
            
            # Extract building names from the paths
            building_names = set()
            for blob in all_blobs:
                # Look for any content in 11_abstractbim_plots
                if blob.startswith('buildings/') and '/11_abstractbim_plots/' in blob:
                    # Extract building name from the path
                    parts = blob.split('/')
                    if len(parts) >= 4:  # buildings/building_name/11_abstractbim_plots/...
                        building_name = parts[1]  # Second part is the building name
                        if building_name:
                            building_names.add(building_name)
            
            buildings_with_content = sorted(building_names)
            
        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
    else:
        buildings_path = os.path.join(get_base_project_path(), "buildings")
        if not os.path.exists(buildings_path):
            st.error(f"Buildings directory not found at: {buildings_path}")
            return
        for building in os.listdir(buildings_path):
            if os.path.isdir(os.path.join(buildings_path, building)):
                paths = get_project_paths(building)
                if os.path.exists(paths['graph']) and os.listdir(paths['graph']):
                    buildings_with_content.append(building)
    
    if not buildings_with_content:
        st.warning("No buildings with content found")
        return
    
    # Display buildings in a grid
    cols = st.columns(3)
    for idx, building in enumerate(buildings_with_content):
        with cols[idx % 3]:
            st.subheader(building)
            paths = get_project_paths(building)
            title_picture = load_title_picture(paths['graph'])
            if title_picture:
                if is_azure_environment():
                    image_data = read_file(BASE_PROJECT_FOLDER, title_picture)
                    st.image(image_data, use_column_width=True)
                else:
                    st.image(title_picture, use_column_width=True)
            if st.button(f"View {building}", key=f"btn_{building}", type="primary", use_container_width=True):
                st.session_state['selected_building'] = building
                st.switch_page("pages/1_Metrics.py")

# Password protection
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Strip whitespace from both entered and secret password
        if st.session_state["password"].strip() == st.secrets["password"].strip():
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

def get_image_base64(image_path):
    """Convert image to base64 for display"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def main():
    if not check_password():
        return

    #st.write("Streamlit debug output is working!")

    display_index()

if __name__ == "__main__":
    main() 