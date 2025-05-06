import pytest
import os
import sys
import pandas as pd
from pathlib import Path

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from qto_buccaneer.utils.metadata_filter import MetadataFilter

@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        'Name': ['Room 101', 'Room 102', 'Room 103', 'Room 104'],
        'Area': [20.0, 25.0, 30.0, 15.0],
        'Type': ['Office', 'Meeting', 'Office', 'Storage'],
        'IsExternal': [True, False, True, False],
        'Floor': [1, 1, 2, 2]
    })

def test_filter_df_exact_match(sample_df):
    """Test filtering with exact match."""
    filters = {'Type': 'Office'}
    filtered_df = MetadataFilter.filter_df(sample_df, filters)
    
    assert len(filtered_df) == 2
    assert all(filtered_df['Type'] == 'Office')

def test_filter_df_multiple_values(sample_df):
    """Test filtering with multiple allowed values."""
    filters = {'Type': ['Office', 'Storage']}
    filtered_df = MetadataFilter.filter_df(sample_df, filters)
    
    assert len(filtered_df) == 3
    assert all(filtered_df['Type'].isin(['Office', 'Storage']))

def test_filter_df_comparison_operators(sample_df):
    """Test filtering with comparison operators."""
    filters = {'Area': [(">", 20.0)]}
    filtered_df = MetadataFilter.filter_df(sample_df, filters)
    
    assert len(filtered_df) == 2
    assert all(filtered_df['Area'] > 20.0)
    
    # Test with multiple conditions
    filters = {'Area': [(">", 15.0), ("<", 30.0)]}
    filtered_df = MetadataFilter.filter_df(sample_df, filters)
    
    assert len(filtered_df) == 2
    assert all(filtered_df['Area'] > 15.0)
    assert all(filtered_df['Area'] < 30.0)

def test_filter_df_multiple_fields(sample_df):
    """Test filtering with multiple fields."""
    filters = {
        'Type': 'Office',
        'Floor': 2
    }
    filtered_df = MetadataFilter.filter_df(sample_df, filters)
    
    assert len(filtered_df) == 1
    assert filtered_df.iloc[0]['Name'] == 'Room 103'

def test_filter_df_boolean_field(sample_df):
    """Test filtering with boolean field."""
    filters = {'IsExternal': True}
    filtered_df = MetadataFilter.filter_df(sample_df, filters)
    
    assert len(filtered_df) == 2
    assert all(filtered_df['IsExternal'] == True)

def test_filter_df_from_str_simple(sample_df):
    """Test filtering with simple string expression."""
    filtered_df = MetadataFilter.filter_df_from_str(sample_df, "Type=Office")
    
    assert len(filtered_df) == 2
    assert all(filtered_df['Type'] == 'Office')

def test_filter_df_from_str_complex(sample_df):
    """Test filtering with complex string expression."""
    filtered_df = MetadataFilter.filter_df_from_str(sample_df, "Type=Office AND Area>20.0")
    
    assert len(filtered_df) == 1
    assert filtered_df.iloc[0]['Name'] == 'Room 103'
    
    # Test with OR condition
    filtered_df = MetadataFilter.filter_df_from_str(sample_df, "Type=Office OR Area<20.0")
    
    assert len(filtered_df) == 3
    assert set(filtered_df['Name']) == set(['Room 101', 'Room 103', 'Room 104'])

def test_filter_df_from_str_with_parentheses(sample_df):
    """Test filtering with parentheses in expression."""
    filtered_df = MetadataFilter.filter_df_from_str(
        sample_df, 
        "Type=Office AND (Floor=1 OR Area>25.0)"
    )
    
    assert len(filtered_df) == 2
    assert set(filtered_df['Name']) == set(['Room 101', 'Room 103'])