import pandas as pd
import os
from pathlib import Path


def export_to_excel(df: pd.DataFrame, path: str) -> None:
    """Export a DataFrame to a new Excel file."""
    if not df.empty:
        df.to_excel(path, index=False)


