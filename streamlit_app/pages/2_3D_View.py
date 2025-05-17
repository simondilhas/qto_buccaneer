import streamlit as st
import os
from pathlib import Path
import json
import plotly.graph_objects as go
from azure_config import get_base_project_path

st.set_page_config(
    page_title="3D View",
    page_icon="🎨",
    layout="wide"
)

def get_project_paths(building_name):
    """Get the paths for a specific building"""
    return {
        'project': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name),
        'graph': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "11_abstractbim_plots"),
        'check': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "09_building_inside_envelope")
    }

def display_3d_visualization(graph_path):
    """Display 3D visualization from image and Plotly JSON file"""
    # Create a unique key for the button state
    button_key = "show_3d_plotly"
    
    # Initialize button state if not exists
    if button_key not in st.session_state:
        st.session_state[button_key] = False
    
    if not os.path.exists(graph_path):
        st.warning("Graph directory not found")
        return

    # First look for image file
    image_file = None
    json_file = None
    
    for file in os.listdir(graph_path):
        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_file = os.path.join(graph_path, file)
            break
        elif file.endswith('.json'):
            json_file = os.path.join(graph_path, file)
    
    # Show button if JSON file exists
    if json_file:
        if st.button("Näher anschauen", key="btn_3d"):
            st.session_state[button_key] = True
            st.experimental_rerun()
    
    # Show image if not showing plotly
    if not st.session_state[button_key] and image_file:
        st.image(image_file, caption=None)
    # Show plotly if button was pressed
    elif st.session_state[button_key] and json_file:
        try:
            with open(json_file, 'r') as f:
                plotly_data = json.load(f)
                if isinstance(plotly_data, dict) and 'data' in plotly_data:
                    fig = go.Figure(data=plotly_data['data'])
                    if 'layout' in plotly_data:
                        fig.update_layout(plotly_data['layout'])
                    st.plotly_chart(fig, use_container_width=True)
        except json.JSONDecodeError:
            st.warning("Could not load JSON data for 3D visualization")
            st.session_state[button_key] = False
            st.experimental_rerun()

# Configure base path using environment-aware configuration
BASE_PROJECT_FOLDER = get_base_project_path()

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"3D View - {building}")
    
    paths = get_project_paths(building)
    display_3d_visualization(paths['graph'])
else:
    st.warning("Please select a building from the home page") 