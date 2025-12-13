"""
Interactive UI Module for IFC Viewer
Provides hierarchical tables, filters, and interactive controls for IFC visualization.
"""

import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go
from collections import defaultdict
from .ifc_viewer_geometry import GeometryExtractor


class HierarchicalTableUI:
    """
    Creates an interactive UI with filters, hierarchical table, visibility controls,
    and property panels for IFC model visualization.
    """
    
    def __init__(self, hierarchy, visualizer, model):
        """
        Initialize the UI with hierarchy data, visualizer, and IFC model.
        
        Parameters:
        -----------
        hierarchy : dict
            Hierarchical structure of IFC elements (storey -> type -> elements)
        visualizer : Visualizer3D
            The 3D visualizer instance
        model : ifcopenshell.file
            The loaded IFC model
        """
        self.hierarchy = hierarchy
        self.visualizer = visualizer
        self.model = model
        self.properties_panel = widgets.HTML(value="<b>Properties:</b><br>Select an object")
        self.all_checkboxes = {}
        self.table_output = widgets.Output()
        self.viewer_output = widgets.Output()
        self.filter_storey = None
        self.filter_ifc_type = None

    def create_ui(self):
        """
        Create and return the complete UI widget with all controls.
        
        Returns:
        --------
        widgets.VBox
            The complete UI widget
        """
        print("🔧 Starting UI creation with filters...")
        
        # Create filter dropdowns
        storey_options = ['All'] + sorted(list(self.hierarchy.keys()))
        ifc_type_options = ['All'] + sorted(set(
            ifc_type for storey in self.hierarchy.values() for ifc_type in storey.keys()
        ))
        
        self.storey_dropdown = widgets.Dropdown(
            options=storey_options,
            value='All',
            description='Storey:',
            layout=widgets.Layout(width='300px')
        )
        
        self.ifc_type_dropdown = widgets.Dropdown(
            options=ifc_type_options,
            value='All',
            description='IFC Type:',
            layout=widgets.Layout(width='300px')
        )
        
        apply_filter_btn = widgets.Button(
            description='Apply Filters',
            button_style='success',
            layout=widgets.Layout(width='120px')
        )
        apply_filter_btn.on_click(self._apply_filters)
        
        filter_box = widgets.HBox([self.storey_dropdown, self.ifc_type_dropdown, apply_filter_btn])
        
        # Create visibility accordion
        visibility_accordion = self._create_visibility_accordion()
        
        # Expand/collapse buttons
        expand_all_btn = widgets.Button(
            description="Expand all",
            button_style='info',
            layout=widgets.Layout(width='120px')
        )
        collapse_all_btn = widgets.Button(
            description="Collapse all",
            button_style='info',
            layout=widgets.Layout(width='120px')
        )
        
        expand_all_btn.on_click(lambda x: self._expand_all_accordions(visibility_accordion))
        collapse_all_btn.on_click(lambda x: self._collapse_all_accordions(visibility_accordion))
        
        buttons_box = widgets.HBox([expand_all_btn, collapse_all_btn])
        
        # Visibility panel
        visibility_panel = widgets.VBox([
            widgets.HTML("<b>🎛️ Element Visibility Control</b>"),
            buttons_box,
            visibility_accordion
        ], layout=widgets.Layout(
            border='1px solid #ddd',
            padding='10px',
            max_height='400px',
            overflow_y='auto'
        ))
        
        # Main control panel
        control_panel = widgets.VBox([
            widgets.HTML("<b>📊 IFC Elements Filters and Table</b>"),
            filter_box,
            self.viewer_output,
            self.table_output,
            self.properties_panel,
            visibility_panel
        ])
        
        # Initial update
        self._update_table()
        self._update_viewer()
        
        print(f"✅ UI created with filters, table, and dynamic viewer")
        return control_panel

    def _create_table(self):
        """Create the interactive table with QTO properties."""
        header_values = ["Storey", "Type", "Name", "GUID"]
        
        # Collect all QTO keys
        qto_keys_by_type = defaultdict(set)
        for storey_name, types in self.hierarchy.items():
            if self.filter_storey and self.filter_storey != 'All' and storey_name != self.filter_storey:
                continue
            for ifc_type, elements in types.items():
                if self.filter_ifc_type and self.filter_ifc_type != 'All' and ifc_type != self.filter_ifc_type:
                    continue
                for element in elements:
                    if GeometryExtractor.extract_custom_mesh_from_entity(element):
                        qto_props = GeometryExtractor.extract_qto_properties(element, self.model)
                        qto_keys_by_type[ifc_type].update(qto_props.keys())
        
        qto_keys = sorted(set().union(*qto_keys_by_type.values())) if qto_keys_by_type else []
        
        if qto_keys:
            header_values.extend(qto_keys)
        
        # Build table data
        cells_values = [[] for _ in header_values]
        row_colors = []
        current_row = 0
        
        for storey_name, types in self.hierarchy.items():
            if self.filter_storey and self.filter_storey != 'All' and storey_name != self.filter_storey:
                continue
            for ifc_type, elements in types.items():
                if self.filter_ifc_type and self.filter_ifc_type != 'All' and ifc_type != self.filter_ifc_type:
                    continue
                for element in elements:
                    if GeometryExtractor.extract_custom_mesh_from_entity(element):
                        element_name = element.Name or f"{element.is_a()}_{element.GlobalId[:8]}"
                        full_name = f"{storey_name}/{ifc_type}/{element_name}"
                        
                        if full_name in self.visualizer.mesh_dict:
                            cells_values[0].append(storey_name)
                            cells_values[1].append(ifc_type)
                            cells_values[2].append(element_name)
                            cells_values[3].append(element.GlobalId[:8])
                            
                            qto_props = GeometryExtractor.extract_qto_properties(element, self.model)
                            for key in qto_keys:
                                value = qto_props.get(key, "-")
                                cells_values[header_values.index(key)].append(str(value))
                            
                            row_colors.append("#ffffff" if current_row % 2 == 0 else "#f0f0f0")
                            current_row += 1
        
        if not cells_values[0]:
            return go.Figure(data=[go.Table(
                header=dict(values=["Message"], fill_color='#FF5733', font=dict(color='white')),
                cells=dict(values=[["No element matches the filters."]], align='center')
            )])
        
        # Create table
        table = go.Figure(data=[go.Table(
            header=dict(
                values=header_values,
                fill_color='#4CAF50',
                font=dict(color='white', size=12),
                align='left'
            ),
            cells=dict(
                values=cells_values,
                fill_color=[row_colors],
                align='left',
                height=30
            )
        )])
        
        table.update_layout(
            width=800,
            height=400,
            margin=dict(l=0, r=0, t=20, b=0),
            clickmode='event+select'
        )
        
        # Add click handler
        def on_table_click(trace, points, selector):
            if points.point_inds:
                row_index = points.point_inds[0]
                full_name = f"{cells_values[0][row_index]}/{cells_values[1][row_index]}/{cells_values[2][row_index]}"
                self._select_mesh(full_name)
        
        table.data[0].on_click(on_table_click)
        
        return table

    def _update_table(self):
        """Update the table display."""
        with self.table_output:
            self.table_output.clear_output()
            table = self._create_table()
            display(table)

    def _update_viewer(self):
        """Update the 3D viewer display."""
        with self.viewer_output:
            self.viewer_output.clear_output()
            for i, trace in enumerate(self.visualizer.fig.data):
                if trace.name in self.visualizer.visibility:
                    self.visualizer.fig.data[i].visible = self.visualizer.visibility[trace.name]
            display(self.visualizer.fig)

    def _apply_filters(self, b):
        """Apply the selected filters to the visualization."""
        self.filter_storey = self.storey_dropdown.value
        self.filter_ifc_type = self.ifc_type_dropdown.value
        
        print(f"🔍 Applying filters: Storey={self.filter_storey}, IFC Type={self.filter_ifc_type}")
        
        # Update visibility based on filters
        for full_name in self.visualizer.mesh_dict:
            storey, ifc_type, _ = full_name.split('/')
            is_visible = (
                (self.filter_storey == 'All' or storey == self.filter_storey) and
                (self.filter_ifc_type == 'All' or ifc_type == self.filter_ifc_type)
            )
            self.visualizer.visibility[full_name] = is_visible
            self.visualizer.mesh_dict[full_name].visible = is_visible
            
            if full_name in self.all_checkboxes:
                self.all_checkboxes[full_name].value = is_visible
        
        self._update_table()
        self._update_viewer()
        print("✅ 3D view and table updated")

    def _create_visibility_accordion(self):
        """Create the hierarchical visibility control accordion."""
        visibility_accordion = widgets.Accordion(children=[])
        visibility_titles = []
        
        for storey_name, types in self.hierarchy.items():
            if self.filter_storey and self.filter_storey != 'All' and storey_name != self.filter_storey:
                continue
            
            type_accordion = widgets.Accordion(children=[])
            type_titles = []
            
            for ifc_type, elements in types.items():
                if self.filter_ifc_type and self.filter_ifc_type != 'All' and ifc_type != self.filter_ifc_type:
                    continue
                
                element_checkboxes = []
                for element in elements:
                    if GeometryExtractor.extract_custom_mesh_from_entity(element):
                        element_name = element.Name or f"{element.is_a()}_{element.GlobalId[:8]}"
                        full_name = f"{storey_name}/{ifc_type}/{element_name}"
                        
                        if full_name in self.visualizer.mesh_dict:
                            checkbox = widgets.Checkbox(
                                value=self.visualizer.visibility.get(full_name, True),
                                description=element_name,
                                indent=False,
                                layout=widgets.Layout(width='auto')
                            )
                            checkbox.full_name = full_name
                            checkbox.observe(self._on_checkbox_change, names="value")
                            element_checkboxes.append(checkbox)
                            self.all_checkboxes[full_name] = checkbox
                
                if element_checkboxes:
                    select_all_checkbox = widgets.Checkbox(
                        value=True,
                        description=f"Select all ({len(element_checkboxes)} elements)",
                        indent=False,
                        style={'font_weight': 'bold'}
                    )
                    select_all_checkbox.related_checkboxes = element_checkboxes
                    select_all_checkbox.observe(self._on_select_all_change, names="value")
                    
                    type_container = widgets.VBox([
                        select_all_checkbox,
                        widgets.HTML("<hr style='margin: 5px 0;'>"),
                        *element_checkboxes
                    ])
                    
                    type_accordion.children += (type_container,)
                    type_titles.append(f"{ifc_type} ({len(element_checkboxes)})")
            
            if type_accordion.children:
                for i, title in enumerate(type_titles):
                    type_accordion.set_title(i, title)
                visibility_accordion.children += (type_accordion,)
                visibility_titles.append(f"{storey_name} ({len(type_titles)} types)")
        
        for i, title in enumerate(visibility_titles):
            visibility_accordion.set_title(i, title)
        
        return visibility_accordion

    def _on_checkbox_change(self, change):
        """Handle individual checkbox changes."""
        checkbox = change['owner']
        full_name = checkbox.full_name
        is_visible = change['new']
        
        self.visualizer.visibility[full_name] = is_visible
        self.visualizer.mesh_dict[full_name].visible = is_visible
        
        for i, trace in enumerate(self.visualizer.fig.data):
            if trace.name == full_name:
                self.visualizer.fig.data[i].visible = is_visible
                break
        
        self._update_viewer()
        
        if is_visible:
            self._select_mesh(full_name)
        else:
            if self.visualizer.selected_mesh[0] == full_name:
                self._deselect_current()

    def _on_select_all_change(self, change):
        """Handle 'select all' checkbox changes."""
        select_all_checkbox = change['owner']
        new_value = change['new']
        
        for checkbox in select_all_checkbox.related_checkboxes:
            if checkbox.full_name in self.visualizer.mesh_dict:
                checkbox.value = new_value
                self.visualizer.visibility[checkbox.full_name] = new_value
                self.visualizer.mesh_dict[checkbox.full_name].visible = new_value
                
                for i, trace in enumerate(self.visualizer.fig.data):
                    if trace.name == checkbox.full_name:
                        self.visualizer.fig.data[i].visible = new_value
                        break
        
        self._update_viewer()

    def _select_mesh(self, full_name):
        """Select and highlight a mesh, showing its properties."""
        if full_name not in self.visualizer.mesh_dict:
            return
        
        self.visualizer.selected_mesh[0] = full_name
        
        # Highlight selected mesh in yellow
        for i, trace in enumerate(self.visualizer.fig.data):
            color = "#ffff00" if trace.name == full_name else self.visualizer.original_colors[trace.name]
            self.visualizer.fig.data[i].color = color
        
        self._update_viewer()
        
        # Find the element
        element = None
        for storey_name, types in self.hierarchy.items():
            for ifc_type, elements in types.items():
                for elem in elements:
                    element_name = elem.Name or f"{elem.is_a()}_{elem.GlobalId[:8]}"
                    if full_name == f"{storey_name}/{ifc_type}/{element_name}":
                        element = elem
                        break
                if element:
                    break
            if element:
                break
        
        # Display properties
        props_html = "<b>🔍 Selected Object Properties:</b><br>"
        props = self.visualizer.properties[full_name]
        for key, value in props.items():
            props_html += f"<b>{key}:</b> {value}<br>"
        
        # Add PropertySets
        if element and hasattr(element, 'IsDefinedBy'):
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if pset.is_a("IfcPropertySet") and hasattr(pset, 'HasProperties'):
                        props_html += f"<br><b>{pset.Name}:</b><br>"
                        for prop in pset.HasProperties:
                            prop_name = getattr(prop, 'Name', 'Unknown')
                            prop_value = getattr(prop, 'NominalValue', None)
                            value_str = prop_value.wrappedValue if prop_value and hasattr(prop_value, 'wrappedValue') else str(prop_value) if prop_value else 'N/A'
                            props_html += f"<b>{prop_name}:</b> {value_str}<br>"
        
        # Add IfcCovering properties for walls
        if element and (element.is_a("IfcWall") or element.is_a("IfcWallStandardCase")):
            for rel in self.model.by_type("IfcRelCoversBldgElements"):
                if rel.RelatingBuildingElement == element and rel.RelatedCoverings:
                    for covering in rel.RelatedCoverings:
                        if GeometryExtractor.extract_custom_mesh_from_entity(covering):
                            props_html += f"<br><b>IfcCovering Properties ({covering.GlobalId}):</b><br>"
                            if hasattr(covering, 'IsDefinedBy'):
                                for rel_cov in covering.IsDefinedBy:
                                    if rel_cov.is_a("IfcRelDefinesByProperties"):
                                        pset = rel_cov.RelatingPropertyDefinition
                                        if pset.is_a("IfcElementQuantity") and hasattr(pset, 'Name') and pset.Name.startswith("Qto_"):
                                            for qty in pset.Quantities:
                                                qty_name = getattr(qty, 'Name', 'Unknown')
                                                qty_value = None
                                                if qty.is_a('IfcQuantityLength'):
                                                    qty_value = getattr(qty, 'LengthValue', None)
                                                elif qty.is_a('IfcQuantityArea'):
                                                    qty_value = getattr(qty, 'AreaValue', None)
                                                elif qty.is_a('IfcQuantityVolume'):
                                                    qty_value = getattr(qty, 'VolumeValue', None)
                                                elif qty.is_a('IfcQuantityCount'):
                                                    qty_value = getattr(qty, 'CountValue', None)
                                                elif qty.is_a('IfcQuantityWeight'):
                                                    qty_value = getattr(qty, 'WeightValue', None)
                                                value = qty_value if qty_value is not None else 'N/A'
                                                props_html += f"<b>{qty_name}_Covering:</b> {value}<br>"
        
        self.properties_panel.value = props_html

    def _deselect_current(self):
        """Deselect the currently selected mesh."""
        self.visualizer.selected_mesh[0] = None
        
        for i, trace in enumerate(self.visualizer.fig.data):
            self.visualizer.fig.data[i].color = self.visualizer.original_colors[trace.name]
        
        self._update_viewer()
        self.properties_panel.value = "<b>🔍 Properties:</b><br>Select an object"

    def _expand_all_accordions(self, accordion):
        """Recursively expand all accordions."""
        for i in range(len(accordion.children)):
            accordion.selected_index = i
            child = accordion.children[i]
            if hasattr(child, 'children') and isinstance(child.children[0], widgets.Accordion):
                self._expand_all_accordions(child.children[0])

    def _collapse_all_accordions(self, accordion):
        """Recursively collapse all accordions."""
        accordion.selected_index = None
        for child in accordion.children:
            if hasattr(child, 'children'):
                for subchild in child.children:
                    if isinstance(subchild, widgets.Accordion):
                        subchild.selected_index = None
