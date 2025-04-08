import pandas as pd
import os
from pathlib import Path
from typing import Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader
import subprocess
from dataclasses import dataclass
import openpyxl
from openpyxl.utils import get_column_letter


def export_to_excel(df: pd.DataFrame, path: str) -> None:
    """Export a DataFrame to a new Excel file."""
    if not df.empty:
        df.to_excel(path, index=False)


def generate_pdf_report(
    project_data: dict, 
    template_path: str = "template.tex", 
    output_path: str = "output.tex") -> None:
    
    """Generate a PDF report from a LaTeX template using project data.
    
    Args:
        project_data (dict): Dictionary containing data to be rendered in the template
        template_path (str, optional): Path to the LaTeX template file. Defaults to "template.tex"
        output_path (str, optional): Path for the output tex file. Defaults to "output.tex"
    """
    # Get the directory containing the template
    template_dir = str(Path(template_path).parent)
    template_name = Path(template_path).name
    
    # Set up Jinja environment with the correct directory
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    rendered = template.render(**project_data)

    # Write rendered template to file
    with open(output_path, "w") as f:
        f.write(rendered)

    # Generate PDF using pdflatex
    subprocess.run(["pdflatex", output_path])

def create_project_comparison_df(df: pd.DataFrame, metrics: Optional[list[str]] = None) -> pd.DataFrame:
    """
    Create a comparison DataFrame with projects as rows and metrics as columns.

    Args:
        df (pd.DataFrame): Input DataFrame containing metrics data
        metrics (Optional[list[str]]): List of metric names to include in the comparison.
            If None, all metrics will be included.

    Returns:
        pd.DataFrame: DataFrame with projects as rows and metrics as columns
    """
    try:
        # Filter metrics if a list is provided
        if metrics is not None:
            df = df[df['metric_name'].isin(metrics)].copy()
            
            if df.empty:
                return pd.DataFrame()
        
        # Create a copy to avoid modifying the original DataFrame
        df = df.copy()
        
        # Clean up project names by removing the suffix
        df['file_name'] = df['file_name'].str.replace('_abstractBIM_sp_enriched.ifc', '')
        
        # Create metric names with units
        df['metric_with_unit'] = df['metric_name'] + ' [' + df['unit'] + ']'
        
        pivot_df = df.pivot(
            index='file_name',
            columns='metric_with_unit',
            values='value'
        )
        
        # Only sort if no specific metrics order was provided
        if metrics is None:
            pivot_df = pivot_df.sort_index(axis=1)
        else:
            # Reorder columns based on the provided metrics order
            metric_order = [m + ' [' + df[df['metric_name'] == m]['unit'].iloc[0] + ']' for m in metrics]
            pivot_df = pivot_df[metric_order]
            
        pivot_df = pivot_df.reset_index()
        pivot_df = pivot_df.rename(columns={'file_name': 'Project'})
        
        return pivot_df
        
    except Exception as e:
        return pd.DataFrame()

@dataclass
class ExcelLayoutConfig:
    """Configuration for Excel export layout."""
    horizontal_lines: bool = True
    vertical_lines: bool = False
    bold_headers: bool = True
    auto_column_width: bool = True
    row_height: Optional[float] = None
    alternating_colors: bool = False
    number_format: str = '#,##0.00'
    header_color: str = 'E0E0E0'  # Light gray
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {k: v for k, v in self.__dict__.items()}

def export_project_comparison_excel(
    df: pd.DataFrame, 
    output_path: str, 
    metrics: Optional[list[str]] = None,
    layout_config: Optional[ExcelLayoutConfig] = None
) -> None:
    """
    Create and export project comparison to Excel file with customizable formatting.

    Args:
        df (pd.DataFrame): Input DataFrame containing metrics data
        output_path (str): Path where the Excel file should be saved
        metrics (Optional[list[str]]): List of metric names to include in the comparison
        layout_config (Optional[ExcelLayoutConfig]): Configuration for Excel layout.
            If None, default settings will be used.
    """
    comparison_df = create_project_comparison_df(df, metrics)
    
    if comparison_df.empty:
        return
        
    config = layout_config or ExcelLayoutConfig()
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        comparison_df.to_excel(writer, index=False, sheet_name='Comparison')
        worksheet = writer.sheets['Comparison']
        
        # Auto-adjust column widths if enabled
        if config.auto_column_width:
            for idx, col in enumerate(comparison_df.columns):
                max_length = max(
                    comparison_df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                adjusted_width = max_length + 2
                column_letter = get_column_letter(idx + 1)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Set row height if specified
        if config.row_height:
            for row in range(1, len(comparison_df) + 2):
                worksheet.row_dimensions[row].height = config.row_height
        
        # Add gridlines
        for row in range(1, len(comparison_df) + 2):
            for col in range(1, len(comparison_df.columns) + 1):
                cell = worksheet.cell(row=row, column=col)
                borders = {}
                
                if config.horizontal_lines:
                    borders['bottom'] = openpyxl.styles.Side(style='thin')
                if config.vertical_lines:
                    borders['right'] = openpyxl.styles.Side(style='thin')
                
                if borders:
                    cell.border = openpyxl.styles.Border(**borders)
                
                # Apply number format to numeric cells
                if row > 1 and col > 1:  # Skip header row and project column
                    try:
                        float(cell.value)  # Check if value is numeric
                        cell.number_format = config.number_format
                    except (TypeError, ValueError):
                        pass
        
        # Format headers
        if config.bold_headers:
            for col in range(1, len(comparison_df.columns) + 1):
                cell = worksheet.cell(row=1, column=col)
                cell.font = openpyxl.styles.Font(bold=True)
                
                if config.header_color:
                    cell.fill = openpyxl.styles.PatternFill(
                        start_color=config.header_color,
                        end_color=config.header_color,
                        fill_type='solid'
                    )
        
        # Apply alternating colors if enabled
        if config.alternating_colors:
            for row in range(2, len(comparison_df) + 2, 2):  # Start after header
                for col in range(1, len(comparison_df.columns) + 1):
                    cell = worksheet.cell(row=row, column=col)
                    cell.fill = openpyxl.styles.PatternFill(
                        start_color='F5F5F5',  # Light gray
                        end_color='F5F5F5',
                        fill_type='solid'
                    )

# Example usage:
"""
# Use default settings
export_project_comparison_excel(df, 'comparison.xlsx')

# Custom layout
config = ExcelLayoutConfig(
    horizontal_lines=True,
    vertical_lines=True,
    bold_headers=True,
    auto_column_width=True,
    row_height=20,
    alternating_colors=True,
    number_format='#,##0.00',
    header_color='E0E0E0'
)
export_project_comparison_excel(df, 'comparison.xlsx', layout_config=config)

# Minimal layout
minimal_config = ExcelLayoutConfig(
    horizontal_lines=False,
    vertical_lines=False,
    bold_headers=True,
    auto_column_width=True
)
export_project_comparison_excel(df, 'comparison.xlsx', layout_config=minimal_config)
""" 