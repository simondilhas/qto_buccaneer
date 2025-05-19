import pytest
from pathlib import Path
import pandas as pd
import json
import yaml
from qto_buccaneer._utils._result_bundle import BaseResultBundle

def test_result_bundle_initialization():
    # Test initialization with all parameters
    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    json_data = {'key': 'value'}
    folderpath = Path('test/path')
    yaml_summary = 'test: value'
    
    bundle = BaseResultBundle(
        dataframe=df,
        json=json_data,
        folderpath=folderpath,
        yaml_summary=yaml_summary
    )
    
    assert bundle.dataframe.equals(df)
    assert bundle.json == json_data
    assert bundle.folderpath == folderpath
    assert bundle.yaml_summary == yaml_summary
    
    # Test initialization with minimal parameters
    minimal_bundle = BaseResultBundle(dataframe=df, json=json_data)
    assert minimal_bundle.dataframe.equals(df)
    assert minimal_bundle.json == json_data
    assert minimal_bundle.folderpath is None
    assert minimal_bundle.yaml_summary is None

def test_result_bundle_conversions():
    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    json_data = {'key': 'value'}
    bundle = BaseResultBundle(dataframe=df, json=json_data)
    
    # Test to_df
    assert bundle.to_df().equals(df)
    
    # Test to_dict
    assert bundle.to_dict() == json_data
    
    # Test to_json
    assert bundle.to_json() == json.dumps(json_data, indent=2)
    
    # Test to_yaml_summary
    yaml_output = bundle.to_yaml_summary()
    assert isinstance(yaml_output, str)
    assert yaml.safe_load(yaml_output) == json_data

def test_save_json(tmp_path):
    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    json_data = {'key': 'value'}
    bundle = BaseResultBundle(dataframe=df, json=json_data)
    
    # Test saving to file
    output_path = tmp_path / 'test_output.json'
    bundle.save_json(output_path)
    
    # Verify file was created and contains correct content
    assert output_path.exists()
    with open(output_path, 'r') as f:
        saved_content = json.load(f)
    assert saved_content == json_data

def test_yaml_summary_caching():
    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    json_data = {'key': 'value'}
    bundle = BaseResultBundle(dataframe=df, json=json_data)
    
    # First call should generate the YAML
    first_yaml = bundle.to_yaml_summary()
    assert bundle.yaml_summary is not None
    
    # Second call should use cached value
    second_yaml = bundle.to_yaml_summary()
    assert first_yaml == second_yaml 