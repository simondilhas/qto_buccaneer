import os
import shutil

# Source base where all building folders are
SRC_BASE = "projects/Seefeld__private/buildings"  # <-- change to your actual source folder
DST_BASE = os.path.join("streamlit_app", "buildings")

# Find all building folders in the source
building_names = [name for name in os.listdir(SRC_BASE) if os.path.isdir(os.path.join(SRC_BASE, name))]

for building in building_names:
    src_building = os.path.join(SRC_BASE, building)
    dst_building = os.path.join(DST_BASE, building)

    # --- Copy metrics Excel file(s) ---
    src_metrics_dir = os.path.join(src_building, "07_metrics")
    dst_metrics_dir = os.path.join(dst_building, "07_metrics")
    if os.path.isdir(src_metrics_dir):
        os.makedirs(dst_metrics_dir, exist_ok=True)
        for file in os.listdir(src_metrics_dir):
            if file.endswith(('.xlsx', '.xls')):
                shutil.copy2(os.path.join(src_metrics_dir, file), os.path.join(dst_metrics_dir, file))
                print(f"Copied {file} to {dst_metrics_dir}")

    # --- Copy graph folder ---
    src_graph_dir = os.path.join(src_building, "11_abstractbim_plots")
    dst_graph_dir = os.path.join(dst_building, "11_abstractbim_plots")
    if os.path.isdir(src_graph_dir):
        if os.path.exists(dst_graph_dir):
            shutil.rmtree(dst_graph_dir)
        shutil.copytree(src_graph_dir, dst_graph_dir)
        print(f"Copied {src_graph_dir} -> {dst_graph_dir}")

    # --- Copy check folder ---
    for check_folder in ["09_building_inside_envelope", "09_check_building_inside_envelop"]:
        src_check_dir = os.path.join(src_building, check_folder)
        dst_check_dir = os.path.join(dst_building, check_folder)
        if os.path.isdir(src_check_dir):
            print(f"Contents of {src_check_dir}: {os.listdir(src_check_dir)}")
            if os.path.exists(dst_check_dir):
                shutil.rmtree(dst_check_dir)
            shutil.copytree(src_check_dir, dst_check_dir)
            print(f"Copied {src_check_dir} -> {dst_check_dir}")
        else:
            print(f"Check folder not found for {building}: {src_check_dir}")