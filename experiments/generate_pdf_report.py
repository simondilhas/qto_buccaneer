from jinja2 import Environment, FileSystemLoader
import subprocess
from pathlib import Path

def generate_pdf_report(project_data: dict, template_path: str = "report_template.tex", output_path: str = "output.tex") -> None:
    """Generate a PDF report from a LaTeX template using project data.
    
    Args:
        project_data (dict): Dictionary containing data to be rendered in the template
        template_path (str, optional): Path to the LaTeX template file. Defaults to "report_template.tex"
        output_path (str, optional): Path for the output tex file. Defaults to "output.tex"
    """
    # Get the directory containing the script
    script_dir = Path(__file__).parent
    
    # Set up Jinja environment with the script directory
    env = Environment(loader=FileSystemLoader(script_dir))
    
    # Just use the filename, not the full path
    template_name = Path(template_path).name
    template = env.get_template(template_name)
    rendered = template.render(**project_data)

    # Write rendered template to file
    with open(output_path, "w") as f:
        f.write(rendered)

    # Generate PDF using pdflatex
    subprocess.run(["pdflatex", output_path])

data = {
    "flaechen": [
        {"name": "Hauptnutzungsflächen", "abbr": "HNF", "soll": "2'026m²", "ist": "1'999m²", "grade": "+"},
        {"name": "Flächeneffizienz", "abbr": "HNF/GF", "soll": "> 53%", "ist": "53%", "grade": "+"},
        {"name": "Volumeneffizienz", "abbr": "GV/GF", "soll": "Ø 4.95m", "ist": "5.10m", "grade": "+"},
    ],
    "zulassung": "ja"
}

generate_pdf_report(data, "report_template.tex", "output.tex")