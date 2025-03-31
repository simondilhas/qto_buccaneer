import pandas as pd
import os
from pathlib import Path

def format_console_output(df: pd.DataFrame, details: dict) -> None:
    """Format and print calculation results to console."""
    print("\n=== Calculation Results ===")
    if df.empty:
        print("No results to display")
        return

    print(f"File: {df['file_name'].iloc[0]}\n")
    print(f"Metric: {df['metric_name'].iloc[0]}")
    print(f"Value: {df['value'].iloc[0]} {df['unit'].iloc[0]}")
    print(f"Status: {df['status'].iloc[0]}")

    if details:  # Only print room details if there are any
        print("\n=== Room Details ===")
        for room_name, value in details.items():
            print(f"\nRoom {room_name}:")
            print(f"Value: {value} {df['unit'].iloc[0]}")


def export_to_excel(df: pd.DataFrame, path: str) -> None:
    """Export a DataFrame to a new Excel file."""
    if not df.empty:
        df.to_excel(path, index=False)


