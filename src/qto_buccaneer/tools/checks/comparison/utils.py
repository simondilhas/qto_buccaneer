import yaml
from pathlib import Path
import pandas as pd
from typing import Dict, Any
from qto_buccaneer.utils.metadata_filter import MetadataFilter

class SafeLoader(yaml.SafeLoader):
    """Custom YAML loader that handles both scalar and sequence nodes."""
    def construct_scalar(self, node):
        if isinstance(node, yaml.SequenceNode):
            return [self.construct_scalar(child) for child in node.value]
        return super().construct_scalar(node)

def load_filter_config(filter_dir: str) -> Dict[str, Any]:
    """Load filter configuration from file or string."""
    if Path(filter_dir).exists():
        with open(filter_dir, 'r') as f:
            return yaml.load(f, Loader=SafeLoader)
    return yaml.load(filter_dir, Loader=SafeLoader)

def get_check_config(filter_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract check configuration from filter config."""
    checks = filter_config.get('checks', [])
    if not checks:
        raise ValueError("No checks configuration found in YAML file")
    return checks[0]

def calculate_differences(
    merged_df: pd.DataFrame,
    tolerance: float,
    target_area_column: str,
    actual_area_column: str,
    key_target_column: str,
    key_actual_column: str
) -> pd.DataFrame:
    """Calculate area differences and determine status based on percentage tolerance."""
    # Fill missing values
    merged_df[actual_area_column] = merged_df[actual_area_column].fillna(0.0)
    merged_df[target_area_column] = merged_df[target_area_column].fillna(0.0)

    # Compute area difference
    merged_df['area_diff'] = merged_df[actual_area_column] - merged_df[target_area_column]

    # Compute percentage difference based on target area, safely
    merged_df['area_diff_pct'] = 0.0
    mask = merged_df[target_area_column] > 0
    merged_df.loc[mask, 'area_diff_pct'] = (
        (merged_df.loc[mask, 'area_diff'].abs() / merged_df.loc[mask, target_area_column]) * 100
    )

    # Determine status
    def get_status(row, key_target_column, key_actual_column, actual_area_column, target_area_column, tolerance):
        actual_area = row.get(actual_area_column, 0.0)
        target_area = row.get(target_area_column, 0.0)
        key_target = row.get(key_target_column, None)

        # Small value threshold
        EPSILON = 0.001  # treat < 0.001 as zero

        # 1. Missing → Target exists, actual missing
        if target_area > EPSILON and actual_area < EPSILON:
            return 'missing'

        # 2. Project-specific → Target exists (LongName present), no area planned, but actual area > 0
        if pd.notna(key_target) and target_area < EPSILON and actual_area > EPSILON:
            return 'project_specific'

        # 3. Extra space → No target LongName, but actual area > 0
        if pd.isna(key_target) and actual_area > EPSILON:
            return 'extra_space'

        # 4. Within tolerance
        if target_area > EPSILON:
            lower_bound = target_area * (1 - tolerance / 100.0)
            upper_bound = target_area * (1 + tolerance / 100.0)
            if lower_bound <= actual_area <= upper_bound:
                return 'within_tolerance'

        # 5. Otherwise: Out of tolerance
        return 'out_of_tolerance'

    merged_df['status'] = merged_df.apply(
        lambda row: get_status(
            row,
            key_target_column=key_target_column,
            key_actual_column=key_actual_column,
            actual_area_column=actual_area_column,
            target_area_column=target_area_column,
            tolerance=tolerance
        ),
        axis=1
    )

    return merged_df

def apply_filter(df: pd.DataFrame, filter_str: str) -> pd.DataFrame:
    """Apply filter to DataFrame if specified."""
    if not filter_str:
        return df
    
    try:
        return MetadataFilter.filter_df_from_str(df, filter_str)
    except KeyError as e:
        raise ValueError(f"Column {e} not found in DataFrame. Cannot apply filter.") 