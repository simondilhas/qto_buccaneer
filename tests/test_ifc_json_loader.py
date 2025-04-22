import pytest
from qto_buccaneer.utils.ifc_json_loader import IfcJsonLoader

def test_ifc_json_loader_initialization():
    """Test the initialization of IfcJsonLoader with sample data."""
    geometry_data = [
        {
            "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
            "ifc_type": "IfcSpace",
            "vertices": [
                [7.125, 7.75, -3.4],
                [7.125, 7.75, -0.4],
                [0.0, 7.75, -0.4],
                [0.0, 7.75, -3.4]
            ],
            "faces": [
                [1, 0, 3],
                [2, 1, 3]
            ]
        },
        {
            "ifc_global_id": "1cTPue28D2tej2wdtN2O_a",
            "ifc_type": "IfcSpace",
            "vertices": [
                [7.475, 8.1, -3.4],
                [7.475, 8.1, 0.0],
                [-0.35, 8.1, 0.0],
                [-0.35, 8.1, -3.4]
            ],
            "faces": [
                [1, 0, 3],
                [2, 1, 3]
            ]
        }
    ]
    
    properties_data = {
        "elements": {
            "1": {
                "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
                "type": "IfcSpace",
                "name": "SGR",
                "parent_id": "2",
                "properties": {
                    "PredefinedType": "INTERNAL",
                    "ePset_abstractBIM.SpacesLongName": "SGR",
                    "ePset_abstractBIM.SpacesName": "SGR"
                }
            },
            "2": {
                "ifc_global_id": "2YmaQ8oXj9A8Fo5t$6NGj7",
                "type": "IfcBuildingStorey",
                "name": "UG"
            },
            "3": {
                "ifc_global_id": "1cTPue28D2tej2wdtN2O_a",
                "type": "IfcSpace",
                "name": "CORRIDOR",
                "parent_id": "2",
                "properties": {
                    "PredefinedType": "INTERNAL",
                    "ePset_abstractBIM.SpacesLongName": "CORRIDOR",
                    "ePset_abstractBIM.SpacesName": "CORRIDOR"
                }
            }
        },
        "indexes": {
            "by_type": {
                "IfcSpace": [1, 3],
                "IfcBuildingStorey": [2]
            }
        },
        "global_id_to_id": {
            "1QkKxMqDv7nuSnClC0HTpb": 1,
            "2YmaQ8oXj9A8Fo5t$6NGj7": 2,
            "1cTPue28D2tej2wdtN2O_a": 3
        }
    }
    
    loader = IfcJsonLoader(geometry_data, properties_data)
    
    assert loader.geometry == geometry_data
    assert loader.properties == properties_data
    assert "1QkKxMqDv7nuSnClC0HTpb" in loader.geometry_index
    assert "1cTPue28D2tej2wdtN2O_a" in loader.geometry_index
    assert "1QkKxMqDv7nuSnClC0HTpb" in loader.properties_index
    assert "1cTPue28D2tej2wdtN2O_a" in loader.properties_index
    assert loader.by_type_index["IfcSpace"] == [1, 3]
    assert loader.global_id_to_id["1QkKxMqDv7nuSnClC0HTpb"] == 1

def test_get_spaces_in_storey():
    """Test getting spaces in a specific storey."""
    geometry_data = [
        {
            "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
            "ifc_type": "IfcSpace",
            "vertices": [[7.125, 7.75, -3.4], [7.125, 7.75, -0.4], [0.0, 7.75, -0.4], [0.0, 7.75, -3.4]],
            "faces": [[1, 0, 3], [2, 1, 3]]
        },
        {
            "ifc_global_id": "1cTPue28D2tej2wdtN2O_a",
            "ifc_type": "IfcSpace",
            "vertices": [[7.475, 8.1, -3.4], [7.475, 8.1, 0.0], [-0.35, 8.1, 0.0], [-0.35, 8.1, -3.4]],
            "faces": [[1, 0, 3], [2, 1, 3]]
        },
        {
            "ifc_global_id": "1Lh9kPvIP9K8x1cSw46NVh",
            "ifc_type": "IfcSpace",
            "vertices": [[7.475, 8.1, -3.9], [7.475, 8.1, -3.4], [-0.35, 8.1, -3.4], [-0.35, 8.1, -3.9]],
            "faces": [[1, 0, 3], [2, 1, 3]]
        }
    ]
    
    properties_data = {
        "elements": {
            "1": {
                "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
                "type": "IfcSpace",
                "parent_id": "4",
                "properties": {"PredefinedType": "INTERNAL"}
            },
            "2": {
                "ifc_global_id": "1cTPue28D2tej2wdtN2O_a",
                "type": "IfcSpace",
                "parent_id": "4",
                "properties": {"PredefinedType": "INTERNAL"}
            },
            "3": {
                "ifc_global_id": "1Lh9kPvIP9K8x1cSw46NVh",
                "type": "IfcSpace",
                "parent_id": "5",
                "properties": {"PredefinedType": "INTERNAL"}
            },
            "4": {
                "ifc_global_id": "2YmaQ8oXj9A8Fo5t$6NGj7",
                "type": "IfcBuildingStorey",
                "name": "UG"
            },
            "5": {
                "ifc_global_id": "3YmaQ8oXj9A8Fo5t$6NGj8",
                "type": "IfcBuildingStorey",
                "name": "EG"
            }
        },
        "indexes": {
            "by_type": {
                "IfcSpace": [1, 2, 3],
                "IfcBuildingStorey": [4, 5]
            }
        },
        "global_id_to_id": {
            "1QkKxMqDv7nuSnClC0HTpb": 1,
            "1cTPue28D2tej2wdtN2O_a": 2,
            "1Lh9kPvIP9K8x1cSw46NVh": 3,
            "2YmaQ8oXj9A8Fo5t$6NGj7": 4,
            "3YmaQ8oXj9A8Fo5t$6NGj8": 5
        }
    }
    
    loader = IfcJsonLoader(geometry_data, properties_data)
    
    # Test getting spaces from UG
    ug_spaces = loader.get_spaces_in_storey("UG")
    assert len(ug_spaces) == 2
    assert "1QkKxMqDv7nuSnClC0HTpb" in ug_spaces
    assert "1cTPue28D2tej2wdtN2O_a" in ug_spaces
    
    # Test getting spaces from EG
    eg_spaces = loader.get_spaces_in_storey("EG")
    assert len(eg_spaces) == 1
    assert "1Lh9kPvIP9K8x1cSw46NVh" in eg_spaces
    
    # Test getting spaces from non-existent storey
    no_spaces = loader.get_spaces_in_storey("OG")
    assert len(no_spaces) == 0

def test_get_geometry():
    """Test getting geometry for a specific GUID."""
    geometry_data = [
        {
            "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
            "ifc_type": "IfcSpace",
            "vertices": [[7.125, 7.75, -3.4], [7.125, 7.75, -0.4], [0.0, 7.75, -0.4], [0.0, 7.75, -3.4]],
            "faces": [[1, 0, 3], [2, 1, 3]]
        },
        {
            "ifc_global_id": "1cTPue28D2tej2wdtN2O_a",
            "ifc_type": "IfcSpace",
            "vertices": [[7.475, 8.1, -3.4], [7.475, 8.1, 0.0], [-0.35, 8.1, 0.0], [-0.35, 8.1, -3.4]],
            "faces": [[1, 0, 3], [2, 1, 3]]
        }
    ]
    
    properties_data = {
        "elements": {
            "1": {
                "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
                "type": "IfcSpace",
                "parent_id": "3"
            },
            "2": {
                "ifc_global_id": "1cTPue28D2tej2wdtN2O_a",
                "type": "IfcSpace",
                "parent_id": "3"
            },
            "3": {
                "ifc_global_id": "2YmaQ8oXj9A8Fo5t$6NGj7",
                "type": "IfcBuildingStorey",
                "name": "UG"
            }
        },
        "indexes": {
            "by_type": {
                "IfcSpace": [1, 2],
                "IfcBuildingStorey": [3]
            }
        },
        "global_id_to_id": {
            "1QkKxMqDv7nuSnClC0HTpb": 1,
            "1cTPue28D2tej2wdtN2O_a": 2,
            "2YmaQ8oXj9A8Fo5t$6NGj7": 3
        }
    }
    
    loader = IfcJsonLoader(geometry_data, properties_data)
    
    # Test getting existing geometry
    space1_geom = loader.get_geometry("1QkKxMqDv7nuSnClC0HTpb")
    assert space1_geom == geometry_data[0]
    
    # Test getting non-existent geometry
    no_geom = loader.get_geometry("nonexistent")
    assert no_geom is None

def test_get_properties():
    """Test getting properties for a specific GUID."""
    geometry_data = [
        {
            "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
            "ifc_type": "IfcSpace",
            "vertices": [[7.125, 7.75, -3.4], [7.125, 7.75, -0.4], [0.0, 7.75, -0.4], [0.0, 7.75, -3.4]],
            "faces": [[1, 0, 3], [2, 1, 3]]
        }
    ]
    
    properties_data = {
        "elements": {
            "1": {
                "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
                "type": "IfcSpace",
                "parent_id": "2",
                "properties": {
                    "PredefinedType": "INTERNAL",
                    "ePset_abstractBIM.SpacesLongName": "SGR"
                }
            },
            "2": {
                "ifc_global_id": "2YmaQ8oXj9A8Fo5t$6NGj7",
                "type": "IfcBuildingStorey",
                "name": "UG"
            }
        },
        "indexes": {
            "by_type": {
                "IfcSpace": [1],
                "IfcBuildingStorey": [2]
            }
        },
        "global_id_to_id": {
            "1QkKxMqDv7nuSnClC0HTpb": 1,
            "2YmaQ8oXj9A8Fo5t$6NGj7": 2
        }
    }
    
    loader = IfcJsonLoader(geometry_data, properties_data)
    
    # Test getting existing properties
    space1_props = loader.get_properties("1QkKxMqDv7nuSnClC0HTpb")
    assert space1_props == properties_data["elements"]["1"]
    
    # Test getting non-existent properties
    no_props = loader.get_properties("nonexistent")
    assert no_props is None

def test_get_storey_for_space():
    """Test getting storey name for a specific space."""
    geometry_data = [
        {
            "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
            "ifc_type": "IfcSpace",
            "vertices": [[7.125, 7.75, -3.4], [7.125, 7.75, -0.4], [0.0, 7.75, -0.4], [0.0, 7.75, -3.4]],
            "faces": [[1, 0, 3], [2, 1, 3]]
        }
    ]
    
    properties_data = {
        "elements": {
            "1": {
                "ifc_global_id": "1QkKxMqDv7nuSnClC0HTpb",
                "type": "IfcSpace",
                "parent_id": "2",
                "properties": {"PredefinedType": "INTERNAL"}
            },
            "2": {
                "ifc_global_id": "2YmaQ8oXj9A8Fo5t$6NGj7",
                "type": "IfcBuildingStorey",
                "name": "UG"
            }
        },
        "indexes": {
            "by_type": {
                "IfcSpace": [1],
                "IfcBuildingStorey": [2]
            }
        },
        "global_id_to_id": {
            "1QkKxMqDv7nuSnClC0HTpb": 1,
            "2YmaQ8oXj9A8Fo5t$6NGj7": 2
        }
    }
    
    loader = IfcJsonLoader(geometry_data, properties_data)
    
    # Test getting storey for existing space
    storey_name = loader.get_storey_for_space("1QkKxMqDv7nuSnClC0HTpb")
    assert storey_name == "UG"
    
    # Test getting storey for non-existent space
    no_storey = loader.get_storey_for_space("nonexistent")
    assert no_storey is None 