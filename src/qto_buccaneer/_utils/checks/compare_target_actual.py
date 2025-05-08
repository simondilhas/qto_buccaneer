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
    # Fill missing values only in actual column
    merged_df[actual_area_column] = merged_df[actual_area_column].fillna(0.0)

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
        target_value = row.get(target_area_column, None)  # Changed from 0.0 to None
        key_target = row.get(key_target_column, None)
        key_actual = row.get(key_actual_column, None)

        # 1. Missing → Target exists, actual missing
        if pd.notna(key_target) and pd.isna(key_actual):
            return 'missing'

        # 2. Project-specific size → Target exists (LongName present), no value planned, but actual value > 0
        if pd.notna(key_target) and (pd.isna(target_value) or target_value < EPSILON) and actual_value > EPSILON:
            return 'project_specific'

        # 3. Project-specific name → No target LongName, but actual value > 0
        if pd.isna(key_target) and pd.notna(key_actual) and actual_value > EPSILON:
            return 'project_specific_name'

        # 4. Extra space → No target LongName, but actual value > 0
        if pd.isna(key_target) and actual_value > EPSILON:
            return 'extra_space'

        # 5. Within tolerance - only check if target value exists
        if pd.notna(target_value) and target_value > EPSILON:
            lower_bound = target_value * (1 - tolerance / 100.0)
            upper_bound = target_value * (1 + tolerance / 100.0)
            if lower_bound <= actual_value <= upper_bound:
                return 'within_tolerance'

        # 6. Otherwise: Out of tolerance
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


### Needed functions for sure rest???

def _aggregate_grouped_data(df: pd.DataFrame, key_columns: Union[str, list[str]], numerical_column: str) -> pd.DataFrame:
    """
    Aggregate data by grouping on key columns and performing various aggregations.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame to be aggregated
    key_columns : Union[str, list[str]]
        Column name(s) to group by. Can be a single string or list of strings
    numerical_column : str
        Column name containing numerical values to sum
    
    Returns:
    --------
    pandas.DataFrame
        Aggregated DataFrame with counts, sums, and unique values as comma-separated lists
    """
    # Convert single string to list for consistent handling
    if isinstance(key_columns, str):
        key_columns = [key_columns]
    
    # First check if numerical column exists
    if numerical_column not in df.columns:
        raise KeyError(f"Numerical column '{numerical_column}' not found in DataFrame")
    
    # Check if all key columns exist
    for col in key_columns:
        if col not in df.columns:
            raise KeyError(f"Key column '{col}' not found in DataFrame")
    
    # Create aggregation dictionary
    agg_dict = {}
    
    # Add count for the first key column
    agg_dict[key_columns[0]] = lambda x: None if df.loc[x.index, numerical_column].isna().all() else len(x)
    
    # Add numerical column aggregation
    agg_dict[numerical_column] = lambda x: x.sum() if not x.isna().all() else None
    
    # Add other columns with unique values as comma-separated lists
    for col in df.columns:
        if col not in key_columns and col != numerical_column:
            agg_dict[col] = lambda x: ', '.join(sorted(set(str(val) for val in x if pd.notna(val))))
    
    # Group by all key columns
    grouped = df.groupby(key_columns).agg(agg_dict).rename(columns={
        key_columns[0]: 'count',
        numerical_column: f'sum_{numerical_column}'
    })
    
    return grouped

def _create_key_column(df, config, data_type='target'):
    """
    Create a new key column based on the config key.
    If key is a single value, creates key column.
    If key is a list, combines values from the list.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame
    config : dict
        Configuration dictionary containing key information
    data_type : str, default='target'
        Specifies whether to create key for 'target' or 'actual' data
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame with new key column added
    """
    # Get the key configuration
    key_config = config['config']['keys']
    
    # Validate data_type
    if data_type not in ['target', 'actual']:
        raise ValueError("data_type must be either 'target' or 'actual'")
    
    # Get the appropriate key
    key = key_config.get(data_type)
    if key is None:
        raise KeyError(f"No key configuration found for {data_type}")
    
    # Create column name
    column_name = f'key'
    
    # Handle the key
    if isinstance(key, list):
        # If it's a list, combine values with underscore
        df[column_name] = df[key].apply(lambda x: '_'.join(x.astype(str)), axis=1)
    else:
        # If it's a single value, just copy the column
        df[column_name] = df[key]

           
    return df

def _prepare_target_data(df, config, data_type='target'):
    """
    Prepare actual data for comparison by creating a key column and aggregating data.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame containing actual data
    config : dict
        Configuration dictionary containing key information
    data_type : str, optional
        Type of data being processed ('actual' or 'target'), defaults to 'actual'

    Returns:
    --------
    pandas.DataFrame
        DataFrame with key column and aggregated data
    """ 
    # Use the passed config directly instead of loading it again
    key_columns = config['config']['keys'][data_type]
    # Convert single string to list for consistent handling
    if isinstance(key_columns, str):
        key_columns = [key_columns]
        
    numerical_column = config['config']['numerical_columns'][data_type]
    columns_to_keep = config['config']['return_values'][data_type]

    # Create key column first
    df = _create_key_column(df, config, data_type)
    
    # Then aggregate the data
    grouped_data = _aggregate_grouped_data(df, 'key', numerical_column)
    
    # Reset index to make 'key' a regular column
    grouped_data = grouped_data.reset_index()
    
    # Rename sum_m2 back to m2 if it exists
    if f'sum_{numerical_column}' in grouped_data.columns:
        grouped_data = grouped_data.rename(columns={f'sum_{numerical_column}': numerical_column})

    columns_to_keep = columns_to_keep + ['count'] + ['key']

    # Select only the columns we want to keep
    df_filtered = grouped_data[columns_to_keep]

    return df_filtered

def _create_pivot_columns(df, pivot_column, quantity_column):
    """
    Create new columns based on unique values in pivot_column, filled with values from quantity_column.
    Columns are created in order from smallest to biggest value.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input dataframe
    pivot_column : str
        Name of the column to create new columns from
    quantity_column : str
        Name of the column containing the values to fill in the new columns
    
    Returns:
    --------
    tuple
        (pandas.DataFrame with new columns added, list of newly created column names)
    """
    # Create a copy of the original dataframe
    result = df.copy()
    
    # Get unique values from pivot column and sort them
    unique_values = sorted(df[pivot_column].unique())
    
    # Keep track of created columns
    created_columns = []
    
    # Create new columns for each unique value
    for value in unique_values:
        # Create new column name using just the value
        new_column = str(value)
        created_columns.append(new_column)
        # Fill the new column with values where pivot_column matches the value
        result[new_column] = np.where(result[pivot_column] == value, result[quantity_column], 0)
        # NEW LINE: Ensure the column is float type
        result[new_column] = result[new_column].astype(float)
    
    return result, created_columns

def _prepare_actual_data(df, config, data_type='actual'):
    """
    Prepare actual data for comparison by creating a key column and aggregating data.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame containing actual data
    config : dict
        Configuration dictionary containing key information
    data_type : str, optional
        Type of data being processed ('actual' or 'target'), defaults to 'actual'

    Returns:
    --------
    pandas.DataFrame
        DataFrame with key column and aggregated data
    """ 
    # Use the passed config directly instead of loading it again
    key_columns = config['config']['keys'][data_type]
    # Convert single string to list for consistent handling
    if isinstance(key_columns, str):
        key_columns = [key_columns]
        
    numerical_column = config['config']['numerical_columns'][data_type]
    columns_to_keep = config['config']['return_values'][data_type]
    expand_column = config['config']['numerical_columns']['expand_column']
    print(expand_column)

    # Create pivot columns and get the list of created columns
    df_pivot, pivot_columns = _create_pivot_columns(df, expand_column, numerical_column)

    # Create key column first
    df_for_aggregation = _create_key_column(df_pivot, config, data_type)
    
    # Then aggregate the data
    grouped_data = _aggregate_grouped_data(df_for_aggregation, 'key', numerical_column)
    
    # Reset index to make 'key' a regular column
    grouped_data = grouped_data.reset_index()
    
    if pivot_columns is not None:
        for col in pivot_columns:
            # Group by key and sum the values
            sums = df_for_aggregation.groupby('key')[col].sum()
            # Map the sums back to the grouped_data
            grouped_data[col] = grouped_data['key'].map(sums)

        numerical_sums = df_for_aggregation.groupby('key')[numerical_column].sum()
        grouped_data[numerical_column] = grouped_data['key'].map(numerical_sums)

    # Add count and key to columns to keep
    columns_to_keep = columns_to_keep + ['count'] + ['key'] + [numerical_column]
    
    # Combine the filtered columns with the pivot columns
    final_columns = columns_to_keep + pivot_columns
    
    # Select the combined columns, but only those that exist in grouped_data
    available_columns = [col for col in final_columns if col in grouped_data.columns]
    df_filtered = grouped_data[available_columns]

    return df_filtered

def _merge_target_and_actual(df_target, df_actual):
    """
    Merge target and actual dataframes on the 'key' column.
    
    Parameters:
    df_target : pandas.DataFrame
        Target dataframe
    df_actual : pandas.DataFrame
        Actual dataframe

    Returns:
    pandas.DataFrame
        Merged dataframe with target and actual data

    """
    sufix_target = "_target"
    sufix_actual = "_actual"
    # rename the columns of the target dataframe
    df_target.columns = [col + sufix_target for col in df_target.columns]
    # rename the columns of the actual dataframe
    df_actual.columns = [col + sufix_actual for col in df_actual.columns]

    # Merge the dataframes on the 'key' column
    df_merged = pd.merge(df_target, df_actual, left_on=f'key{sufix_target}', right_on=f'key{sufix_actual    }', how='left')
    # Merge the dataframes on the 'key' column

    
    return df_merged


def process_compare_target_actual_logic(
    target_df: pd.DataFrame,
    actual_df: pd.DataFrame,
    config: Dict[str, Any]
) -> BaseResultBundle:
    """Core data processing logic for the tool"""

    # Get configuration from the config
    # The config is nested under 'config' key
    check_config = config.get('config', {})
    if not check_config:
        raise ValueError("No 'config' section found in the check configuration")
        
    # Log available columns for debugging
    logger.info(f"Target DataFrame columns: {target_df.columns.tolist()}")
    logger.info(f"Actual DataFrame columns: {actual_df.columns.tolist()}")
    
    # Prepare target and actual data
    target_df = _prepare_target_data(target_df, config, 'target')
    actual_df = _prepare_actual_data(actual_df, config, 'actual')
    merged_df = _merge_target_and_actual(target_df, actual_df)
    
    # Get return values from config
    return_values = check_config.get('return_values', [])
    
    # Calculate differences if numerical comparison columns are provided
    if 'numerical_comparison' in check_config:
        numerical_config = check_config['numerical_comparison']
        tolerance = numerical_config.get('tolerance', 5.0)  # Default tolerance of 5%
        
        target_key = check_config['keys']['target']
        actual_key = check_config['keys']['actual']

        target_column = f"{numerical_config['target']}_target"
        actual_column = f"{numerical_config['actual']}_actual"
        
        merged_df = calculate_differences(
            merged_df=merged_df,
            tolerance=tolerance,
            target_area_column=target_column,
            actual_area_column=actual_column,
            key_target_column=f"{target_key}_target",
            key_actual_column=f"{actual_key}_actual"
        )
        
        # Create ComparisonResult object for numerical comparison
        comparison = ComparisonResult(
            merged_df=merged_df,
            return_values=return_values,
            numerical_target_column=target_column,
            numerical_actual_column=actual_column,
            comparison_type="numerical"
        )
    else:
        # For name comparison, set status based on presence in target and actual
        target_key = check_config['keys']['target']
        actual_key = check_config['keys']['actual']
        
        merged_df['status'] = merged_df.apply(
            lambda row: 'missing' if pd.isna(row[f'{actual_key}_actual']) else 
                       'extra' if pd.isna(row[f'{target_key}_target']) else 
                       'match',
            axis=1
        )
        
        # Create ComparisonResult object for name comparison
        comparison = ComparisonResult(
            merged_df=merged_df,
            return_values=return_values,
            comparison_type="name"
        )
    
    # Get BaseResultBundle
    result_bundle = comparison.to_result_bundle()
    
    # Filter the merged DataFrame to only include the requested return values
    available_columns = merged_df.columns.tolist()
    valid_return_values = [col for col in return_values if col in available_columns]
    if valid_return_values != return_values:
        missing_columns = set(return_values) - set(valid_return_values)
        logger.warning(f"Some return values not found in DataFrame: {missing_columns}")
    
    # Update the result bundle with the filtered DataFrame
    result_bundle.dataframe = merged_df[valid_return_values]
    
    return result_bundle






