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

- Define the logic how a metric is defined in metrics_config.yaml
- Calculate Metrics based on yaml
- Calculate Metrics by room
- Export metrics to Excel and other reports


All using open standards (IFC) and Python tools.

## 🧭 Designed for abstractBIM Data

This library is optimized for use with [**abstractBIM**](https://abstractbim.com) IFC files. Why?

Because abstractBIM enforces consistent structure, naming, and geometry—so you can focus on logic and automation, not debugging messy models.

You can adapt this code to raw IFC files using `ifcopenshell`, but you may need to roll up your sleeves. We include some examples and fallbacks where possible.

> Want to skip the modeling chaos and get right to the treasure?  
> Use abstractBIM as your map. The calculations here are free—the clean data is the magic sauce.

## 📁 Project Structure

```
qto-buccaneer/
├── src/
│   └── qto_buccaneer/
│       ├── utils/
│       │   ├── ifc_loader.py    # IFC file loading and element filtering
│       │   └── qto_calculator.py # Core quantity calculation methods
│       ├── metrics.py           # Main metrics calculation interface
│       ├── metrics_config.yaml  # Metrics configuration
│       └── reports.py           # Export utilities
├── examples/
│   └── calculate_metrics.py     # Basic usage example
├── tests/
│   └── .                        # Test files
├── requirements.txt             # Project dependencies
└── README.md                    # This file

```

## ⚙️ Installation

```bash
git clone https://github.com/simondilhas/qto-buccaneer.git
cd qto-buccaneer
pip install -r requirements.txt
```

## 🚀 Quick Start

```python
from qto_buccaneer.metrics import calculate_all_metrics
from qto_buccaneer.utils.reports import export_to_excel

# Calculate all metrics using configuration file
metrics_df, room_metrics_df = calculate_all_metrics(
    ifc_path="path/to/your/model.ifc",
    config_path="path/to/your/metrics_config.yaml"
)

# Export results to Excel
export_to_excel(metrics_df, "metrics.xlsx")
export_to_excel(room_metrics_df, "room_metrics.xlsx")
```

All calculation functions accept optional parameters to customize the behavior for your specific needs and IFC structure.
Check the `examples` directory for more detailed usage examples.

## 🗺️ Development Pipeline

We're charting a course for more features! Here's what's on the horizon:

0. **Refacturing for config pattern**
   - Tests$
   - Documentation
   - Bugfixes with metrics config

1. **Data Enrichment & Classifications** 
   - Adding support for various classification systems
   - Enhanced data enrichment capabilities
   - More sophisticated calculation rules

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
   - Comprehensive documentation
   - Extended API support

Want to help with any of these? Check out our [Contributing](#-contributing) section!

## 🤝 Contributing

Ahoy fellow BIM pirates! We're excited about every form of contribution, whether it's:

- Ideas for new features
- Bug reports
- Code contributions
- Use cases we haven't thought of
- Or anything else you think could make this better

Let's figure it out together! Drop a line to simon.dilhas@abstract.build and let's make quantity takeoffs better for everyone.