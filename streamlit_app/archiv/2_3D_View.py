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
    """Display 3D visualization from Plotly JSON file"""
    if is_azure_environment():
        if not is_dir(get_base_project_path(), graph_path):
            st.warning(f"Graph directory not found at: {graph_path}")
            return
        files = list_files(get_base_project_path(), graph_path)
    else:
        if not os.path.exists(graph_path):
            st.warning(f"Graph directory not found at: {graph_path}")
            return
        files = os.listdir(graph_path)

    json_file = None
    for file in files:
        # Get just the filename from the full path
        filename = os.path.basename(file)
        if filename.lower() == 'titel_picture.json':
            json_file = file  # Keep the full path
            break

    if json_file:
        try:
            if is_azure_environment():
                json_data = read_file(get_base_project_path(), json_file)
                plotly_data = json.loads(json_data.decode('utf-8'))
            else:
                with open(json_file, 'r') as f:
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
        except Exception as e:
            st.error(f"Error loading JSON data: {str(e)}")
    else:
        st.warning("No 3D visualization data found")

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"3D View - {building}")
    
    paths = get_project_paths(building)
    display_3d_visualization(paths['graph'])
else:
    st.warning("Please select a building from the home page") 