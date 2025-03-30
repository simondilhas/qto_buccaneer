# QTO Buccaneer  
*Quantity Takeoff tools for data-savvy BIM rebels*

Ahoy! This Python library is your toolkit for exploring, extracting, and calculating quantities from IFC models—ideal for anyone in construction, architecture, or BIM who's tired of manual takeoffs and spreadsheet acrobatics.

## 📑 Table of Contents
- [What This Is](#-what-this-is)
- [Designed for abstractBIM Data](#-designed-for-abstractbim-data)
- [Project Structure](#-project-structure)
- [Installation](#️-installation)
- [Quick Start](#-quick-start)
- [Development Pipeline](#-development-pipeline)
- [Contributing](#-contributing)

## ⚓ What This Is

A growing set of scripts and functions to help you:

- Extract Gross Floor Areas  
- Calculate wall, slab, and facade quantities  
- Classify elements (e.g. internal vs. external)  
- Link quantities to cost data  
- Export results to Excel, CSV, or dashboards  

All using open standards (IFC) and Python tools.

## 🧭 Designed for abstractBIM Data

This library is optimized for use with [**abstractBIM**](https://abstractbim.com) IFC files. Why?

Because abstractBIM enforces consistent structure, naming, and geometry—so you can focus on logic and automation, not debugging messy models.

You can adapt this code to raw IFC files using `ifcopenshell`, but you may need to roll up your sleeves. We include some examples and fallbacks where possible.

> Want to skip the modeling chaos and get right to the treasure?  
> Use abstractBIM as your map. The calculations here are free—the clean data is the magic sauce.

## 📁 Project Structure

qto-buccaneer/
├── src/
│ └── qto_buccaneer/
│ ├── utils
| |└──ifc_loader.py # IFC file loading and element filtering
│ └── qto_calculator.py # Quantity calculation methods
├── examples/
│ └── example_use_qto_calculator.py # Usage examples
├── tests/
│ └── .|.. # Test files
├── requirements.txt # Project dependencies
└── README.md # This file

## ⚙️ Installation

```bash
git clone https://github.com/simondilhas/qto-buccaneer.git
cd qto-buccaneer
pip install -r requirements.txt

```

## 🚀 Quick Start

```python
from src.qto_buccaneer.ifc_loader import IfcLoader
from src.qto_buccaneer.qto_calculator import QtoCalculator

# Load your IFC file
loader = IfcLoader("path/to/your/model.ifc")
qto = QtoCalculator(loader)

# Calculate quantities with default values optimized for abstractBIM IFC files
gfa = qto.calculate_gross_floor_area()
volume = qto.calculate_gross_floor_volume()
```
All calculation functions accept optional parameters to customize the behavior for your specific needs and IFC structure.
Check the `examples` directory for more detailed usage examples.

## 🗺️ Development Pipeline

We're charting a course for more features! Here's what's on the horizon:

1. **Data Enrichment & Classifications** 
   - Adding support for various classification systems
   - Enriching the IFC with additional data
   - More sophisticated calculation rules based on these enriched files

2. **Predefined Visualization**
   - Ready-to-use graphs and charts
   - Standard reporting templates
   - Visual comparison tools

3. **Multi-Project Analysis**
   - Compare quantities across projects
   - Benchmark capabilities
   - Portfolio-level insights

4. **Real-World Testing**
   - Validation in live projects
   - Performance optimization
   - Edge case handling

5. **Library Development**
   - Package distribution via PyPI
   - More tests
   - Comprehensive documentation

Want to help with any of these? Check out our [Contributing](#-contributing) section!

## 🤝 Contributing

Ahoy fellow BIM pirates! We're excited about every form of contribution, whether it's:

- Ideas for new features
- Bug reports
- Code contributions
- Use cases we haven't thought of
- Or anything else you think could make this better

Let's figure it out together! Drop a line to simon.dilhas@abstract.build and let's make quantity takeoffs better for everyone.

API Documentation
===============

QTO Calculator
-------------

.. automodule:: src.qto_buccaneer.qto_calculator
   :members:
   :undoc-members:
   :show-inheritance:

IFC Loader
----------

.. automodule:: src.qto_buccaneer.utils.ifc_loader
   :members:
   :undoc-members:
   :show-inheritance:

Welcome to QTO Buccaneer's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   readme
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
