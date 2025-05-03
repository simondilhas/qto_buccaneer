from pathlib import Path
from typing import Union

def ensure_directory_exists(directory_path: Union[str, Path]) -> Path:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory that should exist
        
    Returns:
        Path: The path to the directory (as a Path object)
        
    Example:
        >>> ensure_directory_exists("path/to/directory")
        Path("path/to/directory")
    """
    directory_path = Path(directory_path)
    directory_path.mkdir(parents=True, exist_ok=True)
    return directory_path 