from qto_buccaneer.visualization import create_floorplan_per_storey

if __name__ == "__main__":
    create_floorplan_per_storey(
        space_geometry_path='examples/ifc_json_data/geometry/IfcSpace_geometry.json',
        door_geometry_path='examples/ifc_json_data/geometry/IfcDoor_geometry.json',
        properties_path='examples/ifc_json_data/metadata/test_metadata.json',
        config_path='src/qto_buccaneer/configs/plot_config.yaml',
        output_dir='output/visualizations'
    )

