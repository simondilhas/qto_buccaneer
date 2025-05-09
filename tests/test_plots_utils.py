import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

import plotly.graph_objects as go
from qto_buccaneer.utils.plots_utils import (
    parse_filter,
    element_matches_conditions,
    apply_layout_settings
)

def test_parse_filter_type_only():
    """Test parsing a filter string with only type."""
    filter_str = "type=IfcWall"
    element_type, conditions = parse_filter(filter_str)
    
    assert element_type == "IfcWall"
    assert conditions == []

def test_parse_filter_with_single_condition():
    """Test parsing a filter string with a single condition."""
    filter_str = "type=IfcWall AND Name=Wall1"
    element_type, conditions = parse_filter(filter_str)
    
    assert element_type == "IfcWall"
    assert conditions == [["Name=Wall1"]]

def test_parse_filter_with_multiple_and_conditions():
    """Test parsing a filter string with multiple AND conditions."""
    filter_str = "type=IfcWall AND Name=Wall1 AND Height=3.0"
    element_type, conditions = parse_filter(filter_str)
    
    assert element_type == "IfcWall"
    assert conditions == [["Name=Wall1"], ["Height=3.0"]]

def test_parse_filter_with_or_conditions():
    """Test parsing a filter string with OR conditions."""
    filter_str = "type=IfcWall AND (Name=Wall1 OR Name=Wall2)"
    element_type, conditions = parse_filter(filter_str)
    
    assert element_type == "IfcWall"
    assert conditions == [["Name=Wall1", "Name=Wall2"]]

def test_parse_filter_with_complex_conditions():
    """Test parsing a filter string with complex conditions."""
    filter_str = "type=IfcWall AND (Name=Wall1 OR Name=Wall2) AND Height=3.0"
    element_type, conditions = parse_filter(filter_str)
    
    assert element_type == "IfcWall"
    assert conditions == [["Name=Wall1", "Name=Wall2"], ["Height=3.0"]]

def test_parse_filter_without_type():
    """Test parsing a filter string without type."""
    filter_str = "Name=Wall1 AND Height=3.0"
    element_type, conditions = parse_filter(filter_str)
    
    assert element_type is None
    assert conditions == [["Name=Wall1"], ["Height=3.0"]]

def test_element_matches_conditions_simple():
    """Test matching an element with simple conditions."""
    element = {
        "Name": "Wall1",
        "Height": "3.0",
        "properties": {
            "IsExternal": "True"
        }
    }
    
    # Test with a single condition that matches
    conditions = [["Name=Wall1"]]
    assert element_matches_conditions(element, conditions) is True
    
    # Test with a single condition that doesn't match
    conditions = [["Name=Wall2"]]
    assert element_matches_conditions(element, conditions) is False

def test_element_matches_conditions_and():
    """Test matching an element with AND conditions."""
    element = {
        "Name": "Wall1",
        "Height": "3.0",
        "properties": {
            "IsExternal": "True"
        }
    }
    
    # Test with multiple conditions that all match
    conditions = [["Name=Wall1"], ["Height=3.0"]]
    assert element_matches_conditions(element, conditions) is True
    
    # Test with multiple conditions where one doesn't match
    conditions = [["Name=Wall1"], ["Height=4.0"]]
    assert element_matches_conditions(element, conditions) is False

def test_element_matches_conditions_or():
    """Test matching an element with OR conditions."""
    element = {
        "Name": "Wall1",
        "Height": "3.0",
        "properties": {
            "IsExternal": "True"
        }
    }
    
    # Test with OR conditions where one matches
    conditions = [["Name=Wall1", "Name=Wall2"]]
    assert element_matches_conditions(element, conditions) is True
    
    # Test with OR conditions where none match
    conditions = [["Name=Wall2", "Name=Wall3"]]
    assert element_matches_conditions(element, conditions) is False

def test_element_matches_conditions_complex():
    """Test matching an element with complex conditions."""
    element = {
        "Name": "Wall1",
        "Height": "3.0",
        "properties": {
            "IsExternal": "True",
            "Material": "Concrete"
        }
    }
    
    # Test with complex conditions that match
    conditions = [
        ["Name=Wall1", "Name=Wall2"],
        ["Height=3.0"],
        ["properties.IsExternal=True", "properties.IsExternal=False"]
    ]
    assert element_matches_conditions(element, conditions) is True
    
    # Test with complex conditions where one group doesn't match
    conditions = [
        ["Name=Wall1", "Name=Wall2"],
        ["Height=4.0"],
        ["properties.IsExternal=True", "properties.IsExternal=False"]
    ]
    assert element_matches_conditions(element, conditions) is False

def test_element_matches_conditions_with_properties():
    """Test matching an element with property conditions."""
    element = {
        "Name": "Wall1",
        "Height": "3.0",
        "properties": {
            "IsExternal": "True",
            "Material": "Concrete"
        }
    }
    
    # Test with property condition that matches
    conditions = [["properties.IsExternal=True"]]
    assert element_matches_conditions(element, conditions) is True
    
    # Test with property condition that doesn't match
    conditions = [["properties.Material=Brick"]]
    assert element_matches_conditions(element, conditions) is False

def test_apply_layout_settings():
    """Test applying layout settings to a figure."""
    # Create a mock figure
    fig = go.Figure()
    
    # Create plot settings
    plot_settings = {
        'defaults': {
            'font_family': 'Arial',
            'text_size': 14,
            'background_color': 'lightgray'
        }
    }
    
    # Apply layout settings
    with patch.object(fig, 'update_layout') as mock_update_layout:
        apply_layout_settings(fig, plot_settings)
        
        # Check that update_layout was called with the correct arguments
        mock_update_layout.assert_called_once()
        
        # Extract the call arguments
        call_args = mock_update_layout.call_args[1]
        
        # Check font settings
        assert call_args['font']['family'] == 'Arial'
        assert call_args['font']['size'] == 14
        
        # Check background color
        assert call_args['paper_bgcolor'] == 'lightgray'
        assert call_args['plot_bgcolor'] == 'lightgray'
        
        # Check legend settings
        assert call_args['showlegend'] is True
        assert call_args['legend']['x'] == 0.98
        assert call_args['legend']['y'] == 0.98 