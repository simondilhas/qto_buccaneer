import streamlit as st
import os
from pathlib import Path
import pandas as pd
from azure_config import get_base_project_path, is_azure_environment
from file_utils import list_files, read_file, exists, join_paths, is_dir
import plotly.express as px
import plotly.graph_objects as go
import io

st.set_page_config(
    page_title="Metrics",
    page_icon="📊",
    layout="wide"
)


def get_project_paths(building_name):
    """Get the paths for a specific building"""
    if is_azure_environment():
        # In Azure, we just need the relative paths since we're using ContainerClient
        return {
            'project': join_paths('buildings', building_name),
            'graph': join_paths('buildings', building_name, "11_abstractbim_plots"),
            'check': join_paths('buildings', building_name, "09_building_inside_envelope"),
            'metrics': join_paths('buildings', building_name, "07_metrics")
        }
    else:
        # In local environment, we need full paths
        return {
            'project': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name),
            'graph': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "11_abstractbim_plots"),
            'check': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "09_building_inside_envelope"),
            'metrics': os.path.join(BASE_PROJECT_FOLDER, "buildings", building_name, "07_metrics")
        }

def display_metrics(building):
    """Display metrics for a building"""
    metrics_path = f"buildings/{building}/07_metrics"
    
    try:
        if is_azure_environment():
            excel_files = list_files(get_base_project_path(), metrics_path)
            excel_files = [f for f in excel_files if f.endswith('.xlsx')]
        else:
            if not os.path.exists(metrics_path):
                st.warning("No metrics found for this building")
                return
            excel_files = [f for f in os.listdir(metrics_path) if f.endswith('.xlsx')]
        
        if not excel_files:
            st.warning("No Excel files found in metrics directory")
            return
        
        # Display the first Excel file found
        excel_file = excel_files[0]
        excel_path = join_paths(metrics_path, excel_file)
        
        if is_azure_environment():
            excel_data = read_file(get_base_project_path(), excel_path)
            df = pd.read_excel(io.BytesIO(excel_data))
        else:
            df = pd.read_excel(excel_path)
        
        # Display the data
        st.dataframe(df)
        
    except Exception as e:
        st.error(f"Error loading metrics: {str(e)}")

# Configure base path using environment-aware configuration
BASE_PROJECT_FOLDER = get_base_project_path()

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"Metrics - {building}")
    
    paths = get_project_paths(building)
    display_metrics(building)
else:
    st.warning("Please select a building from the home page") 