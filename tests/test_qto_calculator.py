import pytest
import yaml
from src.qto_buccaneer.utils.ifc_loader import IfcLoader
from src.qto_buccaneer.utils.qto_calculator import QtoCalculator

# Constants for test data
TEST_IFC_PATH = "tes_model_1.ifc"
TEST_DATA_PATH = "tests/test_data.yaml"

@pytest.fixture
def test_data():
    """Load expected values from YAML file"""
    with open(TEST_DATA_PATH, 'r') as f:
        return yaml.safe_load(f)

@pytest.fixture
def qto():
    """Initialize QtoCalculator with test IFC file"""
    loader = IfcLoader(TEST_IFC_PATH)
    return QtoCalculator(loader)

def test_sum_quantity_basic(qto, test_data):
    """Test summing a quantity from elements using a known quantity set and name."""
    elements = qto.loader.get_elements(ifc_entity="IfcSpace")
    total = qto.sum_quantity(elements, "Qto_SpaceBaseQuantities", "NetFloorArea")
    expected = test_data["sum_quantity"]["NetFloorArea"]
    assert pytest.approx(total, 0.01) == expected

def test_calculate_quantity_area_default(qto, test_data):
    """Test default area calculation without filters."""
    result = qto.calculate_quantity(quantity_type="area")
    expected = test_data["calculate_quantity"]["default_area"]
    assert pytest.approx(result, 0.01) == expected

def test_calculate_quantity_area_with_filter(qto, test_data):
    """Test filtered area calculation (e.g. only GrossArea-named spaces)."""
    include_filter = {"Name": ["GrossArea", "Main Hall"]}
    result = qto.calculate_quantity(
        quantity_type="area",
        include_filter=include_filter,
        include_filter_logic="OR"
    )
    expected = test_data["calculate_quantity"]["filtered_area"]
    assert pytest.approx(result, 0.01) == expected

def test_calculate_quantity_area_with_subtraction(qto, test_data):
    """Test area calculation with subtraction filter (e.g., subtract voids)."""
    result = qto.calculate_quantity(
        quantity_type="area",
        include_filter={"Name": "GrossArea"},
        subtract_filter={"Name": "Void"}
    )
    expected = test_data["calculate_quantity"]["subtracted_area"]
    assert pytest.approx(result, 0.01) == expected

def test_get_elements_by_space(qto, test_data):
    """Test grouped element areas by space."""
    result = qto._get_elements_by_space(
        ifc_entity="IfcCovering",
        grouping_attribute="LongName",
        room_reference_attribute_guid="ePset_abstractBIM.Spaces",
        include_filter={"Name": "Floor Covering"}
    )
    expected = test_data["elements_by_space"]
    for room_name, area in expected.items():
        assert pytest.approx(result.get(room_name, 0.0), 0.01) == area

