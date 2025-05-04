from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union
import pandas as pd
import json, yaml
import zipfile
import os
import ifcopenshell
import io

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle entity_instance objects."""
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

@dataclass
class BaseResultBundle:
    """Base class for all ResultBundle types with common functionality."""
    dataframe: Optional[pd.DataFrame]
    json: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    folderpath: Optional[Path] = None
    ifc_model: Optional['ifcopenshell.file'] = None

    def to_df(self) -> pd.DataFrame:
        """Convert the result bundle to a pandas DataFrame.
        Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement to_df()")

    def save_json(self, path: Union[str, Path]) -> Path:
        """Save the result bundle to a JSON file."""
        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.json, indent=2, cls=CustomJSONEncoder), encoding="utf-8")
        return path

    def save_excel(self, path: Union[str, Path]) -> Path:
        """Save the result bundle to an Excel file."""
        if self.dataframe is None:
            self.dataframe = self.to_df()
        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.dataframe.to_excel(path, index=False)
        return path

@dataclass
class MetadataResultBundle(BaseResultBundle):
    """ResultBundle specifically for IFC metadata."""
    def to_df(self) -> pd.DataFrame:
        """Convert metadata JSON to DataFrame."""
        if self.dataframe is None and self.json is not None:
            if "elements" in self.json:
                self.dataframe = pd.DataFrame.from_dict(self.json["elements"], orient='index')
            else:
                self.dataframe = pd.DataFrame([self.json])
        return self.dataframe

@dataclass
class GeometryResultBundle(BaseResultBundle):
    """ResultBundle specifically for geometry data."""
    def to_df(self) -> pd.DataFrame:
        """Convert geometry data to DataFrame."""
        if self.dataframe is None and self.json is not None:
            if isinstance(self.json, list):
                self.dataframe = pd.DataFrame(self.json)
            else:
                self.dataframe = pd.DataFrame([self.json])
        return self.dataframe

    def save_geometry(self, path: Union[str, Path]) -> Path:
        """Extract geometry zip file to a directory."""
        if self.json is None or "zip_content" not in self.json:
            raise ValueError("No geometry zip content available")

        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.mkdir(parents=True, exist_ok=True)
        
        zip_buffer = io.BytesIO(self.json["zip_content"])
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            zip_file.extractall(path)
        
        return path

@dataclass
class ProcessingResultBundle(BaseResultBundle):
    """ResultBundle for processing summaries and file-based data."""
    def to_df(self) -> pd.DataFrame:
        """Convert processing summary to DataFrame."""
        if self.dataframe is None and self.json is not None:
            if "files" in self.json:
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
                    self.dataframe = pd.DataFrame([self.json])
            else:
                self.dataframe = pd.DataFrame([self.json])
        return self.dataframe

@dataclass
class IFCResultBundle(BaseResultBundle):
    """ResultBundle specifically for IFC model operations."""
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

    def get_ifc(self) -> Optional['ifcopenshell.file']:
        """Get the IFC model if available.
        
        Returns:
            Optional[ifcopenshell.file]: The IFC model if available, None otherwise
        """
        return self.ifc_model

@dataclass
class MetricsResultBundle(BaseResultBundle):
    """ResultBundle specifically for metrics calculations."""
    def to_df(self) -> pd.DataFrame:
        """Convert metrics data to DataFrame."""
        if self.dataframe is None and self.json is not None:
            if isinstance(self.json, list):
                self.dataframe = pd.DataFrame(self.json)
            else:
                self.dataframe = pd.DataFrame([self.json])
        return self.dataframe

    def save_excel(self, path: Union[str, Path]) -> Path:
        """Save metrics data to an Excel file.
        
        Args:
            path: String or Path object specifying where to save the Excel file.
                 If relative, will be saved relative to folderpath if set.
            
        Returns:
            Path: The path where the Excel file was saved
        """
        path = Path(path)
        if not path.is_absolute() and self.folderpath is not None:
            path = self.folderpath / path
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.dataframe is None:
            self.dataframe = self.to_df()
        self.dataframe.to_excel(path, index=False)
        return path

# For backward compatibility
ResultBundle = BaseResultBundle
