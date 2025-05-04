from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union
import pandas as pd
import json, yaml

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle entity_instance objects."""
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

@dataclass
class ResultBundle:
    """A container class for storing and converting analysis results in multiple formats.
    
    This class provides a unified interface for handling analysis results that can be represented
    as both a pandas DataFrame and a JSON-compatible dictionary. It supports conversion between
    different formats and provides methods for saving results to files in various formats (JSON, Excel, YAML).

    The class handles various data structures including:
    - Lists of objects
    - Nested dictionaries with 'elements' keys
    - Metadata dictionaries
    - Processing summaries with file references
    
    Attributes:
        dataframe: Optional pandas DataFrame containing the tabular data
        json: Optional dictionary containing the JSON-compatible data
        summary: Optional string containing a YAML summary for reporting
        folderpath: Optional Path object specifying the base directory for saving results
        ifc_model: Optional ifcopenshell.file object containing the IFC model

    Methods:
        from_json: Create a ResultBundle from a JSON file
        from_excel: Create a ResultBundle from an Excel file
        to_df: Convert the result bundle to a pandas DataFrame
        to_dict: Convert the result bundle to a dictionary
        to_json: Convert the result bundle to a JSON string
        to_summary: Convert the result bundle to a YAML string
        save_json: Save the result bundle to a JSON file
        save_excel: Save the result bundle to an Excel file
        save_summary: Save the summary to a YAML file
        get_summary_dict: Get the summary as a dictionary
        get_ifc: Get the IFC model if available
        save_ifc: Save the IFC model to a file if available
    """
    dataframe: Optional[pd.DataFrame]
    json: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    folderpath: Optional[Path] = None
    ifc_model: Optional['ifcopenshell.file'] = None

    @property
    def output_filepath(self) -> Optional[str]:
        """Get the output filepath from the JSON data.
        
        Returns:
            Optional[str]: The output filepath if available, None otherwise
        """
        if self.json and "output_filepath" in self.json:
            return self.json["output_filepath"]
        return None

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
        if self.dataframe is None and self.json is not None:
            if isinstance(self.json, list):
                # If JSON is a list of objects, convert directly to DataFrame
                self.dataframe = pd.DataFrame(self.json)
            elif "elements" in self.json and isinstance(self.json["elements"], dict):
                # If JSON has an elements dictionary, convert it to DataFrame
                elements_data = self.json["elements"]
                # Convert the nested dictionary to a list of records
                records = []
                for key, value in elements_data.items():
                    record = value.copy()
                    record['element_key'] = key  # Add the key as a column
                    records.append(record)
                self.dataframe = pd.DataFrame(records)
            elif "metadata" in self.json and isinstance(self.json["metadata"], dict):
                # Get the actual element data (level 3)
                elements_data = self.json["metadata"]
                # Convert elements data directly to DataFrame
                self.dataframe = pd.DataFrame.from_dict(elements_data, orient='index')
            elif isinstance(self.json, dict) and "files" in self.json:
                # This is a processing summary, load the actual data from files
                records = []
                for file in self.json["files"]:
                    file_path = self.folderpath / f"{file}.json"
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                records.extend(data)
                            elif isinstance(data, dict) and "elements" in data:
                                for key, value in data["elements"].items():
                                    record = value.copy()
                                    record['element_key'] = key
                                    records.append(record)
                if records:
                    self.dataframe = pd.DataFrame(records)
                else:
                    # If no records were found, fall back to the summary
                    self.dataframe = pd.DataFrame([self.json])
            else:
                # If no metadata, try to convert the entire JSON to DataFrame
                self.dataframe = pd.DataFrame([self.json])
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
        return json.dumps(self.json, indent=2, cls=CustomJSONEncoder)

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
            If DataFrame is None, attempts to create one from JSON data
        """
        if self.dataframe is None:
            self.to_df()  # Use the to_df method to ensure consistent DataFrame creation

        if self.dataframe is None:
            raise ValueError("Cannot save to Excel: No DataFrame available and could not create one from JSON data")

        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.dataframe.to_excel(path, index=False, index_label='id')
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

    def get_summary_dict(self) -> Dict[str, Any]:
        """Get the summary as a dictionary."""
        if self.summary is None:
            return {}
        return yaml.safe_load(self.summary)

    def get_ifc(self) -> Optional['ifcopenshell.file']:
        """Get the IFC model if available.
        
        Returns:
            Optional[ifcopenshell.file]: The IFC model if available, None otherwise
            
        Note:
            This method will return None if no IFC model is available in the result bundle.
            This is expected behavior for result bundles that only contain DataFrame data.
        """
        return self.ifc_model

    def save_ifc(self, path: Union[str, Path]) -> Path:
        """Save the IFC model to a file if available.
        
        Args:
            path: String or Path object specifying where to save the IFC file.
                 If relative, will be saved relative to folderpath if set.
            
        Returns:
            Path: The path where the IFC file was saved
            
        Raises:
            ValueError: If no IFC model is available in the result bundle
            
        Note:
            Creates parent directories if they don't exist
        """
        if self.ifc_model is None:
            raise ValueError("Cannot save IFC file: No IFC model available in the result bundle")

        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.parent.mkdir(parents=True, exist_ok=True)
        
        self.ifc_model.write(str(path))
        return path
