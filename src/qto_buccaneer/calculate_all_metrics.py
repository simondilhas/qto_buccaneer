import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict, Literal
import yaml

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qto_buccaneer.utils.ifc_loader import IfcLoader
from qto_buccaneer.utils.qto_calculator import QtoCalculator

def get_project_info(loader: IfcLoader) -> dict:
    """Get project information from IFC file."""
    project = loader.model.by_type("IfcProject")[0]
    return {
        "project_name": getattr(project, "Name", "Unknown"),
        "project_number": getattr(project, "GlobalId", "Unknown"),
        "project_phase": getattr(project, "Phase", "Unknown"),
        "project_status": getattr(project, "Status", "Unknown")
    }

def load_config(config_path: str) -> dict:
    """Load metrics configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def calculate_metric(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: dict) -> dict:
    """Calculate a single metric using configuration"""
    try:
        value = qto.calculate_quantity(
            quantity_type=metric_config["quantity_type"],
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            subtract_filter=metric_config.get("subtract_filter"),
            subtract_filter_logic=metric_config.get("subtract_filter_logic", "OR"),
            ifc_entity=metric_config["ifc_entity"],
            pset_name=metric_config["pset_name"],
            prop_name=metric_config["prop_name"]
        )
        
        return {
            **file_info,
            "metric_name": metric_name,
            "value": round(value, 2) if value is not None else None,
            "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": metric_config["quantity_type"],
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": "success"
        }
    except Exception as e:
        return {
            **file_info,
            "metric_name": metric_name,
            "value": None,
            "unit": "m³" if metric_config["quantity_type"] == "volume" else "m²",
            "category": "unknown",
            "description": metric_config.get("description", ""),
            "calculation_time": datetime.now(),
            "status": f"error: {str(e)}"
        }

def calculate_room_metric(qto: QtoCalculator, metric_name: str, metric_config: dict, file_info: dict) -> dict:
    """Calculate a single room-based metric using configuration"""
    try:
        values = qto.calculate_by_room(
            ifc_entity=metric_config["ifc_entity"],
            grouping_attribute=metric_config.get("grouping_attribute", "LongName"),
            include_filter=metric_config.get("include_filter"),
            include_filter_logic=metric_config.get("include_filter_logic", "AND"),
            pset_name=metric_config["pset_name"],
            prop_name=metric_config["prop_name"]
        )
        return {
            "values": values,
            "file_info": file_info
        }
    except Exception as e:
        print(f"Error calculating {metric_name}: {e}")
        return None

def calculate_all_metrics(ifc_path: str, config_path: str) -> Tuple[pd.DataFrame, Dict]:
    """Calculate all metrics defined in the configuration file."""
    # Load IFC and config
    loader = IfcLoader(ifc_path)
    qto = QtoCalculator(loader)
    config = load_config(config_path)

    # Get file and project info
    file_info = {
        "filename": Path(ifc_path).name,
        **get_project_info(loader)
    }

    # Calculate standard metrics
    results = [
        calculate_metric(qto, metric_name, metric_config, file_info)
        for metric_name, metric_config in config.get("metrics", {}).items()
    ]

    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Calculate room-based metrics
    room_results = {}
    for metric_name, metric_config in config.get("room_metrics", {}).items():
        result = calculate_room_metric(qto, metric_name, metric_config, file_info)
        if result:
            room_results[metric_name] = result

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
    
