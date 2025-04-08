import sys
from pathlib import Path
import pandas as pd

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.reports import room_program_comparison, ExcelLayoutConfig

# Load IFC model
ifc_loader = IfcLoader("examples/Mustermodell V1_abstractBIM_sp_enriched.ifc")

# Create custom layout config (optional)

# Create comparison
comparison_df = room_program_comparison(
    target_excel_path="examples/target_room_program.xlsx",
    ifc_loader=ifc_loader,
    room_name_column="LongName",  # Adjust these column names to match your Excel file
    target_count_column="Target Count",
    target_area_column="Target Area/Room",
    output_path="examples/room_program_comparison.xlsx")


print(comparison_df)