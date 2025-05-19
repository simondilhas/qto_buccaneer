"""
QTO Buccaneer - Quantity Takeoff tools for data-savvy BIM rebels.

A Python-powered toolkit for exploring, extracting, and calculating quantities from IFC models.
Built for architects, engineers, and construction pros who know their way around Excel more than Python.

### Main Features

- Calculate project-wide metrics based on your own definitions
- Calculate metrics per room or space
- Benchmark different projects to spot trends and outliers
- Export results to Excel and other report formats used by your team
- Create beautiful reports with plans, making information visible and manageable
- Define metric logic using a user-friendly YAML config file — no need to write code
- Enrich and clean up IFC files more easily than working directly with raw ifcopenshell
- Repair IFC Models based on rules
- Build up project specific workflows and apply the same rules consecutive to the models

### Package Structure

- metrics: Core metrics calculation functionality
- enrich: IFC model enrichment and data cleaning
- reports: Export and reporting utilities
- plots: Visualization and plotting tools
- utils: Helper functions for IFC handling and quantity calculations
- configs: Configuration files and settings
- repairs: IFC model repair functionality

### Designed for IFC, Optimized for abstractBIM Data

This library works with any well-structured IFC file, but it shines brightest when used with clean, consistent data.
The toolkit is optimized for abstractBIM Data in the presets, providing:

- Consistent naming
- Predictable geometry
- Clean data structure

Which means less time debugging, more time automating.

While you can use raw IFC + ifcopenshell, the toolkit includes helpers and examples to ease the pain
of working with less structured models.

### Quick Start

```python
from qto_buccaneer.metrics import calculate_all_metrics
import yaml

# Load config
with open("path/to/metrics_config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Calculate metrics
metrics_df = calculate_all_metrics(
    config=config,
    ifc_path="path/to/your/model.ifc"
)
```

For more examples and detailed usage, check the README.md file or visit:
https://simondilhas.github.io/qto_buccaneer/qto_buccaneer/index.html
"""

from ._version import __version__

__version__ = __version__
__author__ = "Simon Dilhas"

# Comment out imports until we verify what actually exists
# from .metrics import calculate_all_metrics

# The following code block is commented out as it's not provided in the original file
# from .utils import load_ifc  # Uncomment if load_ifc exists in utils.py
# from .reports import export_to_excel  # Uncomment if export_to_excel exists in reports.py 

# Expose utils modules
from .utils.ifc_loader import IfcLoader
from .utils.ifc_qto_calculator import QtoCalculator