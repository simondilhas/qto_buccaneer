import streamlit as st
import os
from pathlib import Path
import re
import json
import plotly.graph_objects as go
from azure_config import get_base_project_path, is_azure_environment
from file_utils import list_files, read_file, exists, join_paths, is_dir
from utils.path_utils import get_project_paths, get_storey_files

st.set_page_config(
    page_title="Zones",
    page_icon="🗺️",
    layout="wide"
)

def display_storey_content(storey, files, graph_path):
    """Display content for a specific storey"""
    # Create a unique key for this storey's button state
    button_key = f"show_plotly_{storey}"
    
    # Initialize button state if not exists
    if button_key not in st.session_state:
        st.session_state[button_key] = False
    
    if not st.session_state[button_key] and files['png']:
        try:
            if is_azure_environment():
                image_data = read_file(get_base_project_path(), files['png'])
                st.image(image_data, use_container_width=True)
            else:
                st.image(files['png'], use_container_width=True)
            if files['json']:
                if st.button("Näher anschauen", key=f"btn_{storey}"):
                    st.session_state[button_key] = True
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading image: {str(e)}")
    elif st.session_state[button_key] and files['json']:
        try:
            if is_azure_environment():
                json_data = read_file(get_base_project_path(), files['json'])
                plotly_data = json.loads(json.loads(json_data.decode('utf-8')))
            else:
                with open(files['json'], 'r') as f:
                    plotly_data = json.loads(json.load(f))
            if isinstance(plotly_data, dict) and 'data' in plotly_data:
                fig = go.Figure(data=plotly_data['data'])
                if 'layout' in plotly_data:
                    fig.update_layout(plotly_data['layout'])
                st.plotly_chart(fig, use_container_width=True)
                if st.button("Zurück zur Übersicht", key=f"btn_back_{storey}"):
                    st.session_state[button_key] = False
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading JSON data: {str(e)}")
            st.session_state[button_key] = False
            st.rerun()

def display_zone_layouts(graph_path):
    """Display zone layouts"""
    try:
        if is_azure_environment():
            files = list_files(get_base_project_path(), graph_path)
        else:
            if not os.path.exists(graph_path):
                st.warning("No zone layouts found")
                return
            files = [os.path.join(graph_path, f) for f in os.listdir(graph_path)]
        
        # Look for the specific files
        image_file = None
        json_file = None
        
        for file in files:
            if file.endswith('.png'):
                image_file = file
            elif file.endswith('_data.json'):
                json_file = file
        
        if image_file and json_file:
            # Display the image
            if is_azure_environment():
                image_data = read_file(get_base_project_path(), image_file)
                st.image(image_data, use_container_width=True)
            else:
                st.image(image_file, use_container_width=True)
            
            # Load and display the JSON data
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
        else:
            st.warning("No zone layouts found")
    except Exception as e:
        st.error(f"Error loading zone layouts: {str(e)}")

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"Zones - {building}")
    
    paths = get_project_paths(building)
    display_zone_layouts(paths['graph'])
else:
    st.warning("Please select a building from the home page") 