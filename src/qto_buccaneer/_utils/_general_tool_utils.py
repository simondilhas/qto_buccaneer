from typing import Union
import pandas as pd
from qto_buccaneer._utils._result_bundle import ResultBundle
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
            - 'column_details': dict with detailed information about each column
    """
    validation_results = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'missing': [],
        'duplicates': [],
        'available_columns': list(df.columns),
        'column_details': {
            'available': [],
            'missing': [],
            'duplicate': []
        }
    }
    
    # Validate input types
    if not isinstance(df, pd.DataFrame):
        validation_results['errors'].append(f"{df_name} must be a pandas DataFrame")
        validation_results['is_valid'] = False
        return validation_results
    
    if not isinstance(required_columns, (list, dict)):
        validation_results['errors'].append("required_columns must be a list or dictionary")
        validation_results['is_valid'] = False
        return validation_results
    
    # Convert required_columns to a list if it's a dictionary
    if isinstance(required_columns, dict):
        required_columns = list(required_columns.values())
    
    # Check for duplicate columns in required list
    duplicates = [col for col in required_columns if required_columns.count(col) > 1]
    if duplicates:
        validation_results['duplicates'] = duplicates
        validation_results['column_details']['duplicate'] = duplicates
        validation_results['errors'].append(
            f"Duplicate columns in required columns list: {duplicates}"
        )
        validation_results['is_valid'] = False
    
    # Check for missing columns
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        validation_results['missing'] = missing
        validation_results['column_details']['missing'] = missing
        validation_results['errors'].append(
            f"Missing required columns in {df_name}: {missing}"
        )
        validation_results['is_valid'] = False
    
    # Add available columns to details
    validation_results['column_details']['available'] = list(df.columns)
    
    # Format detailed error message
    if not validation_results['is_valid']:
        error_msg = [
            f"\n{df_name} Validation Error:",
            "=" * 50,
            f"Required columns: {', '.join(sorted(required_columns))}",
            f"Available columns: {', '.join(sorted(df.columns))}",
            f"Missing columns: {', '.join(sorted(missing))}",
            f"Duplicate columns: {', '.join(sorted(duplicates))}",
            "=" * 50,
            "Column Mapping Suggestions:"
        ]
        
        # Add column mapping suggestions
        for missing_col in missing:
            similar_cols = [col for col in df.columns if missing_col.lower() in col.lower() or col.lower() in missing_col.lower()]
            if similar_cols:
                error_msg.append(f"  - '{missing_col}' might be: {', '.join(similar_cols)}")
            else:
                error_msg.append(f"  - '{missing_col}' has no similar columns")
        
        validation_results['errors'].append("\n".join(error_msg))
    
    return validation_results

def validate_config(config_list):
    """
    Validate a list of tool config dictionaries, each expected to have
    'tool_name', 'tool_description', and 'tool_config' keys.

    Args:
        config_list: List of dictionaries representing tool configs.

    Raises:
        ValueError: If any config dict is missing required fields.

    Returns:
        The validated config_list.
    """
    required_fields = ['tool_name', 'tool_description', 'tool_config']
    
    # Validate input type
    if not isinstance(config_list, list):
        raise ValueError(
            f"Config should be a list of dictionaries. Got type: {type(config_list)}"
        )
    
    # Validate each config in the list
    errors = []
    for idx, config in enumerate(config_list):
        if not isinstance(config, dict):
            errors.append(
                f"Config at index {idx} must be a dictionary. Got type: {type(config)}"
            )
            continue
            
        missing = [f for f in required_fields if f not in config]
        if missing:
            errors.append(
                f"Config at index {idx} is missing required fields: {', '.join(missing)}\n"
                f"Available fields: {', '.join(config.keys())}"
            )
            
        # Validate tool_config structure
        if 'tool_config' in config:
            tool_config = config['tool_config']
            if not isinstance(tool_config, dict):
                errors.append(
                    f"tool_config at index {idx} must be a dictionary. Got type: {type(tool_config)}"
                )
    
    if errors:
        error_msg = "\n".join(errors)
        raise ValueError(f"Configuration validation failed:\n{error_msg}")
        
    return config_list