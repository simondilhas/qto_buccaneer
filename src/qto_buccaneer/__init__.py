"""
This package provides tools for exploring, extracting, and calculating quantities 
from IFC models. It's designed for construction, architecture, and BIM professionals 
who need automated quantity takeoffs.

Main Components:
- metrics: Core metrics calculation functionality
- utils: Helper functions for IFC handling and calculations
- reports: Export and reporting utilities
- configs: Configuration files and settings

With this toolkit, you can:

- Calculate project-wide metrics based on your definitions
- Calculate metrics per room or space
- Export results to Excel and other report formats
- Define metric logic using a YAML config file, instead of having to deal with code
- Enrich and clean up IFC files—friendlier than raw ifcopenshell

## 🧭 Designed for IFC, optimized for abstractBIM Data

This library works with any well-structured IFC file, but it shines brightest when used with clean, consistent data.
And that's why it's optimized for abstractBIM Data in the presets. 

Because abstractBIM gives you:

- Consistent naming
- Predictable geometry
- Clean data structure

Which means less time debugging, more time automating.

Yes, you can still use raw IFC + ifcopenshell, but you'll want to be comfortable with model quirks. We will added some helpers and examples to ease the pain...

> Want to skip the modeling chaos and get right to the treasure?  
> Use abstractBIM as your map. The calculations here are free—the clean data is the magic sauce.



"""

from ._version import __version__

__version__ = __version__
__author__ = "Simon Dilhas"

# Comment out imports until we verify what actually exists
# from .metrics import calculate_all_metrics

# The following code block is commented out as it's not provided in the original file
# from .utils import load_ifc  # Uncomment if load_ifc exists in utils.py
# from .reports import export_to_excel  # Uncomment if export_to_excel exists in reports.py 