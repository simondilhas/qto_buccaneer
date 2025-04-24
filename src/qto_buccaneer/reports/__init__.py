from .config import ExcelLayoutConfig, ReportStyleConfig
from .generator import generate_metrics_report
from .comparison import (
    create_project_comparison_df,
    export_project_comparison_excel,
    room_program_comparison,
    export_room_program_comparison
)

def create_abstractBIM_metrics_report(
    metrics_df,
    project_info,
    output_dir="reports",
    report_name="abstractBIM_metrics_report",
    style_config=None
):
    """
    Generate a comprehensive metrics report for an abstractBIM project.
    
    Args:
        metrics_df (pd.DataFrame): DataFrame containing the metrics data
        project_info (Dict[str, str]): Dictionary containing project information
            Required keys: project_name, file_name, address
        output_dir (str): Directory where reports will be saved
        report_name (str): Base name for the report files
        style_config (Optional[ReportStyleConfig]): Configuration for report styling
        
    Returns:
        str: Path to the generated PDF report
    """
    from pathlib import Path
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate the report
    pdf_path = str(output_dir / f"{report_name}.pdf")
    excel_path = str(output_dir / f"{report_name}.xlsx")
    
    return generate_metrics_report(
        metrics_df=metrics_df,
        project_info=project_info,
        excel_path=excel_path,
        output_path=pdf_path,
        style_config=style_config
    )

def create_project_comparison_report(
    metrics_df,
    output_dir="reports",
    report_name="project_comparison",
    metrics=None,
    layout_config=None
):
    """
    Generate a comparison report between multiple projects.
    
    Args:
        metrics_df (pd.DataFrame): DataFrame containing metrics data for multiple projects
        output_dir (str): Directory where reports will be saved
        report_name (str): Base name for the report files
        metrics (Optional[List[str]]): List of metric names to include in the comparison
        layout_config (Optional[ExcelLayoutConfig]): Configuration for Excel layout
        
    Returns:
        str: Path to the generated Excel report
    """
    from pathlib import Path
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate the comparison report
    excel_path = str(output_dir / f"{report_name}.xlsx")
    
    return export_project_comparison_excel(
        df=metrics_df,
        output_path=excel_path,
        metrics=metrics,
        layout_config=layout_config
    )

def create_room_program_comparison_report(
    target_excel_path,
    ifc_loader,
    output_dir="reports",
    report_name="room_program_comparison",
    room_name_column="LongName",
    target_count_column="Target Count",
    target_area_column="Target Area/Room",
    layout_config=None
):
    """
    Generate a comparison report between target room program and actual IFC spaces.
    
    Args:
        target_excel_path (str): Path to Excel file containing target room program
        ifc_loader: Instance of IfcLoader with loaded IFC model
        output_dir (str): Directory where reports will be saved
        report_name (str): Base name for the report files
        room_name_column (str): Column name in target Excel for room names
        target_count_column (str): Column name for target room count
        target_area_column (str): Column name for target room area
        layout_config (Optional[ExcelLayoutConfig]): Configuration for Excel layout
        
    Returns:
        str: Path to the generated Excel report
    """
    from pathlib import Path
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate the comparison report
    excel_path = str(output_dir / f"{report_name}.xlsx")
    
    return room_program_comparison(
        target_excel_path=target_excel_path,
        ifc_loader=ifc_loader,
        room_name_column=room_name_column,
        target_count_column=target_count_column,
        target_area_column=target_area_column,
        output_path=excel_path,
        layout_config=layout_config
    )

__all__ = [
    'create_abstractBIM_metrics_report',
    'create_project_comparison_report',
    'create_room_program_comparison_report',
    'ExcelLayoutConfig',
    'ReportStyleConfig'
] 