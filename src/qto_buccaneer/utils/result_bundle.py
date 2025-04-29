from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union
import pandas as pd
import json, yaml

@dataclass
class ResultBundle:
    """A container class for storing and converting analysis results in multiple formats.
    
    This class provides a unified interface for handling analysis results that can be represented
    as both a pandas DataFrame and a JSON-compatible dictionary. It supports conversion between
    different formats and provides methods for saving results to files.
    
    Attributes:
        dataframe: Optional pandas DataFrame containing the tabular data
        json: Dictionary containing the JSON-compatible data
        folderpath: Optional Path object specifying where to save results
        summary: Optional string containing a summary YAML for reporting
    """
    dataframe: Optional[pd.DataFrame]
    json: Optional[Dict[str, Any]] = None
    folderpath: Optional[Path] = None
    summary: Optional[str] = None

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> 'ResultBundle':
        """Create a ResultBundle from a JSON file.
        
        Args:
            path: Path to the JSON file
            
        Returns:
            ResultBundle: A new ResultBundle instance with data loaded from the JSON file
        """
        path = Path(path)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(dataframe=None, json=data, folderpath=path.parent)

    @classmethod
    def from_excel(cls, path: Union[str, Path]) -> 'ResultBundle':
        """Create a ResultBundle from an Excel file.
        
        Args:
            path: Path to the Excel file
            
        Returns:
            ResultBundle: A new ResultBundle instance with data loaded from the Excel file
        """
        path = Path(path)
        df = pd.read_excel(path)
        return cls(dataframe=df, json=None, folderpath=path.parent)

    def to_df(self) -> pd.DataFrame:
        """Convert the result bundle to a pandas DataFrame.
        
        Returns:
            pd.DataFrame: The DataFrame representation of the data
        """
        return self.dataframe

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result bundle to a dictionary.
        
        Returns:
            Dict[str, Any]: The dictionary representation of the data
        """
        return self.json

    def to_json(self) -> str:
        """Convert the result bundle to a JSON string.
        
        Returns:
            str: A formatted JSON string representation of the data
        """
        return json.dumps(self.json, indent=2)

    def to_summary(self) -> str:
        """Convert the result bundle to a YAML string.
        
        The YAML representation is cached after the first conversion to improve performance.
        
        Returns:
            str: A YAML string representation of the data
        """
        if self.summary is None:
            self.summary = yaml.safe_dump(self.json, sort_keys=False)
        return self.summary

    def save_json(self, path: Union[str, Path]) -> Path:
        """Save the result bundle to a JSON file.
        
        Args:
            path: String or Path object specifying where to save the JSON file.
                 If relative, will be saved relative to folderpath if set.
            
        Returns:
            Path: The path where the JSON file was saved
            
        Note:
            Creates parent directories if they don't exist
        """
        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    def save_excel(self, path: Union[str, Path]) -> Path:
        """Save the result bundle to an Excel file.
        
        Args:
            path: String or Path object specifying where to save the Excel file.
                 If relative, will be saved relative to folderpath if set.
            
        Returns:
            Path: The path where the Excel file was saved
            
        Note:
            Creates parent directories if they don't exist
            Requires the DataFrame to be non-None
        """
        if self.dataframe is None:
            raise ValueError("Cannot save to Excel: DataFrame is None")
        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.dataframe.to_excel(path, index=False)
        return path

    def save_summary(self, path: Union[str, Path]) -> Path:
        """Save the summary to a YAML file.
        
        Args:
            path: String or Path object specifying where to save the YAML file.
                 If relative, will be saved relative to folderpath if set.
            
        Returns:
            Path: The path where the YAML file was saved
            
        Note:
            Creates parent directories if they don't exist
        """
        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_summary(), encoding="utf-8")
        return path

    def get_folderpath(self) -> Optional[Path]:
        """Get the folder path where results are being saved.
        
        Returns:
            Optional[Path]: The folder path if set, None otherwise
        """
        return self.folderpath

    def summary(self) -> Dict[str, Any]:
        """Get the summary as a dictionary.
        
        Returns:
            Dict[str, Any]: The summary data as a dictionary
        """
        if self.summary is None:
            return {}
        return yaml.safe_load(self.summary)
