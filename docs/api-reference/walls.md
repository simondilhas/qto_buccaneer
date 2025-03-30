# Wall Calculations

## Interior Walls

### calculate_walls_interior_net_side_area()

Calculates the total net side area of interior walls.

```python
def calculate_walls_interior_net_side_area(
    include_filter: Optional[dict] = {"Pset_WallCommon.IsExternal": False},
    include_filter_logic: Literal["AND", "OR"] = "AND",
    subtract_filter: Optional[dict] = None,
    subtract_filter_logic: Literal["AND", "OR"] = "OR",
    ifc_entity: str = "IfcWallStandardCase",
    pset_name: str = "Qto_WallBaseQuantities",
    prop_name: str = "NetSideArea",
) -> float
```

Walls are considered interior if the 'IsExternal' property in Pset_WallCommon is False.
The net side area excludes openings like doors and windows.

#### Example
```python
calculator = QtoCalculator(loader)
area = calculator.calculate_walls_interior_net_side_area()
print(f"Interior Walls Net Side Area: {area:.2f} m²")
```

### calculate_walls_interior_structural_area()

Calculates the total area of interior structural walls (walls thicker than 15cm).

```python
def calculate_walls_interior_structural_area(
    include_filter: Optional[dict] = {
        "Pset_WallCommon.IsExternal": False,
        "Width": (">", 0.15)
    },
    include_filter_logic: Literal["AND", "OR"] = "AND",
    subtract_filter: Optional[dict] = None,
    subtract_filter_logic: Literal["AND", "OR"] = "AND",
    ifc_entity: str = "IfcWallStandardCase",
    pset_name: str = "Qto_WallBaseQuantities",
    prop_name: str = "NetSideArea",
) -> float
```

#### Examples
```python
# Get all interior structural walls (default)
area = calculator.calculate_walls_interior_structural_area()

# Get very thick interior walls (more than 25cm)
area = calculator.calculate_walls_interior_structural_area(
    include_filter={
        "Pset_WallCommon.IsExternal": False,
        "Width": (">", 0.25)
    }
)

# Get specific walls by name
area = calculator.calculate_walls_interior_structural_area(
    include_filter={
        "Name": ["Load-bearing Wall 1", "Load-bearing Wall 2"]
    }
)
```

## Exterior Walls

### calculate_walls_exterior_net_side_area()

Calculates the total net side area of exterior walls.

```python
def calculate_walls_exterior_net_side_area(
    include_filter: Optional[dict] = {"Pset_WallCommon.IsExternal": True},
    include_filter_logic: Literal["AND", "OR"] = "AND",
    subtract_filter: Optional[dict] = None,
    subtract_filter_logic: Literal["AND", "OR"] = "OR",
    ifc_entity: str = "IfcWallStandardCase",
    pset_name: str = "Qto_WallBaseQuantities",
    prop_name: str = "NetSideArea",
) -> float
```

Walls are considered exterior if the 'IsExternal' property in Pset_WallCommon is True.
The net side area excludes openings like windows and doors.

#### Example
```python
calculator = QtoCalculator(loader)
area = calculator.calculate_walls_exterior_net_side_area()
print(f"Exterior Walls Net Side Area: {area:.2f} m²")
``` 