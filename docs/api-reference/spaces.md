# Space Calculations

## Interior Spaces

### calculate_space_interior_floor_area()

Calculates the total floor area of interior spaces.

```python
def calculate_space_interior_floor_area(
    include_filter: Optional[dict] = {"PredefinedType": "INTERNAL"},
    include_filter_logic: Literal["AND", "OR"] = "AND",
    subtract_filter: Optional[dict] = {
        "Name": ["LUF", "Void"]
    },
    subtract_filter_logic: Literal["AND", "OR"] = "OR",
    ifc_entity: str = "IfcSpace",
    pset_name: str = "Qto_SpaceBaseQuantities",
    prop_name: str = "NetFloorArea",
) -> float
```

#### Default Behavior
- Includes all spaces marked as "INTERNAL"
- Automatically excludes voids and LUF (Lost Usable Floor) spaces
- Returns net floor area (usable space)

#### Examples
```python
# Basic usage - get all interior floor area
calculator = QtoCalculator(loader)
area = calculator.calculate_space_interior_floor_area()
print(f"Interior Floor Area: {area:.2f} m²")

# Calculate area of specific rooms
living_area = calculator.calculate_space_interior_floor_area(
    include_filter={"Name": ["Living Room", "Kitchen", "Bedroom"]}
)

# Exclude technical spaces
net_area = calculator.calculate_space_interior_floor_area(
    subtract_filter={"Name": ["Technical Room", "Shaft"]}
)
```

### calculate_space_interior_volume()

Calculates the total volume of interior spaces.

```python
def calculate_space_interior_volume(
    ifc_entity: str = "IfcSpace",
    include_filter: Optional[dict] = {"PredefinedType": "INTERNAL"},
    include_filter_logic: Literal["AND", "OR"] = "OR",
    subtract_filter: Optional[dict] = None,
    subtract_filter_logic: Literal["AND", "OR"] = "AND",
    pset_name: str = "Qto_SpaceBaseQuantities",
    prop_name: str = "NetVolume",
) -> float
```

#### Default Behavior
- Calculates volume of all internal spaces
- Uses net volume (actual usable space)
- Based on the abstractBIM IFC standard

#### Examples
```python
# Get total interior volume
volume = calculator.calculate_space_interior_volume()
print(f"Interior Volume: {volume:.2f} m³")

# Calculate volume excluding certain spaces
net_volume = calculator.calculate_space_interior_volume(
    subtract_filter={"Name": ["Void", "Technical Space"]}
)
```

## Exterior Spaces

### calculate_space_exterior_area()

Calculates the total exterior area of spaces.

```python
def calculate_space_exterior_area(
    include_filter: Optional[dict] = {"PredefinedType": "EXTERNAL"},
    include_filter_logic: Literal["AND", "OR"] = "AND",
    subtract_filter: Optional[dict] = None,
    subtract_filter_logic: Literal["AND", "OR"] = "OR",
    ifc_entity: str = "IfcSpace",
    pset_name: str = "Qto_SpaceBaseQuantities",
    prop_name: str = "NetFloorArea",
) -> float
```

#### Default Behavior
- Includes all spaces marked as "EXTERNAL"
- Calculates net floor area
- Based on the abstractBIM IFC standard

#### Examples
```python
# Get total exterior space area
exterior_area = calculator.calculate_space_exterior_area()
print(f"Exterior Space Area: {exterior_area:.2f} m²")

# Calculate specific exterior spaces
balcony_area = calculator.calculate_space_exterior_area(
    include_filter={
        "PredefinedType": "EXTERNAL",
        "Name": ["Balcony", "Terrace"]
    }
)
```

## Common Use Cases

### Calculating Total Building Area
```python
# Get gross floor area
interior_area = calculator.calculate_space_interior_floor_area()
exterior_area = calculator.calculate_space_exterior_area()
total_area = interior_area + exterior_area

print(f"Total Building Area: {total_area:.2f} m²")
```

### Space Analysis
```python
# Get living spaces only
living_area = calculator.calculate_space_interior_floor_area(
    include_filter={
        "PredefinedType": "INTERNAL",
        "Name": ["Living Room", "Bedroom", "Kitchen", "Bathroom"]
    }
)

# Get technical spaces
technical_area = calculator.calculate_space_interior_floor_area(
    include_filter={
        "PredefinedType": "INTERNAL",
        "Name": ["Technical Room", "Storage", "Utility"]
    }
)

# Calculate ratio
living_ratio = living_area / (living_area + technical_area) * 100
print(f"Living Space Ratio: {living_ratio:.1f}%")
```

## Notes
- All area measurements are in square meters (m²)
- All volume measurements are in cubic meters (m³)
- Net areas/volumes exclude structural elements
- The calculations follow the abstractBIM IFC standard
- Filters can be combined using AND/OR logic 