import pytest
import os
import sys
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.utils.config_loader import load_config

# Test data
VALID_CONFIG_YAML = """
project:
  name: Test Project
  description: A test project
metrics:
  - name: area_per_person
    description: Area per person
    formula: area / occupancy
    unit: m²/person
"""

INVALID_CONFIG_YAML = """
project:
  name: Test Project
metrics:
  - name: invalid_metric
    description: Missing formula
"""

def test_load_config_from_file():
    """Test loading a valid configuration from a file."""
    with patch("builtins.open", mock_open(read_data=VALID_CONFIG_YAML)):
        config = load_config("dummy_path.yaml")
        
        # Assertions
        assert config is not None
        assert "project" in config
        assert config["project"]["name"] == "Test Project"
        assert "metrics" in config
        assert len(config["metrics"]) == 1
        assert config["metrics"][0]["name"] == "area_per_person"

def test_load_config_with_validation():
    """Test that validation works correctly."""
    # This test assumes load_config has validation functionality
    with patch("builtins.open", mock_open(read_data=VALID_CONFIG_YAML)):
        config = load_config("dummy_path.yaml", validate=True)
        assert config is not None

def test_load_config_invalid_yaml():
    """Test handling of invalid YAML."""
    with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
        with pytest.raises(yaml.YAMLError):
            load_config("dummy_path.yaml")

def test_load_config_file_not_found():
    """Test handling of file not found error."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_file.yaml")

def test_load_config_with_defaults():
    """Test loading config with default values."""
    minimal_config = """
    project:
      name: Minimal Project
    """
    with patch("builtins.open", mock_open(read_data=minimal_config)):
        # Assuming load_config has a defaults parameter
        config = load_config("dummy_path.yaml", defaults={"metrics": []})
        assert "metrics" in config
        assert config["metrics"] == []