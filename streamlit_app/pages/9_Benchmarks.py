import streamlit as st
import pandas as pd
import io
import os
from azure_config import get_base_project_path, is_azure_environment
from file_utils import read_file, join_paths, exists
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# Page config
st.set_page_config(
    page_title="Benchmarks",
    page_icon="📊",
    layout="wide"
)

# Configure base path using environment-aware configuration
BASE_PROJECT_FOLDER = get_base_project_path()

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"].strip() == st.secrets["password"].strip():
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

def display_kf_row(df):
    """Display the % Anteil KF an GF row with specific styling."""
    # Filter for the KF row using metric_name column
    kf_row = df[df['metric_name'] == "% Anteil KF an GF"]
    
    # Style the filtered dataframe
    def style_cells(val):
        if not isinstance(val, (int, float)):
            return ''
        
        if val < 0:
            return 'background-color: #ffcdd2'  # Red background for negative
        if 11 <= val <= 16:
            return 'color: #2e7d32'  # Green for in-range
        return 'color: #f57f17'  # Yellow for out-of-range
    
    # Apply the styling using Styler.map
    styled_df = kf_row.style.map(style_cells)
    
    # Display the styled dataframe
    st.subheader("% Anteil KF an GF")
    st.dataframe(
        styled_df,
        use_container_width=True
    )
    
    # Add a legend for the styling
    st.markdown("""
    <div style='margin: 10px 0;'>
        <div style='background-color: #ffcdd2; padding: 10px; border-radius: 5px; margin-bottom: 5px;'>
            🔴 Negative values have red background
        </div>
        <div style='color: #2e7d32; padding: 10px; border-radius: 5px; margin-bottom: 5px;'>
            🟢 Values between 11-16% are shown in green
        </div>
        <div style='color: #f57f17; padding: 10px; border-radius: 5px;'>
            🟡 Values outside 11-16% range are shown in yellow
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_all_benchmarks(df):
    """Display the full benchmark dataframe."""
    st.subheader("All Benchmarks")
    st.dataframe(
        df,
        use_container_width=True,
        height=400
    )

def highlight_nan(val):
    """Highlight NaN values in a dataframe."""
    if pd.isna(val):
        return 'background-color: #ffeb3b'  # Yellow background for NaN
    return ''

def display_nan_table(df):
    """Display a table highlighting NaN values."""
    st.subheader("Data with NaN Highlighted")
    styled_df = df.style.map(highlight_nan)
    st.dataframe(styled_df, use_container_width=True)

def display_heatmap(df):
    """Display a heatmap of the benchmark data using Plotly Express."""
    st.subheader("Benchmark Heatmap")
    
    try:
        # Ensure all columns except 'metric_name' are numeric
        numeric_df = df.drop(columns=['metric_name']).apply(pd.to_numeric, errors='coerce')
        
        # Fill NaN values with a placeholder (e.g., 0) or drop them
        numeric_df = numeric_df.fillna(0)
        
        # Create a heatmap using Plotly Express
        fig = px.imshow(
            numeric_df,
            labels=dict(x="Metrics", y="Variants", color="Value"),
            x=numeric_df.columns,
            y=df['metric_name'],
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Viridis"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating heatmap: {str(e)}")

def display_gf_chart(df):
    """Display a bar chart for GF oi Neubau and GF ui Neubau."""
    st.subheader("GF oi Neubau and GF ui Neubau Chart")
    
    try:
        # Filter the dataframe for the relevant rows
        gf_data = df[df['metric_name'].isin(['GF oi Neubau', 'GF ui Neubau'])]
        
        # Melt the dataframe to have a long format suitable for Plotly
        melted_df = gf_data.melt(id_vars='metric_name', var_name='Project', value_name='Value')
        
        # Create a bar chart
        fig = px.bar(
            melted_df,
            x='Project',
            y='Value',
            color='metric_name',
            barmode='group',
            labels={'Value': 'Area', 'Project': 'Project'},
            title='Comparison of GF oi Neubau and GF ui Neubau'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating GF chart: {str(e)}")

import streamlit as st
import pandas as pd
import plotly.express as px

# Load your data


import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

def display_single_metric_bar_chart(df):
    """Display a bar chart for a single selected metric using matplotlib."""
    st.subheader("Metric Comparison per Project")

    # Let user select one metric
    metric_names = df['metric_name'].unique()
    selected_metric = st.selectbox("Select a metric to display", metric_names)

    # Filter data
    filtered_df = df[df['metric_name'] == selected_metric].sort_values(by='building')

    if filtered_df.empty:
        st.warning("No data found for the selected metric.")
        return

    # Plot with matplotlib
    fig, ax = plt.subplots(figsize=(20, 6))
    ax.bar(filtered_df['building'], filtered_df['value'], color='skyblue')

    ax.set_title(f"{selected_metric} per Project")
    ax.set_ylabel(f"Value ({filtered_df['unit'].iloc[0]})")
    ax.set_xlabel("Project")
    ax.tick_params(axis='x', rotation=45)
    ax.grid(axis='y')
    sns.despine()

    st.pyplot(fig)





def load_excel_file(file_name):
    """Load an Excel file from the project folder."""
    try:
        excel_path = join_paths('buildings', file_name)
        if not exists(BASE_PROJECT_FOLDER, excel_path):
            st.warning(f"No data found for {file_name}")
            return None

        # Read Excel file
        if is_azure_environment():
            excel_data = read_file(BASE_PROJECT_FOLDER, excel_path)
            df = pd.read_excel(io.BytesIO(excel_data))
        else:
            df = pd.read_excel(os.path.join(BASE_PROJECT_FOLDER, excel_path))
            

        return df
    except Exception as e:
        st.error(f"Error loading {file_name}: {str(e)}")
        return None



def display_benchmark_data():
    """Main function to display benchmark data."""
    st.title("Building Benchmarks")
    
    # Load benchmark data
    df_benchmark = load_excel_file('building_comparison.xlsx')
    if df_benchmark is None:
        return

    df_all_metrics = load_excel_file('all_metrics.xlsx')
    if df_all_metrics is None:
        return
    
    df_all_metrics['value'] = (
        df_all_metrics['value']
        .astype(str)                      # ensure string first
        .str.replace(',', '')             # remove thousands separator
        .str.replace(' ', '')             # remove stray spaces
        .str.replace('m2', '')            # if any units snuck in
        .astype(float)                    # convert properly
    )


    # Enforce value column is numeric
    df_all_metrics['value'] = pd.to_numeric(df_all_metrics['value'], errors='coerce')

    
    display_single_metric_bar_chart(df_all_metrics)

    # Display the specific KF row
    display_kf_row(df_benchmark)


    
    # Display all benchmarks
    display_all_benchmarks(df_benchmark)
    
    # Display table highlighting NaN values
    display_nan_table(df_benchmark)

    
    # Add download button for the data
    csv = df_benchmark.to_csv(index=False)
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="building_comparison.csv",
        mime="text/csv"
    )

def main():
    if not check_password():
        return
    display_benchmark_data()

if __name__ == "__main__":
    main() 