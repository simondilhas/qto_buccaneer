# Advanced Filtering

## Filter Types

### 1. Simple Equality
Filter elements based on exact matches:
```python
include_filter = {"PropertyName": value}

# Example: Get interior elements
{"Pset_WallCommon.IsExternal": False}
```

### 2. Numeric Comparisons
Filter elements based on measurements:
```python
include_filter = {"PropertyName": (operator, value)}

# Example: Get thick walls
{"Width": (">", 0.15)}  # Walls thicker than 15cm

# Available operators: ">", "<", "=", "!=", ">=", "<="
```

### 3. List Containment
Filter elements based on multiple values:
```python
include_filter = {"PropertyName": [value1, value2]}

# Example: Get specific spaces
{"Name": ["Kitchen", "Living Room"]}
```

## Combining Filters

### Using AND Logic
All conditions must be true:
```python
calculator.calculate_walls_interior_structural_area(
    include_filter={
        "Pset_WallCommon.IsExternal": False,  # Must be interior
        "Width": (">", 0.15),                 # Must be thick
        "Name": ["Wall1", "Wall2"]            # Must have specific name
    },
    include_filter_logic="AND"
)
```

### Using OR Logic
Any condition can be true:
```python
calculator.calculate_space_interior_floor_area(
    include_filter={
        "Name": ["Kitchen", "Living Room"],
        "PredefinedType": "INTERNAL"
    },
    include_filter_logic="OR"
)
``` 