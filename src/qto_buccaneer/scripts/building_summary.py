from pathlib import Path
import yaml
from typing import Any, Dict, List, Optional, Union

class BuildingSummary:
    """
    A class for managing building summary data stored in YAML format.

    This class provides functionality to load, save, and modify building summary data.
    The data is stored in a YAML file and can be easily manipulated through the class methods.

    Attributes:
        path (Path): The path to the YAML file containing the building summary data
        data (dict): The in-memory representation of the building summary data

    Example:
        >>> summary = BuildingSummary(Path("building_summary.yaml"))
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

    def __init__(self, path: Path):
        """
        Initialize a BuildingSummary instance.

        Args:
            path (Path): The path to the YAML file where the building summary data is stored
        """
        self.path = path
        # Get the project root from the path (go up 3 levels from the building folder)
        project_root = path.parent.parent.parent
        self.template_path = project_root / "config" / "building_summary_template.yaml"
        self.data = self._load_template()
        self._initialize_data()

    def _initialize_data(self):
        """Initialize the data structure if it doesn't exist."""
        # Use the template data to initialize fields
        template_data = self._load_template()
        for field, default_value in template_data.items():
            if field not in self.data:
                self.data[field] = default_value

    def _load_template(self) -> dict:
        """
        Load the template YAML file.

        Returns:
            dict: The template data
        """
        with open(self.template_path, "r") as f:
            return yaml.safe_load(f)

    def load(self):
        """
        Load building summary data from the YAML file.

        Returns:
            BuildingSummary: The instance itself for method chaining

        Example:
            >>> summary = BuildingSummary(Path("building_summary.yaml"))
            >>> summary.load()
        """
        if self.path.exists():
            with open(self.path, "r") as f:
                self.data = yaml.safe_load(f)
                self._initialize_data()
        return self

    def save(self):
        """
        Save the current building summary data to the YAML file.

        Example:
            >>> summary = BuildingSummary(Path("building_summary.yaml"))
            >>> summary.load()
            >>> summary.set_name("New Building")
            >>> summary.save()
        """
        with open(self.path, "w") as f:
            yaml.dump(self.data, f, default_flow_style=False, sort_keys=False, indent=2)

    def set_name(self, name: str):
        """
        Set the name of the building.

        Args:
            name (str): The new name for the building

        Example:
            >>> summary = BuildingSummary(Path("building_summary.yaml"))
            >>> summary.load()
            >>> summary.set_name("Residential Complex B")
        """
        self.data["name"] = name

    def _add_dict(self, data: dict, group: str) -> None:
        """Add data to a dictionary-type group."""
        if group not in self.data:
            self.data[group] = {}
        # For checks, we want to replace the entire dictionary
        if group == "checks":
            self.data[group] = data
        else:
            self.data[group].update(data)

    def _add_list(self, data: dict, group: str) -> None:
        """Add data to a list-type group."""
        if group not in self.data:
            self.data[group] = []
        # If the group data is a string, convert it to a list
        if isinstance(self.data[group], str):
            self.data[group] = []
        # If the group data is a dictionary, convert it to a list
        if isinstance(self.data[group], dict):
            self.data[group] = []
        if isinstance(data, dict):
            # Check if the data already exists in the list
            for entry in self.data[group]:
                if entry == data:
                    return
            # Add the data as a new entry in the list
            self.data[group].append(data)
        else:
            # Check if the data already exists in the list
            if data not in self.data[group]:
                # Add the data as a new entry in the list
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

        Args:
            key (str): The data key
            group (Optional[str]): The group to get the data from

        Returns:
            Optional[Any]: The value, or None if not found
        """
        if group == "files":
            for entry in self.data["files"]:
                if key in entry:
                    return entry[key]
            return None
        elif group:
            for entry in self.data["groups"].get(group, []):
                if key in entry:
                    return entry[key]
            return None
        return self.data["data"].get(key)

    def get_group(self, group: str) -> List[Dict[str, Any]]:
        """
        Get all data in a group.

        Args:
            group (str): The group to get data from

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing the group data
        """
        if group == "files":
            return self.data["files"]
        return self.data["groups"].get(group, [])

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
            >>> summary = BuildingSummary(Path("building_summary.yaml"))
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
