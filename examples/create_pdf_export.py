import pandas as pd
import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.reports import create_abstractBIM_metrics_report

# Load metrics data
metrics_df = pd.read_excel('examples/all_metrics.xlsx')

# Define project information
project_info = {
    'project_name': 'Example Project',
    'address': '123 Main St, Anytown, USA',
    'file_name': 'example_project.ifc'
}

# Generate the report
report_path = create_abstractBIM_metrics_report(
    metrics_df=metrics_df,
    project_info=project_info,
    output_dir='reports',  # Output directory for the report
    report_name='example_project_report'  # Base name for the report files
)

print(f"Report generated at: {report_path}")