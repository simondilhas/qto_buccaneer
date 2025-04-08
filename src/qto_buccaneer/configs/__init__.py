"""
## Configuration Overview

1. Metric Configurations (metrics_config_abstractBIM.yaml):
   * Standard metrics: Single-value calculations for the entire project
   * Room-based metrics: Calculations grouped by room
   * Grouped-by-attribute metrics: Calculations grouped by specific attributes
   * Derived metrics: Metrics calculated from other metrics using formulas

2. Configuration Structure:
   Each metric is defined with the following keys:
   
   * description
     - A short description of the metric
   
   * quantity_type
     - Type of quantity ("area", "volume", "count")
   
   * ifc_entity
     - IFC entity type (e.g., "IfcWall", "IfcSlab")
   
   * pset_name
     - Property Set name (optional for attributes)
   
   * prop_name
     - Property or attribute name
   
   * include_filter
     - Conditions for including elements
   
   * include_filter_logic
     - Logic for combining include filters ("AND"/"OR")
   
   * subtract_filter
     - Conditions for subtracting elements
   
   * subtract_filter_logic
     - Logic for combining subtract filters ("AND"/"OR")

3. Filter Types and Examples

1. Simple key-value:
    ```yaml
    include_filter:
        PredefinedType: "INTERNAL"
    ```

2. Multiple values:
    ```yaml
    subtract_filter:
        Name: ["LUF", "Void"]
    ```

3. Boolean value:
    ```yaml
    include_filter:
        Pset_CoveringCommon.IsExternal: true
    ```

4. Conditional operators:
    ```yaml
    subtract_filter:
        Thickness: ["<", 0.1]
    ```

4. Metric Types

1. Standard Metrics:
    - Single value for entire project
    ```yaml
    gross_floor_area:
        description: "Total gross floor area"
        quantity_type: "area"
        ifc_entity: "IfcSpace"
    ```

2. Room-Based Metrics:
    - Grouped by room attributes
    ```yaml
    windows_area_by_room:
        description: "Windows grouped by room"
        ifc_entity: "IfcWindow"
        grouping_attribute: "GlobalId"
    ```

3. Grouped-by-Attribute Metrics:
    - Grouped by specific element attributes
    ```yaml
    facade_net_area_by_direction:
        description: "Facade area by direction"
        grouping_attribute: "Pset_abstractBIM.Normal"
    ```

4. Derived Metrics:
    - Calculated using formulas from other metrics
    ```yaml
    construction_area:
        description: "Total construction area"
        formula: "gross_floor_area - space_interior_floor_area"
    ```

Note: When adding new metrics, ensure they follow the appropriate structure based on 
their type and include all required fields. The configuration system validates the 
structure and relationships between metrics during loading.
"""
