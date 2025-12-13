"""
IFC Viewer Module for qto_buccaneer
Main entry point for interactive 3D visualization of IFC models in Jupyter/Colab notebooks.
"""

import traceback
from pathlib import Path
from .ifc_viewer_loader import IFCDownloader
from .ifc_viewer_geometry import GeometryExtractor
from .ifc_viewer_hierarchy import HierarchicalStructure
from .ifc_viewer_visualizer import Visualizer3D


def visualize_ifc(
    ifc_source,
    color_config_path=None,
    show_ui=True,
    verbose=False
):
    """
    Visualize an IFC model in 3D with optional color configuration.
    
    This is the main entry point for the IFC viewer. It handles loading,
    processing, and displaying IFC models with minimal code required.
    
    Parameters:
    -----------
    ifc_source : str
        Path to IFC file (local path or URL)
    color_config_path : str, optional
        Path to YAML color configuration file
        Default: uses built-in abstractBIM_plots_config.yaml
    show_ui : bool, default=True
        Whether to show the interactive UI (filters, table, properties)
        If False, only shows the 3D viewer
    verbose : bool, default=False
        Whether to print detailed processing information
        
    Returns:
    --------
    tuple
        (visualizer, hierarchy, ui) if show_ui=True
        (visualizer, hierarchy) if show_ui=False
        
    Example:
    --------
    ```python
    # Simple usage with URL
    from qto_buccaneer import visualize_ifc
    
    url = "https://example.com/model.ifc"
    visualize_ifc(url)
    
    # With custom color config
    visualize_ifc(
        "path/to/model.ifc",
        color_config_path="path/to/colors.yaml"
    )
    
    # Just 3D view, no UI
    viz, hier = visualize_ifc(
        "model.ifc",
        show_ui=False
    )
    ```
    """
    try:
        # Determine color config path
        if color_config_path is None:
            # Use default config from package
            package_dir = Path(__file__).parent
            color_config_path = package_dir / "configs" / "abstractBIM_plots_config.yaml"
            if not color_config_path.exists():
                color_config_path = None
        
        if verbose:
            print(f"🚀 Starting IFC file processing...")
            print(f"📂 Source: {ifc_source}")
            if color_config_path:
                print(f"🎨 Color config: {color_config_path}")
            print("-" * 80)
        
        # Load IFC model
        model = IFCDownloader.download_and_load(ifc_source)
        
        # Build hierarchy
        hierarchy_builder = HierarchicalStructure(model)
        hierarchy = hierarchy_builder.get_hierarchy()
        
        # Initialize geometry extractor with colors
        geometry_extractor = GeometryExtractor(color_config_path)
        
        # Initialize visualizer
        visualizer = Visualizer3D(geometry_extractor)
        
        if verbose:
            print("\n🔍 Extracting and processing geometry and QTO properties...")
        
        processed_count = 0
        total_elements = 0
        
        for storey_name, types in hierarchy.items():
            for ifc_type, elements in types.items():
                total_elements += len(elements)
                for element in elements:
                    mesh_json = GeometryExtractor.extract_custom_mesh_from_entity(element)
                    if mesh_json:
                        qto_props = GeometryExtractor.extract_qto_properties(element, model)
                        hierarchy_path = f"{storey_name}/{ifc_type}"
                        visualizer.add_mesh_from_element(element, mesh_json, hierarchy_path, qto_props)
                        processed_count += 1
                    elif verbose:
                        print(f"⚠️ Element {element.GlobalId} ({element.is_a()}) does not have Custom_Mesh")
        
        if processed_count == 0:
            print("⚠️ No elements with Custom_Mesh properties found.")
            print("🔍 Check that the IFC file contains Pset_CustomGeometry properties with Custom_Mesh")
            return None
        
        if verbose:
            print(f"📊 Total elements in structure: {total_elements}")
            print(f"📊 Elements processed with geometry: {processed_count}")
            print(f"✅ {processed_count} elements with geometry processed!")
        
        visualizer.configure_layout()
        
        if show_ui:
            # Import UI module only if needed (requires ipywidgets)
            try:
                from .ifc_viewer_ui import HierarchicalTableUI
                ui = HierarchicalTableUI(hierarchy, visualizer, model)
                ui_widget = ui.create_ui()
                
                from IPython.display import display
                display(ui_widget)
                
                if verbose:
                    print("\n✅ Full visualization! Use the table for selection and the panel for visibility.")
                
                return visualizer, hierarchy, ui
            except ImportError as e:
                print(f"⚠️ ipywidgets not available. Showing 3D view only.")
                if verbose:
                    print(f"   Error: {e}")
                    print("   Install with: !pip install ipywidgets")
                from IPython.display import display
                display(visualizer.fig)
                return visualizer, hierarchy
            except Exception as e:
                print(f"⚠️ Error loading UI. Showing 3D view only.")
                if verbose:
                    print(f"   Error: {e}")
                    import traceback
                    print(traceback.format_exc())
                from IPython.display import display
                display(visualizer.fig)
                return visualizer, hierarchy
        else:
            # Just show the 3D figure
            from IPython.display import display
            display(visualizer.fig)
            return visualizer, hierarchy
            
    except Exception as e:
        print(f"❌ General error: {e}")
        if verbose:
            print(traceback.format_exc())
        return None
