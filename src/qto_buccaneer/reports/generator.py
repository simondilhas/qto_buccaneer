import os
from pathlib import Path
from typing import Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime
import yaml
import pandas as pd

from .config import ReportStyleConfig
from .excel.exporter import export_to_excel
from .utils.text_formatting import format_definition_line, format_disclaimer

def load_metrics_config() -> dict:
    """
    Load metrics configuration from YAML file.
    
    Returns:
        dict: Configuration dictionary
    """
    # Get the package root directory (where the reports module is located)
    package_root = Path(__file__).parent.parent
    
    # Construct path to config file
    config_path = package_root / 'configs' / 'abstractBIM_report_config.yaml'
    print(f"Loading metrics config from: {config_path}")  # Debug print
    
    if not config_path.exists():
        raise FileNotFoundError(f"Metrics configuration file not found at: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        print(f"Loaded config sections: {list(config.keys())}")  # Debug print
        return config

def build_metrics_table(
    metrics_df: pd.DataFrame, 
    base_metrics: dict = None,
    include_metrics: list = None,
    language: str = None
) -> dict:
    """
    Build a formatted metrics table from a DataFrame of metrics.
    
    Args:
        metrics_df (pd.DataFrame): DataFrame containing metrics with columns:
            - metric_name: Name of the metric
            - value: Numeric value
            - unit: Unit of measurement
        base_metrics (dict): Dictionary mapping metric names to their base metrics for percentages.
            If None, will use base_metrics from config.
        include_metrics (list): List of metric names to include in the table.
            If None, will use metrics defined in sections from config.
        language (str): Language code to use for display names (e.g., 'en', 'de').
            If None, will use default_language from config.
            
    Returns:
        dict: Dictionary containing sections with their metrics
    """
    print(f"Input metrics_df shape: {metrics_df.shape}")  # Debug print
    print(f"Input metrics_df columns: {metrics_df.columns.tolist()}")  # Debug print
    
    # Load configuration
    config = load_metrics_config()
    
    # Use default language if none specified
    if language is None:
        language = config.get('default_language', 'en')
    print(f"Using language: {language}")  # Debug print
    
    # Get all defined metrics from the configuration
    defined_metrics = set()
    for section in config.get('sections', []):
        if 'metrics' in section:
            defined_metrics.update(section.get('metrics', []))
    
    print(f"Defined metrics in config: {defined_metrics}")  # Debug print
    
    # First filter to only include metrics that exist in the DataFrame
    available_metrics = set(metrics_df['metric_name'].unique())
    print(f"Available metrics in DataFrame: {available_metrics}")  # Debug print
    
    # Determine which metrics to include
    if include_metrics and len(include_metrics) > 0:
        print(f"Using provided include_metrics: {include_metrics}")  # Debug print
        # Convert include_metrics to set for faster lookups
        include_metrics_set = set(include_metrics)
        # Only keep metrics that are both in include_metrics and available_metrics
        filtered_metrics = include_metrics_set.intersection(available_metrics)
        print(f"Metrics after include_metrics filter: {filtered_metrics}")  # Debug print
    else:
        # If no include_metrics provided or empty list, use defined metrics that are available
        filtered_metrics = defined_metrics.intersection(available_metrics)
        print(f"No include_metrics provided, using defined metrics: {filtered_metrics}")  # Debug print
    
    # Filter the DataFrame to only include the filtered metrics
    metrics_df = metrics_df[metrics_df['metric_name'].isin(filtered_metrics)].copy()
    print(f"Final DataFrame shape after filtering: {metrics_df.shape}")  # Debug print
    
    # Use provided base_metrics or load from config
    if base_metrics is None:
        base_metrics = {}
        for metric_id, metric_config in config.get('metrics', {}).items():
            if metric_config.get('base_metric'):
                base_metrics[metric_id] = metric_config['base_metric']
    
    # Get base metric values
    base_values = {}
    for base_metric in set(base_metrics.values()):
        try:
            base_values[base_metric] = metrics_df[metrics_df['metric_name'] == base_metric]['value'].iloc[0]
        except IndexError:
            base_values[base_metric] = 0
    
    # Build metrics table by sections
    result = {}
    for section in config.get('sections', []):
        section_id = section['id']
        section_title = section['title'].get(language, section['title']['en'])
        
        # Handle special sections
        if section_id == 'title_page':
            result[section_id] = {
                'title': section_title,
                'metrics': []  # No metrics for title page
            }
            continue
            
        if section_id == 'table_of_contents':
            result[section_id] = {
                'title': section_title,
                'metrics': []  # No metrics for table of contents
            }
            continue
            
        # Handle metrics sections
        section_metrics = []
        for metric_id in section.get('metrics', []):
            if metric_id not in filtered_metrics:
                continue
                
            metric_config = config['metrics'].get(metric_id, {})
            metric_row = metrics_df[metrics_df['metric_name'] == metric_id].iloc[0]
            
            # Get display name in selected language
            display_name = metric_config['name'].get(language, metric_config['name']['en'])
            
            # Format the value with unit - show just the number for count metrics
            value = metric_row['value']
            unit = metric_row['unit']
            if unit == 'count':
                formatted_value = f"{value}"
            else:
                formatted_value = f"{value:.2f} {unit}"
            
            # Calculate and format percentage if applicable
            percentage = ''
            base_metric = metric_config.get('base_metric')
            if base_metric:
                base_value = base_values.get(base_metric, 0)
                if base_value > 0:
                    pct = (value / base_value) * 100
                    base_name = config['metrics'][base_metric]['name'].get(language, config['metrics'][base_metric]['name']['en'])
                    percentage = config['formatting']['percentage']['format'].format(
                        value=pct,
                        base_name=base_name.split('(')[0].strip(),
                        of_word=config['formatting']['percentage']['languages'].get(language, 'of')
                    )
            
            section_metrics.append({
                'name': display_name,
                'value1': formatted_value,
                'value2': percentage
            })
        
        if section_metrics:  # Only add section if it has metrics
            result[section_id] = {
                'title': section_title,
                'metrics': section_metrics
            }
    
    print(f"Final sections: {list(result.keys())}")  # Debug print
    return result

def generate_metrics_report(
    metrics_df: pd.DataFrame,
    project_info: dict,
    excel_path: str = 'metrics/all_metrics.xlsx',
    image_dir: str = 'images',
    template_path: str = 'configs',
    output_path: str = 'generated_report.pdf',
    image_placeholders: list = None,
    image_formats: list = None,
    report_template: str = 'abstractBIM_report_template.html',
    style_config: Optional[ReportStyleConfig] = None,
    report_config_path: str = None
) -> str:
    """
    Generate a metrics report from the provided metrics DataFrame.
    
    Args:
        metrics_df (pd.DataFrame): DataFrame containing the metrics data
        project_info (dict): Dictionary containing project information
        excel_path (str): Path to save the metrics Excel file
        image_dir (str): Directory containing report images
        template_path (str): Directory containing the report template
        output_path (str): Path where the final PDF report will be saved
        image_placeholders (list): List of image placeholder names to look for
        image_formats (list): List of image file extensions to check
        report_template (str): Name of the report template file
        style_config (Optional[ReportStyleConfig]): Configuration for report styling
        report_config_path (str): Path to the report configuration YAML file
        
    Returns:
        str: Path to the generated PDF report
    """
    # Get the package root directory (where the reports module is located)
    package_root = Path(__file__).parent.parent
    
    # Convert relative paths to absolute paths
    template_path = str(package_root / template_path)
    image_dir = str(package_root.parent.parent / image_dir)
    excel_path = str(package_root.parent.parent / excel_path)
    output_path = str(package_root.parent.parent / output_path)
    
    print(f"Looking for template in: {template_path}")  # Debug print
    
    # Validate project info
    required_info = ['project_name', 'file_name', 'address']
    missing_info = [key for key in required_info if key not in project_info]
    if missing_info:
        raise ValueError(f"Missing required project info: {', '.join(missing_info)}")
    
    # Set default image placeholders and formats if not provided
    if image_placeholders is None:
        image_placeholders = ['pic_gfa', 'pic_gv', 'pic_project', 'pic_room_floorplan_scale']
    if image_formats is None:
        image_formats = ['.png', '.jpg', '.jpeg']
    
    # Save metrics to Excel
    os.makedirs(os.path.dirname(excel_path), exist_ok=True)
    metrics_df.to_excel(excel_path, index=False)
    
    # Collect available images
    images = {}
    for key in image_placeholders:
        found = False
        for ext in image_formats:
            img_path = os.path.join(image_dir, f"{key}{ext}")
            if os.path.isfile(img_path):
                images[key] = img_path
                found = True
                break
        if not found:
            images[key] = None
    
    # Verify template directory and file
    if not os.path.isdir(template_path):
        raise FileNotFoundError(f"Template directory not found: {template_path}")
    template_file = os.path.join(template_path, report_template)
    if not os.path.isfile(template_file):
        raise FileNotFoundError(f"Template file not found: {template_file}")
    
    # Load report configuration if provided
    include_metrics = None
    if report_config_path:
        try:
            with open(report_config_path, 'r') as f:
                report_config = yaml.safe_load(f)
                include_metrics = report_config.get('include_metrics', [])
                print(f"Loaded include_metrics from config: {include_metrics}")  # Debug print
        except Exception as e:
            print(f"Warning: Could not load report config: {e}")
    
    # Create metrics table using the new function
    metrics_table = build_metrics_table(metrics_df, include_metrics=include_metrics)
    
    # Format definitions and disclaimer
    definitions = [
        ("Gross Floor Area (GFA)", "The total area of all floors in a building, measured from the exterior walls."),
        ("Gross Volume (GV)", "The total volume of the building, including all enclosed spaces."),
        ("Net Floor Area (NFA)", "The usable area within the building, excluding walls."),
        ("Net Volume (NV)", "The volume of usable space within the building."),
        ("Construction Area", "Difference between GFA and NFA."),
        ("Construction Volume", "Difference between GV and NV."),
        ("Facade Area (FA)", "The total exterior surface area of the building envelope."),
        ("Room Type", "A classification of rooms based on their intended function."),
        ("Spatial Relationships", "Position between elements (e.g., a window relating to a room)."),
        ("Storey", "A horizontal division of a building."),
        ("Baseplate", "The foundational slab at the bottom of the building."),
        ("Covering Area", "Area of facade elements like cladding and panels.")
    ]
    
    formatted_definitions = [
        format_definition_line(term, definition)
        for term, definition in definitions
    ]
    
    disclaimer = "These quantities were generated automatically using the abstractBIM system. Accuracy depends on input quality. The general terms and conditions of abstract AG apply."
    formatted_disclaimer = format_disclaimer(disclaimer)
    
    # Render HTML
    env = Environment(loader=FileSystemLoader(template_path))
    template = env.get_template(report_template)
    
    html_out = template.render(
        project_name=project_info['project_name'],
        file_name=project_info['file_name'],
        address=project_info['address'],
        date_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
        images=images,
        logo_path=style_config.logo_path if style_config else None,
        metrics_table=metrics_table,
        formatted_definitions=formatted_definitions,
        formatted_disclaimer=formatted_disclaimer
    )
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir:  # Only create directory if path contains a directory component
        os.makedirs(output_dir, exist_ok=True)
    
    # Save HTML
    html_path = output_path.replace('.pdf', '.html')
    with open(html_path, 'w') as f:
        f.write(html_out)
    
    # Convert to PDF with styling
    try:
        convert_html_to_pdf(html_out, output_path, style_config)
    except Exception as e:
        print(f"Warning: Could not convert to PDF: {e}")
        print(f"HTML report saved at: {html_path}")
        return html_path
    
    return output_path

def convert_html_to_pdf(
    html_content: str, 
    output_path: str,
    style_config: Optional[ReportStyleConfig] = None
) -> str:
    """
    Convert HTML content to PDF using WeasyPrint with styling.
    
    Args:
        html_content (str): HTML content to convert
        output_path (str): Path where the PDF should be saved
        style_config (Optional[ReportStyleConfig]): Configuration for report styling
        
    Returns:
        str: Path to the generated PDF file
        
    Raises:
        Exception: If PDF conversion fails
    """
    try:
        # Use default config if none provided
        style_config = style_config or ReportStyleConfig()
        
        # Add CSS to HTML content
        css = style_config.to_css()
        html_with_css = f"""
            <style>
                {css}
            </style>
            {html_content}
        """
        
        HTML(string=html_with_css).write_pdf(output_path)
        return output_path
    except Exception as e:
        raise Exception(f"Failed to convert HTML to PDF: {str(e)}") 