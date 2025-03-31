import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator

def get_project_info(loader: IfcLoader) -> dict:
    """
    Get project information from IFC file.
    
    Args:
        loader: IfcLoader instance
        
    Returns:
        dict: Project information including name, number, phase etc.
    """
    project = loader.model.by_type("IfcProject")[0]
    return {
        "project_name": getattr(project, "Name", "Unknown"),
        "project_number": getattr(project, "GlobalId", "Unknown"),
        "project_phase": getattr(project, "Phase", "Unknown"),
        "project_status": getattr(project, "Status", "Unknown")
    }

def calculate_all_metrics(ifc_path: str, config_path: Optional[str] = None) -> Tuple[pd.DataFrame, Dict]:
    """
    Calculate all metrics defined in the configuration file.
    
    Args:
        ifc_path: Path to the IFC file
        config_path: Optional path to custom config file (currently not used)
    
    Returns:
        tuple[pd.DataFrame, dict]: DataFrame with standard metrics and dict with room metrics
    """
    # Load IFC
    loader = IfcLoader(ifc_path)
    
    # Initialize calculator with loader
    qto = QtoCalculator(loader)

    # Get file and project info
    file_info = {
        "filename": Path(ifc_path).name,
        **get_project_info(loader)
    }

    # Prepare data for DataFrame
    results = []
    
    # Define standard metrics to calculate
    metrics = {
        "gross_floor_area": {
            "method": qto.calculate_gross_floor_area,
            "quantity_type": "area",
            "description": "Gross floor area"
        },
        "interior_floor_area": {
            "method": qto.calculate_space_interior_floor_area,
            "quantity_type": "area",
            "description": "Interior floor area"
        },
        "exterior_wall_area": {
            "method": qto.calculate_walls_exterior_net_side_area,
            "quantity_type": "area",
            "description": "Exterior wall area"
        },
        # Add more metrics as needed
    }
    
    # Calculate standard metrics
    for metric_name, metric_config in metrics.items():
        try:
            value = metric_config["method"]()
            
            results.append({
                **file_info,  # Include file and project info
                "metric_name": metric_name,
                "value": round(value, 2) if value is not None else None,
                "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
                "category": metric_config["quantity_type"],
                "description": metric_config["description"],
                "calculation_time": datetime.now(),
                "status": "success"
            })
        except Exception as e:
            results.append({
                **file_info,  # Include file and project info
                "metric_name": metric_name,
                "value": None,
                "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
                "category": "unknown",
                "description": metric_config["description"],
                "calculation_time": datetime.now(),
                "status": f"error: {str(e)}"
            })

    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Calculate room-based metrics
    room_metrics = {
        "windows_by_room": qto.create_windows_by_room,
        "doors_by_room": qto.create_doors_by_room,
        "wall_coverings_by_room": qto.create_wall_coverings_by_room
    }
    
    room_results = {}
    for metric_name, method in room_metrics.items():
        try:
            values = method()
            room_results[metric_name] = {
                "values": values,
                "file_info": file_info
            }
        except Exception as e:
            print(f"Error calculating {metric_name}: {e}")

    return df, room_results

def format_results(df: pd.DataFrame, room_results: dict) -> None:
    """Print formatted results to console"""
    # Print file and project info
    print("\n=== Project Information ===")
    print(f"File: {df['filename'].iloc[0]}")
    print(f"Project: {df['project_name'].iloc[0]}")
    print(f"Project Number: {df['project_number'].iloc[0]}")

    # Print standard metrics grouped by category
    print("\n=== Standard Metrics ===")
    for category in df["category"].unique():
        print(f"\n{category.upper()} METRICS:")
        category_df = df[df["category"] == category]
        for _, row in category_df.iterrows():
            if row["status"] == "success":
                print(f"{row['metric_name']}: {row['value']} {row['unit']}")
            else:
                print(f"{row['metric_name']}: {row['status']}")

    # Print room-based metrics
    if room_results:
        print("\n=== Room-Based Metrics ===")
        for metric_name, data in room_results.items():
            print(f"\n{metric_name}:")
            for room, area in data["values"].items():
                print(f"  {room}: {area:.2f} m²")

def export_to_excel(df: pd.DataFrame, room_results: dict, output_path: str = "qto_results.xlsx"):
    """Export results to Excel with multiple sheets"""
    with pd.ExcelWriter(output_path) as writer:
        # Export standard metrics
        df.to_excel(writer, sheet_name="Standard Metrics", index=False)
        
        # Export room-based metrics
        for metric_name, data in room_results.items():
            room_df = pd.DataFrame.from_dict(data["values"], 
                                           orient='index', 
                                           columns=['Area'])
            # Add file info columns
            for key, value in data["file_info"].items():
                room_df[key] = value
            
            room_df.to_excel(writer, sheet_name=metric_name)

if __name__ == "__main__":
    # Example usage
    ifc_path = "examples/Mustermodell V1_abstractBIM.ifc"
    config_path = "src/qto_buccaneer/metrics_config.yaml"
    
    df, room_results = calculate_all_metrics(ifc_path, config_path)
    
    # Print formatted results
    format_results(df, room_results)
    print(df)

    # Export to Excel
    export_to_excel(df, room_results)
    
