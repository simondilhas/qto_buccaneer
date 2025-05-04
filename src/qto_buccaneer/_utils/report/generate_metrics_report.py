from pathlib import Path
import pandas as pd
import yaml
from typing import Union
import os
from weasyprint import HTML
from qto_buccaneer.report import ReportStyleConfig


def _build_metrics_table(
    metrics_df: pd.DataFrame, 
    base_metrics: dict = None,
    include_metrics: list = None,
    language: str = None,
    config_path: str = None
) -> dict:
    """
    Helper function to build a formatted metrics table from a DataFrame.
    Used by other functions to create metrics tables.
    
    Args:
        metrics_df (pd.DataFrame): DataFrame containing metrics data
        base_metrics (dict): Dictionary mapping metric names to their base metrics
        include_metrics (list): List of metric names to include
        language (str): Language code for display names
        
    Returns:
        dict: Dictionary containing sections with their metrics
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    print(f"Input metrics_df shape: {metrics_df.shape}")  # Debug print
    print(f"Input metrics_df columns: {metrics_df.columns.tolist()}")  # Debug print
    
    # Load configuration
    config = _load_metrics_config(config_path)
    
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

def _load_metrics_config(config_path: Union[str, Path]) -> dict:
    """
    Helper function to load metrics configuration from YAML file.
    Used by other functions to load configuration.
    
    Args:
        config_path: Path to the configuration file (string or Path object)
    
    Returns:
        dict: Configuration dictionary
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    # Convert string to Path if necessary
    config_path = Path(config_path) if isinstance(config_path, str) else config_path
    
    # Get the workspace root directory (two levels up from the current file)
    workspace_root = Path(__file__).parent.parent.parent
    print(f"Loading metrics config from: {config_path}")  # Debug print
    if not config_path.exists():
        raise FileNotFoundError(f"Metrics configuration file not found at: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        print(f"Loaded config sections: {list(config.keys())}")  # Debug print
        return config

from typing import Optional

def _convert_html_to_pdf(
    html_content: str, 
    output_path: str,
    style_config: Optional[ReportStyleConfig] = None
) -> str:
    """
    Helper function to convert HTML content to PDF using WeasyPrint with styling.
    Used by generate_metrics_report() to handle PDF conversion.
    
    Args:
        html_content (str): HTML content to convert
        output_path (str): Path where the PDF should be saved
        style_config (Optional[ReportStyleConfig]): Configuration for report styling
        
    Returns:
        str: Path to the generated PDF file
        
    Raises:
        Exception: If PDF conversion fails
        
    Note:
        This is an internal helper function and should not be called directly.
        Use generate_metrics_report() instead.
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
        
        # Set base URL to the output directory for resolving relative paths
        base_url = os.path.dirname(output_path)
        HTML(string=html_with_css, base_url=base_url).write_pdf(output_path)
        return output_path
    except Exception as e:
        raise Exception(f"Failed to convert HTML to PDF: {str(e)}")
    
def _format_definition_line(term: str, definition: str, width: int = 80) -> str:
    """
    Helper function to format a definition line.
    Used by other functions for text formatting.
    
    Args:
        term (str): The term being defined
        definition (str): The definition of the term
        width (int): The total width of the line
        
    Returns:
        str: The formatted definition line
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    # Create the line with term and definition
    line = f"{term}: {definition}"
    return _fill_text_line(line, width)

def _format_disclaimer(disclaimer: str, width: int = 80) -> str:
    """
    Helper function to format disclaimer text.
    Used by other functions for text formatting.
    
    Args:
        disclaimer (str): The disclaimer text
        width (int): The total width of the line
        
    Returns:
        str: The formatted disclaimer
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    return _fill_text_line(disclaimer, width)

def _render_template_with_filled_text(template, context):
    """
    Helper function to render template with filled text.
    Used by other functions for template rendering.
    
    Args:
        template: The Jinja2 template
        context (dict): The context for the template
        
    Returns:
        str: The rendered template with filled text
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    # Format definitions
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
    
    # Format each definition
    formatted_definitions = [
        _format_definition_line(term, definition)
        for term, definition in definitions
    ]
    
    # Format disclaimer
    disclaimer = "These quantities were generated automatically using the abstractBIM system. Accuracy depends on input quality. The general terms and conditions of abstract AG apply."
    formatted_disclaimer = _format_disclaimer(disclaimer)
    
    # Add formatted text to context
    context.update({
        'formatted_definitions': formatted_definitions,
        'formatted_disclaimer': formatted_disclaimer
    })
    
    return template.render(context)

def _fill_text_line(text: str, width: int = 80, fill_char: str = " ") -> str:
    """
    Helper function to fill a text line to a specific width.
    Used by other functions for text formatting.
    
    Args:
        text (str): The text to fill
        width (int): The total width of the line
        fill_char (str): The character to use for filling
        
    Returns:
        str: The filled text line
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    if not text:
        return fill_char * width
        
    # Split text into words
    words = text.split()
    if not words:
        return fill_char * width
        
    # Start with the first word
    lines = [words[0]]
    current_length = len(words[0])
    
    # Add remaining words
    for word in words[1:]:
        # If adding the word would exceed the width, start a new line
        if current_length + len(word) + 1 > width:
            lines.append(word)
            current_length = len(word)
        else:
            # Add the word to the current line
            lines[-1] += " " + word
            current_length += len(word) + 1
            
    # Fill each line to the specified width
    filled_lines = []
    for line in lines:
        # Calculate how many fill characters to add
        fill_count = width - len(line)
        if fill_count > 0:
            filled_line = line + (fill_char * fill_count)
        else:
            filled_line = line
        filled_lines.append(filled_line)
        
    return "\n".join(filled_lines)