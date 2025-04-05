import pandas as pd
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import subprocess


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
