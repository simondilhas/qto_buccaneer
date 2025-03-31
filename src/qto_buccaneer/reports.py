import pandas as pd
import os
from pathlib import Path

def format_console_output(standard_df: pd.DataFrame, room_df: pd.DataFrame) -> None:
    """
    Print formatted results to console.
    
    Args:
        standard_df: DataFrame containing standard metrics
        room_df: DataFrame containing room-based metrics
    """
    # Print file and project info
    print("\n=== Project Information ===")
    print(f"File: {standard_df['filename'].iloc[0]}")
    print(f"Project: {standard_df['project_name'].iloc[0]}")
    print(f"Project Number: {standard_df['project_number'].iloc[0]}")

    # Print standard metrics grouped by category
    print("\n=== Standard Metrics ===")
    for category in standard_df["category"].unique():
        print(f"\n{category.upper()} METRICS:")
        category_df = standard_df[standard_df["category"] == category]
        for _, row in category_df.iterrows():
            if row["status"] == "success":
                print(f"{row['metric_name']}: {row['value']} {row['unit']}")
            else:
                print(f"{row['metric_name']}: {row['status']}")

    # Print room-based metrics
    if not room_df.empty:
        print("\n=== Room-Based Metrics ===")
        for metric_name in room_df["metric_name"].unique():
            print(f"\n{metric_name}:")
            metric_rooms = room_df[room_df["metric_name"] == metric_name]
            for _, row in metric_rooms.iterrows():
                print(f"  {row['room_name']}: {row['value']} {row['unit']}")


def export_to_excel(df: pd.DataFrame, path: str) -> None:
    """Export a DataFrame to a new Excel file."""
    if not df.empty:
        df.to_excel(path, index=False)


