import streamlit as st
import os
from pathlib import Path
import re
import json
import plotly.graph_objects as go
from azure_config import get_base_project_path, is_azure_environment
from file_utils import list_files, read_file, exists, join_paths
from utils.path_utils import get_project_paths, get_storey_files

st.set_page_config(
    page_title="SIA416",
    page_icon="📊",
    layout="wide"
)

def display_storey_content(storey, files, graph_path):
    """Display content for a specific storey"""
    # Create a unique key for this storey's button state
    button_key = f"show_plotly_{storey}"
    
    # Initialize button state if not exists
    if button_key not in st.session_state:
        st.session_state[button_key] = False
    
    if files['json']:
        if st.button("Näher anschauen", key=f"btn_{storey}"):
            st.session_state[button_key] = True
            st.experimental_rerun()
    
    if not st.session_state[button_key] and files['png']:
        try:
            if is_azure_environment():
                image_data = read_file(get_base_project_path(), join_paths(graph_path, files['png']))
                st.image(image_data, caption=None)
            else:
                st.image(os.path.join(graph_path, files['png']), caption=None)
        except Exception as e:
            st.error(f"Error loading image for storey {storey}: {str(e)}")
    elif st.session_state[button_key] and files['json']:
        try:
            if is_azure_environment():
                json_data = read_file(get_base_project_path(), join_paths(graph_path, files['json']))
                plotly_data = json.loads(json_data.decode('utf-8'))
            else:
                with open(os.path.join(graph_path, files['json']), 'r') as f:
                    plotly_data = json.load(f)
            if isinstance(plotly_data, dict) and 'data' in plotly_data:
                fig = go.Figure(data=plotly_data['data'])
                if 'layout' in plotly_data:
                    fig.update_layout(plotly_data['layout'])
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading JSON data for storey {storey}: {str(e)}")
            st.session_state[button_key] = False
            st.experimental_rerun()

def display_sia_layouts(graph_path):
    """Display SIA layouts for all storeys"""
    storey_files = get_storey_files(graph_path, 'sia')
    
    if storey_files:
        st.header("SIA416 Floor Layouts")
        # Create tabs for each storey
        storey_tabs = st.tabs([storey for storey in storey_files.keys()])
        
        for tab, (storey, files) in zip(storey_tabs, storey_files.items()):
            with tab:
                display_storey_content(storey, files, graph_path)
    else:
        st.warning("No SIA416 floor layouts found")

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"SIA416 - {building}")
    
    paths = get_project_paths(building)
    display_sia_layouts(paths['graph'])
else:
    st.warning("Please select a building from the home page") 