"""
This package provides tools for exploring, extracting, and calculating quantities 
from IFC models. It's designed for construction, architecture, and BIM professionals 
who need automated quantity takeoffs.

### Main Components

- metrics: Core metrics calculation functionality
- enrich: Enrich and clean up IFC files—friendlier than raw ifcopenshell
- reports: Export and reporting utilities
- utils: Helper functions for IFC handling and quantity calculations
- configs: Configuration files and settings

### With this toolkit, you can

- Calculate project-wide metrics based on your definitions
- Calculate metrics per room or space
- Calculate metrics and group them by your own custom definitions
- Enrich and clean up IFC files—friendlier than raw ifcopenshell
- Export results to Excel and other report formats
- Define metric logic using a YAML config file, instead of having to deal with code or clicking through the UI

**Designed for IFC, optimized for abstractBIM Data**

This library works with any well-structured IFC file, but it shines brightest when used with clean, consistent data.
And that's why it's optimized for abstractBIM Data in the presets. 

Because abstractBIM gives you:

- Consistent naming
- Predictable geometry
- Clean data structure

Which means less time debugging, more time automating.

Yes, you can still use raw IFC + ifcopenshell, but you'll want to be comfortable with model quirks. We will added some helpers and examples to ease the pain...



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
from .utils.qto_calculator import QtoCalculator