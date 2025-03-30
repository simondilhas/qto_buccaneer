# Getting Started

## Installation

```bash
git clone https://github.com/yourusername/qto-buccaneer.git
cd qto-buccaneer
pip install -r requirements.txt
```

## Quick Start

```python
from qto_calculator import QtoCalculator

# Initialize the calculator
calculator = QtoCalculator(loader)

# Get basic measurements
floor_area = calculator.calculate_space_interior_floor_area()
wall_area = calculator.calculate_walls_interior_net_side_area()
building_volume = calculator.calculate_space_interior_volume()
```

## Basic Concepts

### Measurements
- All lengths are in meters (m)
- Areas are in square meters (m²)
- Volumes are in cubic meters (m³)

### Filters
Filters help you select specific elements:

```python
# Get interior walls
interior_walls = calculator.calculate_walls_interior_net_side_area(
    include_filter={"Pset_WallCommon.IsExternal": False}
)
``` 