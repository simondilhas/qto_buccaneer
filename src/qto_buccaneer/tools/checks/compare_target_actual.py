"""
Module for comparing target and actual building data.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
import pandas as pd
import yaml
import logging
from qto_buccaneer.utils.result_bundle import ResultBundle
from qto_buccaneer.utils.metadata_filter import MetadataFilter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
EPSILON = 0.001  # Small value threshold for area comparisons

class SafeLoader(yaml.SafeLoader):
    """Custom YAML loader that handles both scalar and sequence nodes."""
    def construct_scalar(self, node):
        if isinstance(node, yaml.SequenceNode):
            return [self.construct_scalar(child) for child in node.value]
        return super().construct_scalar(node)

@dataclass
class ComparisonResult:
    """Main data structure for comparison results."""
    merged_df: pd.DataFrame
    return_values: List[str]
    area_target_column: Optional[str] = None
    area_actual_column: Optional[str] = None
    comparison_type: str = "area"  # "area" or "name"
    
    def to_result_bundle(self) -> ResultBundle:
        """Convert the comparison to a ResultBundle."""
        if self.comparison_type == "name":
            return self._create_name_comparison_bundle()
        return self._create_area_comparison_bundle()
    
    def _create_name_comparison_bundle(self) -> ResultBundle:
        """Create a ResultBundle for room name comparison."""
        actual_name_col = self._find_name_column('_actual')
        target_name_col = self._find_name_column('_target')
        
        ifc_rooms = set(self.merged_df[self.merged_df['status'] != 'missing'][actual_name_col].dropna().str.lower().unique())
        excel_rooms = set(self.merged_df[self.merged_df['status'] != 'extra'][target_name_col].dropna().str.lower().unique())
        
        rooms_only_in_ifc = list(ifc_rooms - excel_rooms)
        rooms_only_in_excel = list(excel_rooms - ifc_rooms)
        
        status = self._determine_name_comparison_status(rooms_only_in_excel, rooms_only_in_ifc)
        
        summary_data = {
            "room_comparison": {
                "status": status,
                "summary": {
                    "target_rooms": len(excel_rooms),
                    "actual_rooms": len(ifc_rooms),
                    "additional_rooms": len(rooms_only_in_ifc),
                    "missing_rooms": len(rooms_only_in_excel)
                },
                "additional_rooms": sorted(rooms_only_in_ifc),
                "missing_rooms": sorted(rooms_only_in_excel)
            }
        }
        
        return ResultBundle(dataframe=self.merged_df[self.return_values], json=summary_data)
    
    def _create_area_comparison_bundle(self) -> ResultBundle:
        """Create a ResultBundle for area comparison."""
        stats = self._calculate_area_statistics()
        
        summary_data = {
            "name": "Target Program vs Actual Program",
            "status": str(stats['status']),
            "overview": {
                "total_items": int(stats['total_items']),
                "compliance_rate": float(stats['compliance_rate']),
                "total_area": {
                    "target": float(stats['total_target_area']),
                    "actual": float(stats['total_actual_area']),
                    "difference_pct": float(stats['total_area_diff_pct'])
                }
            },
            "issues": {
                "missing": int(stats['missing_items']),
                "extra": int(stats['extra_items']),
                "out_of_tolerance": int(stats['out_of_tolerance_items'])
            }
        }
        
        return ResultBundle(dataframe=self.merged_df[self.return_values], json=summary_data)
    
    def _find_name_column(self, suffix: str) -> str:
        """Find the name column with the given suffix."""
        col = next(
            (col for col in self.merged_df.columns 
             if col.endswith(suffix) and ('name' in col.lower() or 'longname' in col.lower())),
            None
        )
        if col is None:
            raise ValueError(f"No name column found with suffix {suffix}")
        return col
    
    def _determine_name_comparison_status(self, missing_rooms: List[str], extra_rooms: List[str]) -> str:
        """Determine the status of a name comparison."""
        if not missing_rooms:
            return "success"
        if extra_rooms:
            return "additional roomtypes used"
        return "error"
    
    def _calculate_area_statistics(self) -> Dict[str, float]:
        """Calculate statistics for area comparison."""
        total_items = len(self.merged_df)
        items_within_tolerance = len(self.merged_df[self.merged_df['status'] == 'within_tolerance'])
        missing_items = len(self.merged_df[self.merged_df['status'] == 'missing'])
        extra_items = len(self.merged_df[self.merged_df['status'] == 'extra'])
        
        total_target_area = float(self.merged_df[self.area_target_column].sum())
        total_actual_area = float(self.merged_df[self.area_actual_column].sum())
        total_area_diff = float(total_actual_area - total_target_area)
        total_area_diff_pct = float((total_area_diff / total_target_area * 100) if total_target_area > 0 else 0)
        
        status = self._determine_area_comparison_status(missing_items, extra_items, items_within_tolerance, total_items)
        
        return {
            'total_items': total_items,
            'items_within_tolerance': items_within_tolerance,
            'missing_items': missing_items,
            'extra_items': extra_items,
            'total_target_area': total_target_area,
            'total_actual_area': total_actual_area,
            'total_area_diff': total_area_diff,
            'total_area_diff_pct': total_area_diff_pct,
            'status': status,
            'compliance_rate': float((items_within_tolerance / total_items * 100) if total_items > 0 else 0),
            'out_of_tolerance_items': total_items - items_within_tolerance - missing_items - extra_items
        }
    
    def _determine_area_comparison_status(self, missing_items: int, extra_items: int, 
                                        items_within_tolerance: int, total_items: int) -> str:
        """Determine the status of an area comparison."""
        if missing_items > 0:
            return "failed"
        if extra_items > 0:
            return "warning"
        if items_within_tolerance == total_items:
            return "passed"
        return "warning"

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
    def get_status(row):
        actual_area = row.get(actual_area_column, 0.0)
        target_area = row.get(target_area_column, 0.0)
        key_target = row.get(key_target_column, None)

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

    merged_df['status'] = merged_df.apply(get_status, axis=1)
    return merged_df

def apply_filter(df: pd.DataFrame, filter_str: str) -> pd.DataFrame:
    """Apply filter to DataFrame if specified."""
    if not filter_str:
        return df
    
    try:
        return MetadataFilter.filter_df_from_str(df, filter_str)
    except KeyError as e:
        raise ValueError(f"Column {e} not found in DataFrame. Cannot apply filter.")

def handle_duplicate_global_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle duplicate Global IDs by aggregating their data.
    
    Args:
        df: DataFrame containing the data with potential duplicate Global IDs
        
    Returns:
        DataFrame with aggregated data for duplicate Global IDs
    """
    if 'GlobalId' not in df.columns:
        return df
        
    # Find duplicates
    duplicate_global_ids = df[df.duplicated(subset=['GlobalId'], keep=False)]
    if duplicate_global_ids.empty:
        return df
        
    logger.warning(f"Found {len(duplicate_global_ids)} rows with duplicate GlobalIds")
    
    # Define columns to aggregate
    numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
    string_columns = df.select_dtypes(include=['object']).columns
    
    # Group by GlobalId and aggregate
    aggregation_dict = {
        col: 'sum' if col in numeric_columns else 'first' 
        for col in df.columns if col != 'GlobalId'
    }
    
    # Perform the aggregation
    df = df.groupby('GlobalId', as_index=False).agg(aggregation_dict)
    
    logger.info(f"Aggregated data for {len(duplicate_global_ids['GlobalId'].unique())} duplicate GlobalIds")
    return df

def compare_target_actual(
    actual_df: pd.DataFrame,
    target_df: pd.DataFrame,
    config_path: Union[str, Path],
    output_dir: str,
    rule_name: str,
    building_name: str,
) -> ResultBundle:
    """
    Compare target and actual building data.
    
    Args:
        actual_df: DataFrame containing actual IFC data
        target_df: DataFrame containing target room program
        config_path: Path to the config file (string or Path object)
        output_dir: Directory to save output files
        rule_name: Name of the rule to use from the config file
        building_name: Name of the building for output files
        
    Returns:
        ResultBundle containing comparison results
    """
    # Convert config_path to Path object if it's a string
    config_path = Path(config_path) if isinstance(config_path, str) else config_path
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load and process configuration
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Find the matching rule
    check_config = None
    for check in config.get('checks', []):
        if isinstance(check, dict):
            # Check if this is the room name comparison rule
            if rule_name == 'room_name_comparison' and not check.get('area_target_column') and not check.get('area_actual_column'):
                check_config = check
                break
            # Check if this is the room name and area comparison rule
            elif rule_name == 'room_name_and_area_comparison' and check.get('area_target_column') and check.get('area_actual_column'):
                check_config = check
                break
            
    if not check_config:
        available_rules = []
        for check in config.get('checks', []):
            if isinstance(check, dict):
                if check.get('area_target_column') and check.get('area_actual_column'):
                    available_rules.append('room_name_and_area_comparison')
                else:
                    available_rules.append('room_name_comparison')
        raise ValueError(f"Rule '{rule_name}' not found in config file. Available rules: {list(set(available_rules))}")
    
    # Extract configuration values
    target_key = check_config['key_target_column']
    target_area_column = check_config.get('area_target_column')
    actual_key = check_config['key_actual_column']
    actual_area_column = check_config.get('area_actual_column')
    tolerance = check_config.get('tolerance', 0.1)
    
    # Determine comparison type
    comparison_type = "name" if not (target_area_column and actual_area_column) else "area"
    
    # Combine return values from both target and actual
    return_values = []
    if 'return_values_target' in check_config:
        return_values.extend([f"{col}_target" for col in check_config['return_values_target']])
    if 'return_values_actual' in check_config:
        return_values.extend([f"{col}_actual" for col in check_config['return_values_actual']])
    
    # Add calculated columns to return values
    calculated_columns = ['status']  # Always include status
    if comparison_type == "area":
        calculated_columns.extend(['area_diff', 'area_diff_pct'])
    return_values.extend(calculated_columns)
    
    # Apply filter if specified
    filter_str = check_config.get('filter', '')
    if filter_str:
        actual_df = apply_filter(actual_df, filter_str)

    # Rename columns to avoid conflicts
    actual_df = actual_df.copy()
    actual_df.columns = [f"{col}_actual" for col in actual_df.columns]
    target_df = target_df.copy()
    target_df.columns = [f"{col}_target" for col in target_df.columns]
    
    # Log the merge keys for debugging
    logger.info(f"Merge keys - Target: {target_key}_target, Actual: {actual_key}_actual")
    
    # Check for duplicates in the merge keys before merging
    if target_df[f"{target_key}_target"].duplicated().any():
        logger.warning(f"Found {target_df[f'{target_key}_target'].duplicated().sum()} duplicate values in target key")
        # Keep only the first occurrence of each target key
        target_df = target_df.drop_duplicates(subset=[f"{target_key}_target"], keep='first')
    
    if actual_df[f"{actual_key}_actual"].duplicated().any():
        logger.warning(f"Found {actual_df[f'{actual_key}_actual'].duplicated().sum()} duplicate values in actual key")
        # Keep only the first occurrence of each actual key
        actual_df = actual_df.drop_duplicates(subset=[f"{actual_key}_actual"], keep='first')
    
    # Merge dataframes
    try:
        # First try a left join to match target with actual
        merged_df = pd.merge(
            target_df,
            actual_df,
            how='left',
            left_on=[f"{target_key}_target"],
            right_on=[f"{actual_key}_actual"],
        )
        
        # Then find any actual items that weren't matched (extra items)
        extra_items = actual_df[~actual_df[f"{actual_key}_actual"].isin(merged_df[f"{actual_key}_actual"])]
        if not extra_items.empty:
            # Create a new DataFrame for extra items with NaN for target columns
            extra_df = pd.DataFrame(columns=merged_df.columns)
            for col in actual_df.columns:
                extra_df[col] = extra_items[col]
            # Append extra items to the merged DataFrame
            merged_df = pd.concat([merged_df, extra_df], ignore_index=True)
            
    except KeyError as e:
        raise ValueError(f"Error during merge: {e}. Available columns in target_df: {target_df.columns.tolist()}, actual_df: {actual_df.columns.tolist()}")
    
    # Calculate differences if it's an area comparison
    if comparison_type == "area":
        merged_df = calculate_differences(
            merged_df=merged_df, 
            tolerance=tolerance, 
            target_area_column=f"{target_area_column}_target",
            actual_area_column=f"{actual_area_column}_actual",
            key_target_column=f"{target_key}_target",
            key_actual_column=f"{actual_key}_actual"
        )
    else:
        # For name comparison, set status based on presence in target and actual
        merged_df['status'] = merged_df.apply(
            lambda row: 'missing' if pd.isna(row[f'{actual_key}_actual']) else 
                       'extra' if pd.isna(row[f'{target_key}_target']) else 
                       'match',
            axis=1
        )
    
    # Calculate summary statistics directly
    total_items = len(merged_df)
    items_within_tolerance = len(merged_df[merged_df['status'] == 'within_tolerance'])
    missing_items = len(merged_df[merged_df['status'] == 'missing'])
    extra_items = len(merged_df[merged_df['status'] == 'extra'])
    out_of_tolerance_items = total_items - items_within_tolerance - missing_items - extra_items
    
    if comparison_type == "area":
        total_target_area = float(merged_df[f"{target_area_column}_target"].sum())
        total_actual_area = float(merged_df[f"{actual_area_column}_actual"].sum())
        total_area_diff = float(total_actual_area - total_target_area)
        total_area_diff_pct = float((total_area_diff / total_target_area * 100) if total_target_area > 0 else 0)
        compliance_rate = float((items_within_tolerance / total_items * 100) if total_items > 0 else 0)
        status = "failed" if missing_items > 0 else "warning" if extra_items > 0 else "passed" if items_within_tolerance == total_items else "warning"
    else:
        # For name comparison
        total_target_area = 0.0
        total_actual_area = 0.0
        total_area_diff = 0.0
        total_area_diff_pct = 0.0
        compliance_rate = float((items_within_tolerance / total_items * 100) if total_items > 0 else 0)
        status = "success" if missing_items == 0 else "additional roomtypes used" if extra_items > 0 else "error"
    
    # Create summary dictionary with calculated values
    summary = {
        "checks": [
            {
                "name": "Target Program vs Actual Program",
                "status": status,
                "overview": {
                    "total_items": total_items,
                    "compliance_rate": compliance_rate,
                    "total_area": {
                        "target": total_target_area,
                        "actual": total_actual_area,
                        "difference_pct": total_area_diff_pct
                    }
                },
                "issues": {
                    "missing": missing_items,
                    "extra": extra_items,
                    "out_of_tolerance": out_of_tolerance_items
                }
            }
        ]
    }
    
    # Create ComparisonResult object
    comparison = ComparisonResult(
        merged_df=merged_df,
        return_values=return_values,
        area_target_column=f"{target_area_column}_target" if target_area_column else None,
        area_actual_column=f"{actual_area_column}_actual" if actual_area_column else None,
        comparison_type=comparison_type
    )
    
    # Get ResultBundle
    result_bundle = comparison.to_result_bundle()
    
    # Save results
    building_prefix = f"{building_name}_" if building_name else ""
    
    # Save Excel file
    result_bundle.save_excel(output_path / f"{building_prefix}comparison.xlsx")
    
    # Update the result bundle with the new summary and folderpath
    result_bundle.summary = summary
    result_bundle.folderpath = output_path
    
    return result_bundle


