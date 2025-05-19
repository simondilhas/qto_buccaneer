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
                plotly_data = json.loads(json_data.decode('utf-8'))
            else:
                with open(files['json'], 'r') as f:
                    plotly_data = json.load(f)
            
            if isinstance(plotly_data, dict) and 'data' in plotly_data:
                # Clean the data by converting scattermap to scatter
                cleaned_data = []
                for trace in plotly_data['data']:
                    if isinstance(trace, dict):
                        if 'type' in trace and trace['type'] == 'scattermap':
                            trace['type'] = 'scatter'  # Convert to regular scatter
                        cleaned_data.append(trace)
                
                fig = go.Figure(data=cleaned_data)
                if 'layout' in plotly_data:
                    # Clean layout properties
                    layout = plotly_data['layout'].copy()
                    if 'template' in layout:
                        template = layout['template'].copy()
                        if 'data' in template:
                            template_data = template['data'].copy()
                            if 'scattermap' in template_data:
                                del template_data['scattermap']
                            template['data'] = template_data
                        layout['template'] = template
                    fig.update_layout(layout)
                st.plotly_chart(fig, use_container_width=True)
                if st.button("Zurück zur Übersicht", key=f"btn_back_{storey}"):
                    st.session_state[button_key] = False
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading JSON data: {str(e)}")
            st.session_state[button_key] = False
            st.rerun()

def display_zone_layouts(graph_path):
    """Display zone layouts for all storeys"""
    storey_files = get_storey_files(graph_path, 'zone')
    
    if storey_files:
        st.header("Zone Floor Layouts")
        # Create tabs for each storey
        storey_tabs = st.tabs([storey for storey in storey_files.keys()])
        
        for tab, (storey, files) in zip(storey_tabs, storey_files.items()):
            with tab:
                display_storey_content(storey, files, graph_path)
    else:
        st.warning("No zone floor layouts found")

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"Zones - {building}")
    
    paths = get_project_paths(building)
    display_zone_layouts(paths['graph'])
else:
    st.warning("Please select a building from the home page") 