import streamlit as st
import os
from pathlib import Path
import json
import plotly.graph_objects as go
from azure_config import get_base_project_path, is_azure_environment
from file_utils import list_files, read_file, exists, join_paths, is_dir
from utils.path_utils import get_project_paths

st.set_page_config(
    page_title="3D View",
    page_icon="🎨",
    layout="wide"
)

def display_3d_visualization(graph_path):
    """Display 3D visualization from image and Plotly JSON file"""
    st.write("Debug - Graph path:", graph_path)
    
    button_key = "show_3d_plotly"
    if button_key not in st.session_state:
        st.session_state[button_key] = False

    if is_azure_environment():
        if not is_dir(get_base_project_path(), graph_path):
            st.warning(f"Graph directory not found at: {graph_path}")
            return
        files = list_files(get_base_project_path(), graph_path)
        st.write("Debug - Files found:", files)
    else:
        if not os.path.exists(graph_path):
            st.warning(f"Graph directory not found at: {graph_path}")
            return
        files = os.listdir(graph_path)
        st.write("Debug - Files found:", files)

    image_file = None
    json_file = None
    for file in files:
        # Get just the filename from the full path
        filename = os.path.basename(file)
        if filename.lower() in ['titel_picture.png', 'titel_picture.json']:
            if filename.lower().endswith('.png'):
                image_file = file  # Keep the full path
            elif filename.endswith('.json'):
                json_file = file  # Keep the full path

    if not st.session_state[button_key] and image_file:
        try:
            if is_azure_environment():
                image_data = read_file(get_base_project_path(), image_file)
                st.image(image_data, use_container_width=True)
            else:
                st.image(image_file, use_container_width=True)
            if json_file:
                if st.button("Näher anschauen", key="btn_3d"):
                    st.session_state[button_key] = True
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading image: {str(e)}")
    elif st.session_state[button_key] and json_file:
        try:
            if is_azure_environment():
                json_data = read_file(get_base_project_path(), json_file)
                plotly_data = json.loads(json_data.decode('utf-8'))
            else:
                with open(json_file, 'r') as f:
                    plotly_data = json.load(f)
            if isinstance(plotly_data, dict) and 'data' in plotly_data:
                fig = go.Figure(data=plotly_data['data'])
                if 'layout' in plotly_data:
                    fig.update_layout(plotly_data['layout'])
                st.plotly_chart(fig, use_container_width=True)
                if st.button("Zurück zur Übersicht", key="btn_back"):
                    st.session_state[button_key] = False
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading JSON data: {str(e)}")
            st.session_state[button_key] = False
            st.rerun()

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"3D View - {building}")
    
    paths = get_project_paths(building)
    display_3d_visualization(paths['graph'])
else:
    st.warning("Please select a building from the home page") 