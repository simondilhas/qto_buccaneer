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
    page_title="Abstandsflächen",
    page_icon="📏",
    layout="wide"
)

def get_storey_files(graph_path, prefix):
    """Get all files for each storey with a specific prefix"""
    storey_files = {}
    
    if is_azure_environment():
        if not is_dir(get_base_project_path(), graph_path):
            st.write(f"Debug - Directory not found: {graph_path}")
            return storey_files
        files = list_files(get_base_project_path(), graph_path)
        st.write("Debug - All files found:", files)
    else:
        if not os.path.exists(graph_path):
            st.write(f"Debug - Directory not found: {graph_path}")
            return storey_files
        files = os.listdir(graph_path)
        st.write("Debug - All files found:", files)
    
    for file in files:
        # Get just the filename from the full path
        filename = os.path.basename(file)
        st.write(f"Debug - Checking file: {filename}")
        if filename.startswith(f"floor_layout_by_abstandsflächen_"):
            st.write(f"Debug - Found abstandsflächen file: {filename}")
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.json')):
                # Extract storey from filename
                match = re.search(r'floor_layout_by_abstandsflächen_(.+?)(?:\.\w+)?$', filename)
                if match:
                    storey = match.group(1)
                    st.write(f"Debug - Extracted storey: {storey}")
                    if storey not in storey_files:
                        storey_files[storey] = {'png': None, 'json': None}
                    
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        storey_files[storey]['png'] = file  # Keep full path
                        st.write(f"Debug - Added PNG file for {storey}: {file}")
                    elif filename.endswith('.json'):
                        storey_files[storey]['json'] = file  # Keep full path
                        st.write(f"Debug - Added JSON file for {storey}: {file}")
    
    st.write("Debug - Final storey_files:", storey_files)
    
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

def display_abstandsflächen_layouts(graph_path):
    """Display Abstandsflächen layouts for all storeys"""
    st.write("Debug - Graph path:", graph_path)
    storey_files = get_storey_files(graph_path, 'abstandsflächen')
    
    if storey_files:
        st.header("Abstandsflächen Floor Layouts")
        # Create tabs for each storey
        storey_tabs = st.tabs([storey for storey in storey_files.keys()])
        
        for tab, (storey, files) in zip(storey_tabs, storey_files.items()):
            with tab:
                display_storey_content(storey, files, graph_path)
    else:
        st.warning("No Abstandsflächen floor layouts found")

def display_abstandsflächen_data(graph_path, building):
    """Display Abstandsflächen data"""
    st.write("Debug - Graph path:", graph_path)
    
    # Look for the specific JSON file
    json_file = f"{building}_abstractBIM_data.json"
    json_path = join_paths(graph_path, json_file)
    
    st.write("Debug - Looking for JSON file:", json_path)
    st.write("Debug - Is Azure environment:", is_azure_environment())
    
    try:
        if is_azure_environment():
            # In Azure, we need to use the full path
            st.write("Debug - Reading from Azure")
            json_data = read_file(get_base_project_path(), json_path)
            st.write("Debug - JSON data read successfully")
            # Handle double encoded JSON
            plotly_data = json.loads(json.loads(json_data.decode('utf-8')))
            st.write("Debug - JSON parsed successfully")
        else:
            st.write("Debug - Reading from local file")
            with open(json_path, 'r') as f:
                # Handle double encoded JSON
                plotly_data = json.loads(json.load(f))
            st.write("Debug - JSON parsed successfully")
        
        if isinstance(plotly_data, dict) and 'data' in plotly_data:
            st.write("Debug - Creating Plotly figure")
            fig = go.Figure(data=plotly_data['data'])
            if 'layout' in plotly_data:
                fig.update_layout(plotly_data['layout'])
            # Set the height to 800 pixels
            fig.update_layout(height=800)
            st.plotly_chart(fig, use_container_width=True)
            st.write("Debug - Plotly figure displayed")
        else:
            st.error("Invalid JSON data format")
            st.write("Debug - Plotly data structure:", plotly_data.keys() if isinstance(plotly_data, dict) else type(plotly_data))
    except Exception as e:
        st.error(f"Error loading JSON data: {str(e)}")
        st.write("Debug - Full error:", str(e))
        import traceback
        st.write("Debug - Traceback:", traceback.format_exc())

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"Abstandsflächen - {building}")
    
    paths = get_project_paths(building)
    # Use the new path for Abstandsflächen
    abstandsflächen_path = f"buildings/{building}/09_check_building_inside_envelop/visualizations/{building}_abstractBIM"
    display_abstandsflächen_data(abstandsflächen_path, building)
else:
    st.warning("Please select a building from the home page") 