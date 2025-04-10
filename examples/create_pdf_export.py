import pandas as pd
import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.reports import generate_metrics_report

metrics_df = pd.read_excel('examples/all_metrics.xlsx')

project_info = {
    'project_name': 'Example Project',
    'address': '123 Main St, Anytown, USA',
    'file_name': 'example_project.ifc'
}

generate_metrics_report(    
    metrics_df=metrics_df,
    project_info=project_info,
    excel_path='metrics/all_metrics.xlsx',
    report_config_path='templates/abstractBIM_report_config.yaml'
)