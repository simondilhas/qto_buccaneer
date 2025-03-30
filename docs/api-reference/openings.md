# Opening Calculations

## Windows

### calculate_windows_exterior_area()

Calculates the total area of exterior windows.

```python
def calculate_windows_exterior_area(
    include_filter: Optional[dict] = {"Pset_WindowCommon.IsExternal": True},
    include_filter_logic: Literal["AND", "OR"] = "AND",
    subtract_filter: Optional[dict] = None,
    subtract_filter_logic: Literal["AND", "OR"] = "OR",
    ifc_entity: str = "IfcWindow",
    pset_name: str = "Qto_WindowBaseQuantities",
    prop_name: str = "Area",
) -> float
```

Windows are considered exterior if the 'IsExternal' property in Pset_WindowCommon is True.

### calculate_windows_interior_area()

[Similar structure for interior windows...]

## Doors

### calculate_doors_exterior_area()

Calculates the total area of exterior doors.

```python
def calculate_doors_exterior_area(
    include_filter: Optional[dict] = {"Pset_DoorCommon.IsExternal": True},
    include_filter_logic: Literal["AND", "OR"] = "AND",
    subtract_filter: Optional[dict] = None,
    subtract_filter_logic: Literal["AND", "OR"] = "OR",
    ifc_entity: str = "IfcDoor",
    pset_name: str = "Qto_DoorBaseQuantities",
    prop_name: str = "Area",
) -> float
```

### calculate_doors_interior_area()

[Similar structure for interior doors...] 