import streamlit as st
import os
from pathlib import Path
import re
import json
import plotly.graph_objects as go
from azure_config import get_base_project_path

st.set_page_config(
    page_title="Zonen",
    layout="wide"
)

def get_project_paths(building_name):
    """Get the paths for a specific building"""
    return {
        'project': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name),
        'graph': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "11_abstractbim_plots"),
        'check': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "09_building_inside_envelope")
    }

def get_storey_files(graph_path):
    """Get all files for each storey"""
    storey_files = {}
    if os.path.exists(graph_path):
        for file in os.listdir(graph_path):
            if file.startswith("floor_layout_by_zone_"):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.json')):
                    # Extract storey from filename - everything after 'floor_layout_by_zone_'
                    match = re.search(r'floor_layout_by_zone_(.+?)(?:\.\w+)?$', file)
                    if match:
                        storey = match.group(1)
                        if storey not in storey_files:
                            storey_files[storey] = {'png': None, 'json': None}
                        
                        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                            storey_files[storey]['png'] = os.path.join(graph_path, file)
                        elif file.endswith('.json'):
                            storey_files[storey]['json'] = os.path.join(graph_path, file)
    
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

def display_storey_content(storey, files):
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
        st.image(files['png'], caption=None)
    elif st.session_state[button_key] and files['json']:
        try:
            with open(files['json'], 'r') as f:
                plotly_data = json.load(f)
                if isinstance(plotly_data, dict) and 'data' in plotly_data:
                    fig = go.Figure(data=plotly_data['data'])
                    if 'layout' in plotly_data:
                        fig.update_layout(plotly_data['layout'])
                    st.plotly_chart(fig, use_container_width=True)
        except json.JSONDecodeError:
            st.warning(f"Could not load JSON data for storey {storey}")
            st.session_state[button_key] = False
            st.experimental_rerun()

def display_zone_layouts(graph_path):
    """Display zone layouts for all storeys"""
    storey_files = get_storey_files(graph_path)
    
    if storey_files:
        st.header("Zone Floor Layouts")
        # Create tabs for each storey
        storey_tabs = st.tabs([storey for storey in storey_files.keys()])
        
        for tab, (storey, files) in zip(storey_tabs, storey_files.items()):
            with tab:
                display_storey_content(storey, files)
    else:
        st.warning("No zone floor layouts found")

# Configure base path using environment-aware configuration
BASE_PROJECT_FOLDER = get_base_project_path()

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"Zonen - {building}")
    
    paths = get_project_paths(building)
    display_zone_layouts(paths['graph'])
else:
    st.warning("Please select a building from the home page") 