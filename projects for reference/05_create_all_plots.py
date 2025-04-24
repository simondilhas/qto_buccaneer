from qto_buccaneer.visualization.all_plots import create_all_plots
import os
import yaml

create_all_plots(
    geometry_dir='projects/001_example_project__public/output/04_json_geometry (optional)',
    properties_path='projects/001_example_project__public/output/04_json_geometry (optional)/metadata.json',
    config_path='src/qto_buccaneer/configs/plot_config.yaml',
    output_dir='projects/001_example_project__public/output/05_plots (optional)'
)