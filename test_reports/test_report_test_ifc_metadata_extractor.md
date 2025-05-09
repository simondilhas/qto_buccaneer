# Test Execution Report

## Summary

- Total tests: 10
- Passed: 3
- Failed: 7
- Skipped: 0

## Failed Tests Analysis

### test_extract_materials

**Problem**: Assertion failed

**Error**: E       AssertionError: assert 'material' in {'Materials': ['Concrete']}

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_build_element_id_mapping

**Problem**: Assertion failed

**Error**: E       AssertionError: assert 'BUILDING_ID' in {'PROJECT_ID': 1}

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_create_element_record

**Error Details**:
```
mock_ifc_file = <MagicMock id='1950485128592'>

    def test_create_element_record(mock_ifc_file):
        """Test creating an element record."""
        globalid_to_id, all_elements = _build_element_id_mapping(mock_ifc_file)
>       wall = [el for el in all_elements if el.is_a() == "IfcWall"][0]
E       IndexError: list index out of range

tests\test_ifc_metadata_extractor.py:256: IndexError
```

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_extract_ifc_metadata

**Problem**: Assertion failed

**Error**: E       AssertionError: assert 1 >= 3

**Details**:

- E        +  where 1 = len([{'id': 1, 'parent_id': None, 'GlobalId': 'PROJECT_ID', 'IfcEntity': 'IfcProject', 'Classifications': [], 'Systems': [], 'Name': 'Test Project', 'call_args_list': [], 'call_count': 0, 'called': False, 'method_calls': [GlobalId], 'mock_calls': [GlobalId]}])

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_extract_metadata_dataframe

**Problem**: Assertion failed

**Error**: E       AssertionError: assert False

**Details**:

- E        +  where False = isinstance((   id     GlobalId           Name         type\n0   1   PROJECT_ID   Test Project   IfcProject\n1   2  BUILDING_ID  Test Building  IfcBuilding\n2   3      WALL_ID      Test Wall      IfcWall,), <class 'pandas.core.frame.DataFrame'>)

- E        +    where <class 'pandas.core.frame.DataFrame'> = pd.DataFrame

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_extract_metadata_json

**Problem**: Assertion failed

**Error**: E       AssertionError: assert False

**Details**:

- E        +  where False = isinstance(({'elements': {'1': {'id': 1, 'GlobalId': 'PROJECT_ID', 'Name': 'Test Project', 'type': 'IfcProject'}, '2': {'id': 2, 'GlobalId': 'BUILDING_ID', 'Name': 'Test Building', 'type': 'IfcBuilding'}, '3': {'id': 3, 'GlobalId': 'WALL_ID', 'Name': 'Test Wall', 'type': 'IfcWall'}}},), dict)

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_extract_metadata_json_file

**Problem**: Assertion failed

**Error**: E       AssertionError: assert False

**Details**:

- E        +  where False = isinstance(('C:\\Users\\ciunt\\AppData\\Local\\Temp\\pytest-of-ciunt\\pytest-2\\test_extract_metadata_json_fil0\\output\\test_project_metadata.json',), str)

**Suggested Fix**: Update the implementation to correctly handle these cases.
