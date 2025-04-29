from pathlib import Path
import pandas as pd
import yaml


def _build_metrics_table(
    metrics_df: pd.DataFrame, 
    base_metrics: dict = None,
    include_metrics: list = None,
    language: str = None
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
    config = _load_metrics_config()
    
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

def _load_metrics_config() -> dict:
    """
    Helper function to load metrics configuration from YAML file.
    Used by other functions to load configuration.
    
    Returns:
        dict: Configuration dictionary
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    # Get the workspace root directory (two levels up from the current file)
    workspace_root = Path(__file__).parent.parent.parent
    config_path = workspace_root / 'src' / 'qto_buccaneer' / 'configs' / 'abstractBIM_report_config.yaml'
    print(f"Loading metrics config from: {config_path}")  # Debug print
    if not config_path.exists():
        raise FileNotFoundError(f"Metrics configuration file not found at: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        print(f"Loaded config sections: {list(config.keys())}")  # Debug print
        return config
