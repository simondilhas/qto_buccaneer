import pandas as pd
import os
from pathlib import Path

def format_console_output(df: pd.DataFrame, room_results: dict) -> None:
    """Format and print the calculation results to console."""
    print("\n=== Calculation Results ===")
    print(f"File: {df['filename'].iloc[0]}")
    
    # Print each metric result
    for _, row in df.iterrows():
        print(f"\nMetric: {row['metric_name']}")
        print(f"Value: {row['value']} {row['unit']}")
        print(f"Status: {row['status']}")
        if row.get('description'):
            print(f"Description: {row['description']}")
    
    # Print room results if available
    if room_results:
        print("\n=== Room Details ===")
        for room_id, details in room_results.items():
            print(f"\nRoom {room_id}:")
            for key, value in details.items():
                print(f"  {key}: {value}")


def export_to_excel(df: pd.DataFrame, path: str) -> None:
    """Export a DataFrame to a new Excel file."""
    if not df.empty:
        df.to_excel(path, index=False)


