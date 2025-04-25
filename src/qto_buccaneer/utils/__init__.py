"""
Utility modules for QTO Buccaneer.

This package contains helper functions and classes for working with IFC models and performing quantity takeoffs:

### Core Utilities

- ifc_loader.py: IFC file loading and manipulation
  - Load and parse IFC files
  - Extract geometry and properties
  - Handle IFC model navigation

- qto_calculator.py: Quantity calculations
  - Perform quantity takeoffs
  - Calculate areas, volumes, and other metrics
  - Support custom calculation rules

- config_loader.py: Configuration handling
  - Load and validate YAML configurations
  - Manage project settings
  - Handle metric definitions

- ifc_json_loader.py: JSON-based IFC data handling
  - Convert IFC to structured JSON
  - Handle geometry and metadata
  - Support for floorplan generation

- plots_utils.py: Plotting and visualization
  - Parse filter strings
  - Apply layout settings
  - Support for element filtering

### Usage

```python
from qto_buccaneer.utils import IfcLoader, QtoCalculator

# Load IFC model
loader = IfcLoader("path/to/model.ifc")
model = loader.load()

# Calculate quantities
calculator = QtoCalculator(model)
quantities = calculator.calculate_quantities()
```
"""

# Public API
from .ifc_loader import IfcLoader
from .qto_calculator import QtoCalculator
from .config_loader import load_config
from .ifc_json_loader import IfcJsonLoader

# Internal functions (not exposed)
from .plots_utils import parse_filter as _parse_filter
from .plots_utils import element_matches_conditions as _element_matches_conditions
from .plots_utils import apply_layout_settings as _apply_layout_settings

__all__ = [
    'IfcLoader',
    'QtoCalculator',
    'load_config',
    'IfcJsonLoader'
]