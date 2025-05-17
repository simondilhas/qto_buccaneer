import streamlit as st
import os
from pathlib import Path
import json
import plotly.graph_objects as go
from azure_config import get_base_project_path

st.set_page_config(
    page_title="Check",
    page_icon="✅",
    layout="wide"
)

def get_project_paths(building_name):
    """Get the paths for a specific building"""
    return {
        'project': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name),
        'graph': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "11_abstractbim_plots"),
        'check': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "09_check_building_inside_envelop")
    }

def display_check_visualization(check_path, building_name):
    """Display check visualization from Plotly JSON file"""
    # Construct path to the building-specific subfolder
    building_check_path = os.path.join(check_path, "visualizations", f"{building_name}_abstractBIM")
    
    if not os.path.exists(building_check_path):
        st.warning(f"Check directory not found: {building_check_path}")
        return

    # Look for JSON file
    json_file = None
    for file in os.listdir(building_check_path):
        if file.endswith('_data.json'):
            json_file = os.path.join(building_check_path, file)
            break
    
    if json_file:
        try:
            with open(json_file, 'r') as f:
                json_str = f.read()
                # First parse to get the string
                data_str = json.loads(json_str)
                # Second parse to get the actual data
                data = json.loads(data_str)
                
                # Create figure from the JSON data
                if isinstance(data, dict):
                    if 'data' in data:
                        fig = go.Figure(data=data['data'])
                    else:
                        st.error("No 'data' key found in JSON")
                        return
                else:
                    st.error(f"Expected dictionary, got {type(data)}")
                    return
                
                # Update layout with the JSON layout settings
                if 'layout' in data:
                    fig.update_layout(data['layout'])
                
                # Make the figure larger
                fig.update_layout(
                    height=1000,
                    width=1200,
                    margin=dict(l=0, r=0, t=50, b=0)
                )
                
                # Display the figure
                st.plotly_chart(fig, use_container_width=True)
        except json.JSONDecodeError as e:
            st.error(f"Error parsing JSON data: {str(e)}")
        except Exception as e:
            st.error(f"Error loading visualization: {str(e)}")
    else:
        st.warning("No visualization JSON file found")

# Configure base path using environment-aware configuration
BASE_PROJECT_FOLDER = get_base_project_path()

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"Check - {building}")
    
    paths = get_project_paths(building)
    display_check_visualization(paths['check'], building)
else:
    st.warning("Please select a building from the home page") 