import streamlit as st
import os
from pathlib import Path
import base64
from PIL import Image
import io
from azure_config import get_base_project_path
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

def get_project_paths(building_name):
    """Get the paths for a specific building"""
    return {
        'project': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name),
        'graph': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "11_abstractbim_plots"),
        'check': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "09_building_inside_envelope")
    }

def get_floor_layouts(graph_path, pattern):
    """Get floor layout images matching the pattern"""
    layouts = {}
    if os.path.exists(graph_path):
        for file in os.listdir(graph_path):
            if file.startswith(f"floor_layout_by_{pattern}_") and file.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Extract storey from filename
                match = re.search(r'_(\d+)(?:\.\w+)?$', file)
                if match:
                    storey = match.group(1)
                    layouts[storey] = os.path.join(graph_path, file)
    return dict(sorted(layouts.items(), key=lambda x: int(x[0])))

def display_floor_layouts(graph_path, pattern, title):
    """Display floor layouts for a specific pattern"""
    layouts = get_floor_layouts(graph_path, pattern)
    
    if layouts:
        st.header(title)
        # Create tabs for each storey
        storey_tabs = st.tabs([f"Storey {storey}" for storey in layouts.keys()])
        
        for tab, (storey, image_path) in zip(storey_tabs, layouts.items()):
            with tab:
                st.image(image_path, caption=None)
    else:
        st.warning(f"No floor layouts found for {title}")

def create_3d_view(graph_path):
    """Create a 3D visualization using Plotly"""
    try:
        # Look for 3D visualization files in the graph folder
        if os.path.exists(graph_path):
            for file in os.listdir(graph_path):
                if file.startswith("3d_visualization_") and file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_path = os.path.join(graph_path, file)
                    return st.image(image_path, caption=None)
        return None
    except Exception as e:
        st.error(f"Error creating 3D view: {str(e)}")
        return None

def display_check_tab(check_path):
    """Display check files"""
    st.header("Check Files")
    if os.path.exists(check_path):
        for file in os.listdir(check_path):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(check_path, file)
                st.image(image_path, caption=None)
            else:
                st.write(f"- {file}")
    else:
        st.warning("No check files found")

def display_sia416_tab(graph_path):
    """Display SIA416 related content"""
    st.header("SIA416 Floor Layouts")
    display_floor_layouts(graph_path, "sia", "SIA416 Floor Layouts")

def display_zones_tab(graph_path):
    """Display zones related content"""
    st.header("Zone Floor Layouts")
    display_floor_layouts(graph_path, "zone", "Zone Floor Layouts")

def display_room_types_tab(graph_path):
    """Display room types related content"""
    st.header("Room Type Floor Layouts")
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

def display_index():
    st.title("Building Viewer")
    
    # Get list of buildings
    buildings_path = os.path.join(BASE_PROJECT_FOLDER, "buildings")
    if not os.path.exists(buildings_path):
        st.error(f"Buildings directory not found at: {buildings_path}")
        return
        
    # Get all buildings and filter those with images
    buildings_with_images = []
    for building in os.listdir(buildings_path):
        if os.path.isdir(os.path.join(buildings_path, building)):
            paths = get_project_paths(building)
            if os.path.exists(paths['graph']):
                # Check if there are any images in the graph folder
                has_images = any(file.lower().endswith(('.png', '.jpg', '.jpeg')) 
                               for file in os.listdir(paths['graph']))
                if has_images:
                    buildings_with_images.append(building)
    
    if not buildings_with_images:
        st.warning("No buildings with images found")
        return
    
    # Display buildings in a grid
    cols = st.columns(3)
    for idx, building in enumerate(buildings_with_images):
        with cols[idx % 3]:
            st.subheader(building)
            # Look for a preview image in the graph folder
            paths = get_project_paths(building)
            if os.path.exists(paths['graph']):
                for file in os.listdir(paths['graph']):
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_path = os.path.join(paths['graph'], file)
                        # Convert image to base64 for embedding in HTML
                        image_base64 = get_image_base64(image_path)
                        # Create clickable image using HTML
                        html = f"""
                        <div style="position: relative;">
                            <img src="data:image/png;base64,{image_base64}" style="width:100%; cursor:pointer;" 
                                 onclick="document.querySelector('button[key=\\'btn_{building}\\']').click();">
                        </div>
                        """
                        st.markdown(html, unsafe_allow_html=True)
                        break
            
            # Create a button that will be triggered by the image click
            if st.button(f"View {building}", key=f"btn_{building}", type="primary", use_container_width=True):
                st.session_state['selected_building'] = building
                st.switch_page("pages/1_Metrics.py")

# Password protection
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
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

    display_index()

if __name__ == "__main__":
    main() 