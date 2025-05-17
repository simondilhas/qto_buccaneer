import streamlit as st
import os
from pathlib import Path
import pandas as pd
from azure_config import get_base_project_path, is_azure_environment
from file_utils import list_files, read_file, exists, join_paths, is_dir
import plotly.express as px
import plotly.graph_objects as go

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

def display_metrics(metrics_path):
    """Display metrics from Excel files"""
    if is_azure_environment():
        if not is_dir(BASE_PROJECT_FOLDER, metrics_path):
            st.warning(f"Metrics directory not found at: {metrics_path}")
            return
        # Get all Excel files
        excel_files = [f for f in list_files(BASE_PROJECT_FOLDER, metrics_path) if f.endswith(('.xlsx', '.xls'))]
    else:
        if not os.path.exists(metrics_path):
            st.warning(f"Metrics directory not found at: {metrics_path}")
            return
        excel_files = [f for f in os.listdir(metrics_path) if f.endswith(('.xlsx', '.xls'))]
    
    if not excel_files:
        st.warning("No Excel files found in metrics directory")
        return

    # Metric name mapping for standardization
    metric_mapping = {
        # Geschossfläche
        'GF Gesamt': 'gf_total',
        'GF oi Neubau': 'gf_above',
        'GF ui Neubau': 'gf_below',
        'EBF': 'ebf',
        'KF': 'kf_total',
        
        # Nutzfläche
        'HNF Total': 'hnf_total',
        'NNF Total': 'nnf',
        'VF Verkehrsfläche Neubau': 'vf',
        'FF Funktionsfläche Neubau: m2': 'ff',
        'KF Konstruktionsfläche Total': 'kf_total_2',  # Changed to avoid duplicate key
        
        # Volumenkennwerte
        'GV Neubau oi': 'gv_oi',
        'GV ui Neubau': 'gv_ui',
        
        # Display names for metrics
        'gf_total': 'GF Gesamt',
        'gf_above': 'GF oi',
        'gf_below': 'GF ui',
        'ebf': 'EBF',
        'kf_total': 'KF Konstruktionsfläche',
        'kf_total_2': 'KF Konstruktionsfläche',  # Added display name for new key
        'hnf_total': 'HNF Hauptnutzfläche',
        'nnf': 'NNF Nebennutzfläche',
        'vf': 'VF Verkehrsfläche',
        'ff': 'FF Funktionsfläche',
        'gv_ui': 'GV ui',
        'gv_oi': 'GV oi'
    }

    # Create tabs for each section
    tab1, tab2, tab3 = st.tabs(["Gebäudekennzahlen", "Bauteilkennzahlen", "Daten"])
    
    with tab1:
        try:
            # Read the Excel file
            if is_azure_environment():
                file_path = excel_files[0]
                file_bytes = read_file(BASE_PROJECT_FOLDER, file_path)
                df = pd.read_excel(file_bytes)
            else:
                file_path = os.path.join(metrics_path, excel_files[0])
                df = pd.read_excel(file_path)
            
            # Convert to dictionary with standardized names
            metrics_dict = {}
            for metric_name, value in zip(df['metric_name'], df['value']):
                if metric_name in metric_mapping:
                    metrics_dict[metric_mapping[metric_name]] = value
            
            # Calculate total GV
            gv_ui = metrics_dict.get('gv_ui', 0)
            gv_oi = metrics_dict.get('gv_oi', 0)
            metrics_dict['gv_total'] = gv_ui + gv_oi
            
            # Display Geschossfläche metrics horizontally
            st.subheader("Flächenkennwerte [m²]")
            cols_gf = st.columns(5)
            
            # Function to display metric without unit
            def display_metric_no_unit(col, title, value):
                with col:
                    st.metric(
                        label=title,
                        value=f"{value:,.1f}".replace(",", "'"),
                        delta=None
                    )
            
            # First row
            display_metric_no_unit(cols_gf[0], metric_mapping['gf_total'], metrics_dict.get('gf_total', 0))
            display_metric_no_unit(cols_gf[1], metric_mapping['gf_above'], metrics_dict.get('gf_above', 0))
            display_metric_no_unit(cols_gf[2], metric_mapping['gf_below'], metrics_dict.get('gf_below', 0))
            display_metric_no_unit(cols_gf[3], metric_mapping['ebf'], metrics_dict.get('ebf', 0))
            with cols_gf[4]:
                st.metric(label="", value="", delta=None)  # Empty column with no value
            
            # Display Nutzfläche metrics horizontally with ratios
            cols_nf = st.columns(5)
            gf_total = metrics_dict.get('gf_total', 0)
            
            # Function to display metric with ratio
            def display_metric_with_ratio(col, title, value, ratio_value, unit="m²"):
                with col:
                    st.metric(
                        label=title,
                        value=f"{value:,.1f}".replace(",", "'"),
                        delta=None
                    )
                    if ratio_value > 0:
                        st.caption(f"{ratio_value:.1f}% von GF")
            
            if gf_total > 0:
                # Calculate ratios
                hnf_gf = (metrics_dict.get('hnf_total', 0) / gf_total) * 100
                nnf_gf = (metrics_dict.get('nnf', 0) / gf_total) * 100
                vf_gf = (metrics_dict.get('vf', 0) / gf_total) * 100
                ff_gf = (metrics_dict.get('ff', 0) / gf_total) * 100
                kf_gf = (metrics_dict.get('kf_total_2', 0) / gf_total) * 100
                
                # Display metrics with their ratios
                display_metric_with_ratio(cols_nf[0], metric_mapping['hnf_total'], metrics_dict.get('hnf_total', 0), hnf_gf)
                display_metric_with_ratio(cols_nf[1], metric_mapping['nnf'], metrics_dict.get('nnf', 0), nnf_gf)
                display_metric_with_ratio(cols_nf[2], metric_mapping['vf'], metrics_dict.get('vf', 0), vf_gf)
                display_metric_with_ratio(cols_nf[3], metric_mapping['ff'], metrics_dict.get('ff', 0), ff_gf)
                display_metric_with_ratio(cols_nf[4], metric_mapping['kf_total_2'], metrics_dict.get('kf_total_2', 0), kf_gf)
            
            # Display Volumenkennwerte
            st.subheader("")
            st.subheader("Volumenkennwerte [m³]")
            cols_vol = st.columns(5)
            
            # Display volume metrics
            display_metric_no_unit(cols_vol[0], "GV Total", metrics_dict.get('gv_total', 0))
            display_metric_no_unit(cols_vol[1], metric_mapping['gv_ui'], metrics_dict.get('gv_ui', 0))
            display_metric_no_unit(cols_vol[2], metric_mapping['gv_oi'], metrics_dict.get('gv_oi', 0))
            with cols_vol[3]:
                st.metric(label="", value="", delta=None)  # Empty column
            with cols_vol[4]:
                st.metric(label="", value="", delta=None)  # Empty column
            
            # Save df for tab3
            st.session_state['metrics_df'] = df
        except Exception as e:
            st.error(f"Error loading metrics: {str(e)}")
    
    with tab2:
        st.write("Bauteilkennzahlen content will be added here")
    
    with tab3:
        try:
            # Display raw data
            st.subheader("Rohdaten")
            df = st.session_state.get('metrics_df', None)
            if df is not None:
                st.dataframe(df, use_container_width=True)
                # Add download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{os.path.splitext(excel_files[0])[0]}.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")

# Configure base path using environment-aware configuration
BASE_PROJECT_FOLDER = get_base_project_path()

if 'selected_building' in st.session_state:
    building = st.session_state['selected_building']
    st.title(f"Metrics - {building}")
    
    paths = get_project_paths(building)
    display_metrics(paths['metrics'])
else:
    st.warning("Please select a building from the home page") 