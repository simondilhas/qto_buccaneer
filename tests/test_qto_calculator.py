import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.qto_buccaneer.utils.ifc_loader import IfcLoader
from src.qto_buccaneer.qto_calculator import QtoCalculator

@pytest.fixture
def qto():
    loader = IfcLoader("examples/Mustermodell V1_abstractBIM.ifc")
    return QtoCalculator(loader)

def test_gross_floor_area(qto):
    assert pytest.approx(qto.calculate_gross_floor_area()) == 206.03735
    assert pytest.approx(qto.calculate_gross_floor_area(subtract_filter={"LongName": "LUF"})) == 194.41235

def test_building_volume(qto):
    assert pytest.approx(qto.calculate_gross_floor_volume()) == 710.208555
    assert pytest.approx(qto.calculate_gross_floor_volume(subtract_filter={"LongName": "LUF"})) == 675.333555

def test_coverings(qto):
    assert pytest.approx(qto.calculate_coverings_exterior_area()) == 1010.5960740101783
    assert pytest.approx(qto.calculate_coverings_interior_area()) == 755.3379500000003

def test_windows(qto):
    assert pytest.approx(qto.calculate_windows_exterior_area()) == 6.110200000000002
    assert pytest.approx(qto.calculate_windows_interior_area()) == 0.0

def test_doors(qto):
    assert pytest.approx(qto.calculate_doors_exterior_area()) == 2.1
    assert pytest.approx(qto.calculate_doors_interior_area()) == 0.0

def test_space_measurements(qto):
    assert pytest.approx(qto.calculate_space_interior_floor_area()) == 156.094
    assert pytest.approx(qto.calculate_space_interior_volume()) == 512.4601
    assert pytest.approx(qto.calculate_space_exterior_area()) == 321.671368

def test_slab_measurements(qto):
    assert pytest.approx(qto.calculate_slab_balcony_area()) == 32.84735
    assert pytest.approx(qto.calculate_slab_interior_area()) == 137.554866
    assert pytest.approx(qto.calculate_roof_area()) == 73.79485
    assert pytest.approx(qto.calculate_base_slab_area()) == 73.79485

def test_wall_measurements(qto):
    assert pytest.approx(qto.calculate_walls_exterior_net_side_area()) == 292.40974
    assert pytest.approx(qto.calculate_walls_interior_net_side_area()) == 94.47306989301853
    assert pytest.approx(qto.calculate_walls_interior_structural_area()) == 94.47306989301853

def test_room_based_calculations(qto):
    expected_wall_coverings = {
        'SGR': 89.19,
        'GSA': 128.14690000000002,
        'TRH': 100.0458,
        'LUF': 32.205,
        'WCH': 38.94,
        'WCD': 38.94,
        'RRG': 38.94
    }
    assert qto.create_wall_coverings_by_room() == expected_wall_coverings

    expected_windows = {
        '021YoEi1HD9eSoSLT0LMfy': 3.0551000000000004,
        '2ky6TqzMD7gwJbHxE3Kcxy': 3.0551000000000013
    }
    assert qto.create_windows_by_room() == expected_windows

    expected_doors = {'2lk8ATQRL3YhM35IFLYXiz': 2.1}
    assert qto.create_doors_by_room() == expected_doors

# Filter logic tests
def test_filter_logic(qto):
    # Test AND logic
    area_and = qto.calculate_space_interior_floor_area(
        include_filter={"PredefinedType": "GFA", "Name": "NetFloorArea"},
        include_filter_logic="AND"
    )
    
    # Test OR logic
    area_or = qto.calculate_space_interior_floor_area(
        include_filter={"PredefinedType": "INTERNAL", "Name": "NetFloorArea"},
        include_filter_logic="OR"
    )
    
    assert area_and < area_or

def test_multiple_filters(qto):
    # Test with both include and subtract filters
    area = qto.calculate_gross_floor_area(
        include_filter={"PredefinedType": "GFA"},
        subtract_filter={"LongName": ["LUF", "Void"]}
    )
    assert pytest.approx(area) == 194.41235


def test_invalid_filters(qto):
    # Test with non-existent property
    area = qto.calculate_gross_floor_area(
        include_filter={"NonExistentProperty": "Value"}
    )
    assert pytest.approx(area) == 0

# Specific calculation tests
def test_wall_thickness_filtering(qto):
    # Test filtering walls by thickness
    thick_walls = qto.calculate_walls_interior_structural_area(
        include_filter={
            "Pset_WallCommon.IsExternal": False,
            "Qto_WallBaseQuantities.Width": (">", 0.2)
        }
    )
    thin_walls = qto.calculate_walls_interior_structural_area(
        include_filter={
            "Pset_WallCommon.IsExternal": False,
            "Qto_WallBaseQuantities.Width": ("<", 0.2)
        }
    )
    assert thick_walls != thin_walls


# Performance test (optional)
@pytest.mark.skip(reason="Performance test, run manually")
def test_performance_large_calculation(qto):
    import time
    start = time.time()
    
    # Run multiple calculationsdef test_quantity_sum_helper(qto):
    # Test the internal sum_quantity method
    spaces = qto.loader.get_elements(ifc_entity="IfcSpace")
    total = qto.sum_quantity(
        spaces, 
        "Qto_SpaceBaseQuantities",
        "NetFloorArea"
    )
    assert pytest.approx(total) > 0

    qto.calculate_gross_floor_area()
    qto.calculate_gross_floor_volume()
    qto.calculate_walls_exterior_net_side_area()
    qto.create_wall_coverings_by_room()
    
    duration = time.time() - start
    assert duration < 5.0  # Should complete within 5 seconds

# Comparison tests
def test_area_relationships(qto):
    # Test logical relationships between different areas
    gross_area = qto.calculate_gross_floor_area()
    net_area = qto.calculate_space_interior_floor_area()
    assert gross_area > net_area

    exterior_walls = qto.calculate_walls_exterior_net_side_area()
    interior_walls = qto.calculate_walls_interior_net_side_area()
    assert exterior_walls > interior_walls 