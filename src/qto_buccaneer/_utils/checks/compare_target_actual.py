"""
Module for comparing target and actual building data.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
import pandas as pd
import yaml
import logging
from qto_buccaneer._utils._result_bundle import BaseResultBundle
from qto_buccaneer._utils._general_tool_utils import unpack_dataframe, validate_df, validate_config
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
    numerical_target_column: Optional[str] = None
    numerical_actual_column: Optional[str] = None
    comparison_type: str = "name"  # "name" or "numerical"
    
    def to_result_bundle(self) -> BaseResultBundle:
        """Convert the comparison to a BaseResultBundle."""
        if self.comparison_type == "name":
            return self._create_name_comparison_bundle()
        return self._create_numerical_comparison_bundle()
    
    def _create_name_comparison_bundle(self) -> BaseResultBundle:
        """Create a BaseResultBundle for room name comparison."""
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
        
        return BaseResultBundle(dataframe=self.merged_df[self.return_values], json=summary_data)
    
    def _create_numerical_comparison_bundle(self) -> BaseResultBundle:
        """Create a BaseResultBundle for numerical comparison."""
        # Check if required columns exist
        missing_columns = []
        if self.numerical_target_column and self.numerical_target_column not in self.merged_df.columns:
            missing_columns.append(self.numerical_target_column)
        if self.numerical_actual_column and self.numerical_actual_column not in self.merged_df.columns:
            missing_columns.append(self.numerical_actual_column)
        
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            logger.info(f"Available columns: {self.merged_df.columns.tolist()}")
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        stats = self._calculate_numerical_statistics()
        
        summary_data = {
            "name": "Target Program vs Actual Program",
            "status": str(stats['status']),
            "overview": {
                "total_items": int(stats['total_items']),
                "compliance_rate": float(stats['compliance_rate']),
                "total_values": {
                    "target": float(stats['total_target_value']),
                    "actual": float(stats['total_actual_value']),
                    "difference_pct": float(stats['total_diff_pct'])
                }
            },
            "issues": {
                "missing": int(stats['missing_items']),
                "extra": int(stats['extra_items']),
                "out_of_tolerance": int(stats['out_of_tolerance_items'])
            }
        }
        
        # Filter return values to only include columns that exist
        valid_return_values = [col for col in self.return_values if col in self.merged_df.columns]
        if valid_return_values != self.return_values:
            logger.warning(f"Some return values not found in DataFrame: {set(self.return_values) - set(valid_return_values)}")
        
        return BaseResultBundle(dataframe=self.merged_df[valid_return_values], json=summary_data)
    
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
    
    def _calculate_numerical_statistics(self) -> Dict[str, float]:
        """Calculate statistics for numerical comparison."""
        total_items = len(self.merged_df)
        items_within_tolerance = len(self.merged_df[self.merged_df['status'] == 'within_tolerance'])
        missing_items = len(self.merged_df[self.merged_df['status'] == 'missing'])
        extra_items = len(self.merged_df[self.merged_df['status'] == 'extra'])
        
        total_target_value = float(self.merged_df[self.numerical_target_column].sum())
        total_actual_value = float(self.merged_df[self.numerical_actual_column].sum())
        total_diff = float(total_actual_value - total_target_value)
        total_diff_pct = float((total_diff / total_target_value * 100) if total_target_value > 0 else 0)
        
        status = self._determine_numerical_comparison_status(missing_items, extra_items, items_within_tolerance, total_items)
        
        return {
            'total_items': total_items,
            'items_within_tolerance': items_within_tolerance,
            'missing_items': missing_items,
            'extra_items': extra_items,
            'total_target_value': total_target_value,
            'total_actual_value': total_actual_value,
            'total_diff': total_diff,
            'total_diff_pct': total_diff_pct,
            'status': status,
            'compliance_rate': float((items_within_tolerance / total_items * 100) if total_items > 0 else 0),
            'out_of_tolerance_items': total_items - items_within_tolerance - missing_items - extra_items
        }
    
    def _determine_numerical_comparison_status(self, missing_items: int, extra_items: int, 
                                        items_within_tolerance: int, total_items: int) -> str:
        """Determine the status of a numerical comparison."""
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
    """Calculate numerical differences and determine status based on percentage tolerance."""
    # Fill missing values
    merged_df[actual_area_column] = merged_df[actual_area_column].fillna(0.0)
    merged_df[target_area_column] = merged_df[target_area_column].fillna(0.0)

    # Compute difference
    merged_df['diff'] = merged_df[actual_area_column] - merged_df[target_area_column]

    # Compute percentage difference based on target value, safely
    merged_df['diff_pct'] = 0.0
    mask = merged_df[target_area_column] > 0
    merged_df.loc[mask, 'diff_pct'] = (
        (merged_df.loc[mask, 'diff'].abs() / merged_df.loc[mask, target_area_column]) * 100
    )

    # Determine status
    def get_status(row):
        actual_value = row.get(actual_area_column, 0.0)
        target_value = row.get(target_area_column, 0.0)
        key_target = row.get(key_target_column, None)

        # 1. Missing → Target exists, actual missing
        if target_value > EPSILON and actual_value < EPSILON:
            return 'missing'

        # 2. Project-specific → Target exists (LongName present), no value planned, but actual value > 0
        if pd.notna(key_target) and target_value < EPSILON and actual_value > EPSILON:
            return 'project_specific'

        # 3. Extra space → No target LongName, but actual value > 0
        if pd.isna(key_target) and actual_value > EPSILON:
            return 'extra_space'

        # 4. Within tolerance
        if target_value > EPSILON:
            lower_bound = target_value * (1 - tolerance / 100.0)
            upper_bound = target_value * (1 + tolerance / 100.0)
            if lower_bound <= actual_value <= upper_bound:
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

def process_compare_target_actual_logic(
    target_df: pd.DataFrame,
    actual_df: pd.DataFrame,
    config: Dict[str, Any]
) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """Core data processing logic for the tool"""
    try:
        # Get configuration from the config
        # The config is nested under 'config' key
        check_config = config.get('config', {})
        if not check_config:
            raise ValueError("No 'config' section found in the check configuration")
            
        target_key = check_config['keys']['target']
        actual_key = check_config['keys']['actual']
        filter_str = check_config.get('filter', '')
        
        # Log available columns for debugging
        logger.info(f"Target DataFrame columns: {target_df.columns.tolist()}")
        logger.info(f"Actual DataFrame columns: {actual_df.columns.tolist()}")
        logger.info(f"Looking for target key: {target_key}")
        logger.info(f"Looking for actual key: {actual_key}")
        
        # Verify column existence before proceeding
        if target_key not in target_df.columns:
            raise ValueError(f"Target key '{target_key}' not found in target DataFrame. Available columns: {target_df.columns.tolist()}")
        if actual_key not in actual_df.columns:
            raise ValueError(f"Actual key '{actual_key}' not found in actual DataFrame. Available columns: {actual_df.columns.tolist()}")
        
        # Get return values from the config
        return_values = []
        if 'return_values' in check_config:
            if 'target' in check_config['return_values']:
                return_values.extend([f"{col}_target" for col in check_config['return_values']['target']])
            if 'actual' in check_config['return_values']:
                # Map 'guid' to 'GlobalId' in return values if needed
                actual_return_values = []
                for col in check_config['return_values']['actual']:
                    if col == 'guid':
                        actual_return_values.append('GlobalId')
                    else:
                        actual_return_values.append(col)
                return_values.extend([f"{col}_actual" for col in actual_return_values])
        
        # Add calculated columns to return values
        calculated_columns = ['status']  # Always include status
        return_values.extend(calculated_columns)
        
        # Apply filter if specified
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
        
        # Calculate differences if numerical comparison columns are provided
        if 'numerical_comparison' in check_config:
            numerical_config = check_config['numerical_comparison']
            tolerance = numerical_config.get('tolerance', 5.0)  # Default tolerance of 5%
            
            # Add _actual and _target suffixes to the column names
            target_column = f"{numerical_config['target']}_target"
            actual_column = f"{numerical_config['actual']}_actual"
            
            # Verify the columns exist after renaming
            if target_column not in merged_df.columns:
                raise ValueError(f"Target column '{target_column}' not found in merged DataFrame. Available columns: {merged_df.columns.tolist()}")
            if actual_column not in merged_df.columns:
                raise ValueError(f"Actual column '{actual_column}' not found in merged DataFrame. Available columns: {merged_df.columns.tolist()}")
            
            merged_df = calculate_differences(
                merged_df=merged_df,
                tolerance=tolerance,
                target_area_column=target_column,
                actual_area_column=actual_column,
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
        
        # Filter the merged DataFrame to only include the requested return values
        # First, ensure all requested columns exist
        available_columns = merged_df.columns.tolist()
        valid_return_values = [col for col in return_values if col in available_columns]
        if valid_return_values != return_values:
            missing_columns = set(return_values) - set(valid_return_values)
            logger.warning(f"Some return values not found in DataFrame: {missing_columns}")
            
        # Add calculated columns if they exist in the DataFrame and are not duplicates
        calculated_columns = ['status', 'diff', 'diff_pct']
        valid_calculated_columns = [
            col for col in calculated_columns 
            if col in available_columns and col not in valid_return_values
        ]
        valid_return_values.extend(valid_calculated_columns)
        
        # Create ComparisonResult object with filtered DataFrame
        comparison = ComparisonResult(
            merged_df=merged_df[valid_return_values],
            return_values=valid_return_values,
            comparison_type="name"
        )
        
        # Get BaseResultBundle
        result_bundle = comparison.to_result_bundle()
        
        return merged_df[valid_return_values], result_bundle.summary
        
    except Exception as e:
        logger.exception(f"Processing failed in compare_target_actual")
        raise RuntimeError(f"Processing failed in compare_target_actual: {str(e)}")






