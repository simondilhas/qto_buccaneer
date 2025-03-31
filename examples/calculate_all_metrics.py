import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.metrics import calculate_all_metrics
from qto_buccaneer.reports import format_console_output, export_to_excel

def main():
    # Example usage
    ifc_path = "examples/Mustermodell V1_abstractBIM.ifc"
    config_path = "src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml"
    
    df, room_results = calculate_all_metrics(ifc_path, config_path)
    
    # Print formatted results
    format_console_output(df, room_results)
    print(df)

    # Export to Excel
    export_to_excel(df, "metrics.xlsx")
    #export_to_excel(room_results, "room_metrics.xlsx")

if __name__ == "__main__":
    main() 