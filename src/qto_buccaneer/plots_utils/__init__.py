"""
Plotting utilities for QTO Buccaneer.

This package provides tools for visualizing IFC models and quantity takeoff results:

### Core Features

- Floorplan Generation
  - Create 2D floor plans from IFC models
  - Customize visualization styles
  - Support for different element types

- 3D Visualization
  - Generate 3D views of IFC models
  - Customize camera angles and perspectives
  - Highlight specific elements or metrics

- Metric Visualization
  - Create charts and graphs for quantity data
  - Compare metrics across different views
  - Generate visual reports

### Usage

```python
from qto_buccaneer.plots_utils import load_plot_config, create_single_plot

# Load plot configuration
config = load_plot_config("path/to/plot_config.yaml")

# Create a plot
plot = create_single_plot(
    geometry_dir="path/to/geometry_json",
    properties_path="path/to/metadata.json",
    config=config
)
```

### Configuration

Plot configurations are defined in YAML files and support:
- Custom colors and styles
- Element filtering
- View settings
- Output formats
"""

from qto_buccaneer.plots_utils.three_d import (
    load_plot_config,
    create_single_plot,
)

__all__ = [
    'load_plot_config',
    'create_single_plot',
]
