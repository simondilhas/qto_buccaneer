"""
Configuration files for QTO Buccaneer.

This package contains:
    - Metric configurations (metrics_config_abstractBIM.yaml)
    - Enrichment configurations (enrichment_config_abstractBIM.yaml)
    - Report templates (report_templat.tex)
    - Space tables (enrichment_space_table.xlsx)

Configuration for project metrics.Each metric is defined as a dictionary with the following keys:
- description: A short description of the metric.
- quantity_type: The type of quantity to calculate. Options include:
    - "area"
    - "volume"
    - "count"
- ifc_entity: The IFC entity to calculate the quantity for (e.g. IfcWall, IfcSlab).
- pset_name: The name of the Property Set (Pset) to retrieve the property from.
- prop_name: The name of the property or attribute within the Pset (Property Set) to use for quantity calculation.
- include_filter: A dictionary of conditions to include only specific elements.
- include_filter_logic: Logical operator to combine multiple include filters. Options:
    - "AND"
    - "OR"
- subtract_filter: A dictionary of conditions to subtract specific elements from the result.
- subtract_filter_logic: Logical operator to combine multiple subtract filters. Options:
    - "AND"
    - "OR"

---------------------------
Filter Key Usage Examples:
---------------------------

Use filters to narrow down the included or subtracted elements. Examples:1. Key-value pair:
   - description: "Calculate area of internal walls"
   - include_filter: PredefinedType: "INTERNAL"2. Filter with multiple values:
   - subtract_filter: Name: ["LUF", "Void"]3. Filter with boolean value:
   - subtract_filter: Pset_CoveringCommon.IsExternal: true4. Filter with condition (operator, value):
   - subtract_filter: Thickness: ("<", 0.1)Combine multiple conditions using include_filter_logic or subtract_filter_logic:
Example:
    include_filter: PredefinedType: "INTERNAL", Pset_SpaceCommon.IsExternal: true
    include_filter_logic: "AND"adding new metrics and template:

1. add a new metric to the metrics list by copying this template yaml:

metrics:
  new_metric:
    description: "Description of the metric"
    quantity_type: "area" or "volume" or "count"
    ifc_entity: "IfcSpace"
    pset_name: "Pset_Name" (leave blank for attributes)
    prop_name: "Attribute Name or Property Name"
    include_filter:
      "Key": "Value"
      "Key": ["Value1", "Value2"]
      ...
    include_filter_logic: "AND" or "OR"
    subtract_filter:
      "Key": ["<"", Number]
      "Key": ["Value1", "Value2"]
      ...
    subtract_filter_logic: "OR"Explain the difference between metrics and room-based metrics:

- metrics: Calculated based on all spaces or elements in the project.
- room-based metrics: Calculated based on spaces grouped by room.
"""
