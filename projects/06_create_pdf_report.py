import sys
from pathlib import Path
import pandas as pd

# Add src directory to path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.reports import create_abstractBIM_metrics_report
from scripts.project_utils import load_project_data, get_project_path

def main():
    # Get project directory
    project_dir = Path(__file__).parent
    
    # Load project data
    project_data = load_project_data(project_dir)
    
    # Get metrics data
    metrics_file = get_project_path(project_dir, "output/03_quantities") / f"{project_data['settings']['ifc_file'].replace('.ifc', '_metrics.xlsx')}"
    metrics_df = pd.read_excel(metrics_file)
    
    # Generate the report
    report_path = create_abstractBIM_metrics_report(
        metrics_df=metrics_df,
        project_info={
            'project_name': project_data['metadata']['name'],
            'address': project_data['settings']['address'],
            'file_name': project_data['settings']['ifc_file']
        },
        output_dir=str(get_project_path(project_dir, "output/06_reports")),
        report_name=f"{project_data['metadata']['name']}_report"
    )
    
    print(f"Report generated at: {report_path}")

def run_workflow(project_name, config):
    # For each step in workflow
    for step in config['workflow']['steps']:
        # Run the appropriate script
        # Pass project-specific info and step config
        pass

if __name__ == "__main__":
    main()
