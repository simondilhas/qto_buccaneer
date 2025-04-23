from qto_buccaneer.visualize_floorplan import create_floorplan_per_storey

if __name__ == "__main__":
    create_floorplan_per_storey(
        geometry_dir='examples/ifc_json_data/geometry',
        properties_path='examples/ifc_json_data/metadata/test_metadata.json',
        config_path='src/qto_buccaneer/configs/plot_config.yaml',
        output_dir='output/visualizations',
        plot_name='floor_layout_by_name'
    ) 