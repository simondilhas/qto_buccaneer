# TODO: add checks from reports here
import pandas as pd
from qto_buccaneer.scripts.building_summary import BuildingSummary
from qto_buccaneer.utils import load_config
from qto_buccaneer.utils.metadata_filter import MetadataFilter
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
import json

class SafeLoader(yaml.SafeLoader):
    """Custom YAML loader that handles both scalar and sequence nodes."""
    def construct_scalar(self, node):
        if isinstance(node, yaml.SequenceNode):
            return [self.construct_scalar(child) for child in node.value]
        return super().construct_scalar(node)


@dataclass
class BuildingComparison:
    """Main data structure for building comparison results."""
    merged_df: pd.DataFrame
    return_values: list[str] 
    area_target_column: str
    area_actual_column: str
    
    def __post_init__(self):
        """Initialize the comparison."""
        pass
    
    def to_summary_yaml(self) -> dict:
        """Generate YAML summary of the comparison."""
        # Calculate statistics from merged DataFrame
        total_items = len(self.merged_df)
        items_within_tolerance = len(self.merged_df[self.merged_df['status'] == 'within_tolerance'])
        missing_items = len(self.merged_df[self.merged_df['status'] == 'missing'])
        extra_items = len(self.merged_df[self.merged_df['status'] == 'extra'])
        
        # Calculate total areas
        total_target_area = float(self.merged_df[self.area_target_column].sum())
        total_actual_area = float(self.merged_df[self.area_actual_column].sum())
        total_area_diff = float(total_actual_area - total_target_area)
        total_area_diff_pct = float((total_area_diff / total_target_area * 100) if total_target_area > 0 else 0)
        
        # Determine status
        if missing_items > 0:
            status = "failed"
        elif extra_items > 0:
            status = "warning"
        elif items_within_tolerance == total_items:
            status = "passed"
        else:
            status = "warning"
        
        # Get problematic items
        #problematic_df = self.merged_df[self.merged_df['status'] != 'within_tolerance']
        #problematic_items = [
        #    {
        #        "category": str(row['target_key']),
        #        "status": str(row['status']),
        #        "name": str(row.get('name_target', row.get('name_actual', ''))),
        #        "target": float(row['target_area']),
        #        "actual": float(row['actual_area']),
        #        "difference_pct": float(row['area_diff_pct'])
        #    }
        #    for _, row in problematic_df.iterrows()
        #]
        
        summary = {
            "name": "Target Program vs Actual Program",
            "status": str(status),
            "overview": {
                "total_items": int(total_items),
                "compliance_rate": float((items_within_tolerance / total_items * 100) if total_items > 0 else 0),
                "total_area": {
                    "target": float(total_target_area),
                    "actual": float(total_actual_area),
                    "difference_pct": float(total_area_diff_pct)
                }
            },
            "issues": {
                "missing": int(missing_items),
                "extra": int(extra_items),
                "out_of_tolerance": int(total_items - items_within_tolerance - missing_items - extra_items)
            },
            #"problematic_items": sorted(
            #    problematic_items,
            #    key=lambda x: abs(x["difference_pct"]),
            #    reverse=True
            #)[:10]
        }
        
        return summary
    
    def to_dict(self) -> dict:
        """Convert the comparison data to a dictionary."""
        return self.to_dataframe().to_dict(orient='records')
    
    def to_dataframe(self,) -> pd.DataFrame:
        """Return the merged DataFrame with the spcified columns."""
        return self.merged_df[self.return_values]

def _load_filter_config(filter_dir: str) -> dict:
    """Load filter configuration from file or string."""
    if Path(filter_dir).exists():
        with open(filter_dir, 'r') as f:
            return yaml.load(f, Loader=SafeLoader)
    return yaml.load(filter_dir, Loader=SafeLoader)

def _get_check_config(filter_config: dict) -> dict:
    """Extract check configuration from filter config."""
    checks = filter_config.get('checks', [])
    if not checks:
        raise ValueError("No checks configuration found in YAML file")
    return checks[0]


def _calculate_differences(
    merged_df: pd.DataFrame,
    tolerance: float,  # e.g. 10.0 for ±10%
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
        key_target_column = row.get(key_target_column, None)

        # Small value threshold
        EPSILON = 0.001  # treat < 0.001 as zero

        # 1. Missing → Target exists, actual missing
        if target_area > EPSILON and actual_area < EPSILON:
            return 'missing'

        # 2. Project-specific → Target exists (LongName present), no area planned, but actual area > 0
        if pd.notna(key_target_column) and target_area < EPSILON and actual_area > EPSILON:
            return 'project_specific'

        # 3. Extra space → No target LongName, but actual area > 0
        if pd.isna(key_target_column) and actual_area > EPSILON:
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





def _save_results(comparison: BuildingComparison, output_path: Path, building_name: str) -> None:
    """Save comparison results to files."""
    # Save YAML summary
    summary = comparison.to_summary_yaml()
    with open(output_path / f"{building_name}_summary.yaml", 'w') as f:
        yaml.dump(summary, f)
    
    # Save DataFrame
    df = comparison.to_dataframe()
    df.to_excel(output_path / f"{building_name}_comparison.xlsx", index=False)
    

def compare_target_actual(
    target_df: pd.DataFrame,
    actual_metadata_df: pd.DataFrame,
    output_dir: str,
    config_dir: str,
    building_name: str,
) -> BuildingComparison:
    """
    Compare target and actual building data.
    
    Args:
        target_df: DataFrame containing target room data
        actual_metadata_df: DataFrame containing actual room data
        output_dir: Directory to save output files
        filter_dir: Either a YAML string or a path to a YAML file containing filter configuration
        building_name: Name of the building for output files
        
    Returns:
        BuildingComparison object containing comparison results
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load and process configuration
    filter_config = _load_filter_config(config_dir)
    check_config = _get_check_config(filter_config)
    
    # Extract configuration values
    target_key = check_config['key_target_column']
    target_area_column = check_config['area_target_column']
    actual_key = check_config['key_actual_column']
    actual_area_column = check_config['area_actual_column']
    tolerance = check_config.get('tolerance', 0.1)
    return_values = check_config.get('return_values', [])
    
    filter_str = check_config.get('filter', '')
    if filter_str:
        actual_df = MetadataFilter.filter_df_from_str(actual_metadata_df, filter_str)
        
    merged_df = pd.merge(
        target_df,
        actual_df,
        how='outer',
        left_on=[target_key],
        right_on=[actual_key],
        suffixes=('_target', '_actual')
    )
    merged_df.to_excel(output_path / f"{building_name}_merged.xlsx", index=False)
    
    merged_df_1 = _calculate_differences(
        merged_df=merged_df, 
        tolerance=tolerance, 
        target_area_column=target_area_column,
        actual_area_column=actual_area_column,
        key_target_column=target_key,
        key_actual_column=actual_key
    )
    
    merged_df_1.to_excel(output_path / f"{building_name}_merged_1.xlsx", index=False)
    
    
    # Create BuildingComparison object
    comparison = BuildingComparison(merged_df, return_values=return_values, area_target_column=target_area_column, area_actual_column=actual_area_column)
    
    # Save results
    _save_results(comparison, output_path, building_name)
    
    return comparison
