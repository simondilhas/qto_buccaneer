import sys
from pathlib import Path
import pandas as pd

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.reports import export_project_comparison_excel

df = pd.read_excel("examples/all_metrics.xlsx")

metrics_to_compare = ['gross_floor_area', 'gross_volume']

comparison_df = export_project_comparison_excel(
    df=df,
    metrics=metrics_to_compare,
    output_path="examples/project_comparison.xlsx"
)

print(comparison_df)