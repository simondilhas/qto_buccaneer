from typing import Union
import pandas as pd
from qto_buccaneer.utils._result_bundle import ResultBundle
from typing import List, Dict, Any

def unpack_dataframe(data: Union[pd.DataFrame, ResultBundle]) -> pd.DataFrame:
    """Unpack a DataFrame from either a DataFrame or ResultBundle.
    
    Args:
        data: Either a pandas DataFrame or a ResultBundle containing a DataFrame
        
    Returns:
        pd.DataFrame: The unpacked DataFrame
        
    Raises:
        ValueError: If the input is neither a DataFrame nor a ResultBundle with a DataFrame
    """
    if isinstance(data, pd.DataFrame):
        return data
    elif isinstance(data, ResultBundle):
        if data.dataframe is not None:
            return data.dataframe
        else:
            raise ValueError("ResultBundle does not contain a DataFrame")
    else:
        raise ValueError("Input must be either a DataFrame or a ResultBundle")
    
def validate_df(
    df: pd.DataFrame,
    required_columns: Union[List[str], Dict[str, str]],
    df_name: str = "DataFrame"
) -> Dict[str, Any]:
    """Validate a DataFrame against required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names or dictionary of column mappings
        df_name: Name of the DataFrame for error messages (default: "DataFrame")
        
    Returns:
        Dict containing validation results:
            - 'is_valid': bool indicating if all validations passed
            - 'errors': list of error messages if any validations failed
            - 'warnings': list of warning messages if any non-critical issues found
            - 'missing': list of missing columns
            - 'duplicates': list of duplicate columns
            - 'available_columns': list of available columns in the DataFrame
    """
    validation_results = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'missing': [],
        'duplicates': [],
        'available_columns': list(df.columns)
    }
    
    # Convert required_columns to a list if it's a dictionary
    if isinstance(required_columns, dict):
        required_columns = list(required_columns.values())
    
    # Check for duplicate columns in required list
    duplicates = [col for col in required_columns if required_columns.count(col) > 1]
    if duplicates:
        validation_results['duplicates'] = duplicates
        validation_results['errors'].append(
            f"Duplicate columns in required columns list: {duplicates}"
        )
        validation_results['is_valid'] = False
    
    # Check for missing columns
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        validation_results['missing'] = missing
        validation_results['errors'].append(
            f"Missing required columns in {df_name}: {missing}"
        )
        validation_results['is_valid'] = False
    
    return validation_results

def validate_config(config):
    required_fields = ['tool_name', 'tool_description']
    missing = [f for f in required_fields if f not in config]
    if missing:
        raise ValueError(f"Missing required config fields: {', '.join(missing)}")
    return config