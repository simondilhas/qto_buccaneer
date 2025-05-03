from pathlib import Path
import yaml
from typing import Any, Dict, List, Optional, Union
from qto_buccaneer.utils.yaml_utils import SafeLoader

class BuildingSummary:
    """
    A class for managing building summary data stored in YAML format.

    This class provides functionality to load, save, and modify building summary data.
    The data is stored in a YAML file and can be easily manipulated through the class methods.

    Attributes:
        path (Path): The path to the YAML file containing the building summary data
        data (dict): The in-memory representation of the building summary data

    Example:
        >>> summary = BuildingSummary(
        ...     path=Path("building_summary.yaml"),
        ...     building_name="Building A"
        ... )
        >>> summary.load()
        >>> summary.set_name("Office Building A")
        >>> # Add data to groups
        >>> summary.add("total_area", 5000, group="measurements")
        >>> summary.add("floors", 5, group="measurements")
        >>> summary.add("energy_rating", "A+", group="ratings")
        >>> # Add a file
        >>> summary.add("input_file", "model.ifc", group="files")
        >>> summary.save()
        >>> summary.print()
        Building: Office Building A
        Measurements:
          - total_area: 5000
          - floors: 5
        Ratings:
          - energy_rating: A+
        Files:
          - input_file: model.ifc
    """

    def __init__(self, path: Path, building_name: str, template_path: Optional[Path] = None):
        """
        Initialize the BuildingSummary object.

        Args:
            path: Path to the YAML file
            building_name: Name of the building
            template_path: Optional path to a template YAML file
        """
        self.path = path
        self.building_name = building_name
        self.template_path = template_path
        self.data = {}
        self._initialize_data()
        # Store the building directory path for relative path conversion
        self.building_dir = path.parent
        # Set the building name in the data
        self.set_name(building_name)

    def _initialize_data(self):
        """Initialize the data structure with default values."""
        self.data = {
            "building_name": self.building_name,
            "checks": [],
            "metrics": [],
            "reports": [],
            "data": {},
            "helper_data": []
        }

    def _load_template(self) -> dict:
        """Load data from the template file if it exists."""
        if self.template_path and self.template_path.exists():
            with open(self.template_path, "r") as f:
                return yaml.safe_load(f)
        return {}

    def load(self):
        """
        Load building summary data from the YAML file.

        Returns:
            BuildingSummary: The instance itself for method chaining

        Example:
            >>> summary = BuildingSummary(Path("building_summary.yaml"), "Building A")
            >>> summary.load()
        """
        if self.path.exists():
            with open(self.path, "r") as f:
                # Use safe_load to ensure we don't load any Python objects
                self.data = yaml.safe_load(f)
                self._initialize_data()
        return self
            


    def save(self):
        """
        Save the current building summary data to the YAML file.

        Example:
            >>> summary = BuildingSummary(Path("building_summary.yaml"), "Building A")
            >>> summary.load()
            >>> summary.set_name("New Building")
            >>> summary.save()
        """
        # Convert tuples to lists before saving
        def convert_tuples_to_lists(obj):
            if isinstance(obj, tuple):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: convert_tuples_to_lists(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_tuples_to_lists(item) for item in obj]
            return obj

        data_to_save = convert_tuples_to_lists(self.data)
        
        with open(self.path, 'w') as f:
            yaml.dump(data_to_save, f, default_flow_style=False, sort_keys=False)

    def set_name(self, name: str):
        """
        Set the name of the building.

        Args:
            name (str): The new name for the building

        Example:
            >>> summary = BuildingSummary(Path("building_summary.yaml"), "Building A")
            >>> summary.load()
            >>> summary.set_name("Residential Complex B")
        """
        self.data["name"] = name

    def _convert_to_relative_path(self, path: Union[str, Path]) -> str:
        """
        Convert an absolute path to a path relative to the building directory.
        
        Args:
            path: The path to convert (can be string or Path)
            
        Returns:
            str: The relative path as a string
        """
        if isinstance(path, str):
            path = Path(path)
        try:
            # Try to make the path relative to the building directory
            relative_path = path.relative_to(self.building_dir)
            return str(relative_path)
        except ValueError:
            # If the path is not under the building directory, return it as is
            return str(path)

    def _add_dict(self, data: dict, group: str) -> None:
        """Add data to a dictionary-type group."""
        if group not in self.data:
            self.data[group] = {}
        # For checks, we want to replace the entire dictionary
        if group == "checks":
            self.data[group] = data
        else:
            # Convert any paths in the data to relative paths
            converted_data = {}
            for key, value in data.items():
                if isinstance(value, (str, Path)) and any(ext in str(value).lower() for ext in ['.ifc', '.json', '.xlsx', '.yaml', '.yml']):
                    converted_data[key] = self._convert_to_relative_path(value)
                else:
                    converted_data[key] = value
            self.data[group].update(converted_data)

    def _add_list(self, data: dict, group: str) -> None:
        """Add data to a list group.
        
        Args:
            data: Dictionary containing the data to add
            group: Group name to add the data under
        """
        if group not in self.data:
            self.data[group] = []
        
        if isinstance(data, list):
            # If data is a list, extend the group's list
            self.data[group].extend(data)
        else:
            # If data is a dictionary, append it to the group's list
            self.data[group].append(data)

    def add(self, *, data: dict, group: Optional[str] = None) -> None:
        """
        Add data to the summary.
        
        Args:
            data: Dictionary containing the data to add
            group: Optional group name to add the data under
        """
        if group:
            # Get the template value to determine the type
            template_value = self._load_template().get(group, [])
            
            # If template defines it as a list, use _add_list
            if isinstance(template_value, list):
                self._add_list(data, group)
            # Otherwise use _add_dict
            else:
                self._add_dict(data, group)
        else:
            # Update other data directly
            self.data.update(data)

    def get(self, key: str, group: Optional[str] = None) -> Optional[Any]:
        """
        Get a value by key, optionally from a group.
        For helper_data, you can access nested keys using dot notation (e.g. "extracted_ifc_metadata.total_elements")

        Args:
            key (str): The data key or dot-notation path
            group (Optional[str]): The group to get the data from

        Returns:
            Optional[Any]: The value, or None if not found
        """
        if group == "files":
            for entry in self.data["files"]:
                if key in entry:
                    return entry[key]
            return None
        
        if group == "helper_data":
            # Split the key by dots to handle nested access
            keys = key.split('.')
            current_data = self.data["helper_data"]
            
            # If it's a list, take the first item
            if isinstance(current_data, list) and current_data:
                current_data = current_data[0]
            
            # Traverse the nested structure
            for k in keys:
                if isinstance(current_data, dict) and k in current_data:
                    current_data = current_data[k]
                else:
                    return None
            return current_data
            
        if group:
            # For other groups, try direct access
            if group in self.data:
                if isinstance(self.data[group], dict):
                    return self.data[group].get(key)
                elif isinstance(self.data[group], list):
                    for entry in self.data[group]:
                        if key in entry:
                            return entry[key]
            return None
            
        return self.data["data"].get(key)

    def get_group(self, group: str) -> List[Dict[str, Any]]:
        """
        Get data from a specific group.

        Args:
            group (str): The group to get data from

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing the group data
        """
        if group == "files":
            return self.data["files"]
        # Try both the old format (groups) and new format (direct in root)
        if "groups" in self.data:
            return self.data["groups"].get(group, [])
        return self.data.get(group, [])

    def get_all(self) -> Dict[str, Any]:
        """
        Get all data not in groups.

        Returns:
            Dict[str, Any]: Dictionary of all ungrouped data
        """
        return self.data["data"]

    def print(self):
        """
        Print the building summary data in a formatted way.

        Example:
            >>> summary = BuildingSummary(Path("building_summary.yaml"), "Building A")
            >>> summary.load()
            >>> summary.set_name("Office Building A")
            >>> summary.add("total_area", 5000, group="measurements")
            >>> summary.print()
            Building: Office Building A
            Measurements:
              - total_area: 5000
        """
        # Always load the latest data before printing
        self.load()
        print(f"Building: {self.data.get('name', 'Unnamed')}")
        
        # Print all lists
        for field in ["files", "checks", "metrics", "benchmarks"]:
            if self.data.get(field):
                print(f"\n{field.title()}:")
                for entry in self.data[field]:
                    if isinstance(entry, dict):
                        for key, value in entry.items():
                            print(f"  - {key}: {value}")
                    else:
                        print(f"  - {entry}")
