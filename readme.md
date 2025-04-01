# QTO Buccaneer  
*Quantity Takeoff tools for data-savvy BIM rebels*

Ahoy! This Python library is your toolkit for exploring, extracting, and calculating quantities from IFC models—ideal for anyone in construction, architecture, or BIM who's tired of manual takeoffs and spreadsheet acrobatics.


## 📑 Table of Contents
- [What This Is](#-what-this-is)
- [Designed for abstractBIM Data](#-designed-for-abstractbim-data)
- [Project Structure](#-project-structure)
- [Installation](#️-installation)
- [Quick Start](#-quick-start)
  - [Configuration](#-configuration)
  - [Metrics Configuration](#metrics-configuration)
  - [Room-based Metrics](#room-based-metrics)
  - [Filter Options](#filter-options)
- [Development Pipeline](#-development-pipeline)
- [Contributing](#-contributing)

## ⚓ What This Is

⚓ What This Is

A general-purpose Python library for calculating and managing quantity takeoffs from IFC models using open standards and open-source tools.

With this toolkit, you can:

    Define metric logic using a YAML config file

    Enrich and clean up IFC files—friendlier than raw ifcopenshell

    Calculate project-wide metrics based on your definitions

    Calculate metrics per room or space

    Export results to Excel and other report formats

## 🧭 Designed for abstractBIM Data

This library works with any well-structured IFC file, but it shines brightest when used with clean, consistent data.
And that's why it's optimized for abstractBIM Data in the presets. 

Because abstractBIM gives you:

    Consistent naming

    Predictable geometry

    Clean data structure

Which means less time debugging, more time automating.

    Think of abstractBIM as your treasure map.
    The calculations here are free—the clean data is the real loot.

Yes, you can still use raw IFC + ifcopenshell, but you’ll want to be comfortable with model quirks. We will added some helpers and examples to ease the pain...




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
# Option 1: Clone and install locally
git clone https://github.com/simondilhas/qto-buccaneer.git
cd qto-buccaneer
pip install -r requirements.txt

# Option 2: Install directly from GitHub
pip install git+https://github.com/simondilhas/qto-buccaneer.git
```

## 🚀 Quick Start

### Installation

```bash
# Option 1: Clone and install locally
git clone https://github.com/simondilhas/qto-buccaneer.git
cd qto-buccaneer
pip install -r requirements.txt

# Option 2: Install directly from GitHub
pip install git+https://github.com/simondilhas/qto-buccaneer.git
```

### Usage Examples

Look bellow or in the folder /examples for more detailed once.

#### Calculate Metrics
```python
from qto_buccaneer.metrics import calculate_all_metrics
import yaml

def main():
    # Load config
    with open("path/to/metrics_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Calculate metrics
    metrics_df = calculate_all_metrics(
        config=config,
        filepath="path/to/your/model.ifc"
    )
    
    # Save results
    metrics_df.to_excel("results.xlsx")

if __name__ == "__main__":
    main()
```

#### Enrich IFC Model
```python
import pandas as pd
from qto_buccaneer.enrich import enrich_ifc_with_df

def main():
    # Load enrichment data
    df_enrichment = pd.read_excel("path/to/enrichment_data.xlsx")
    
    # Enrich IFC file
    enriched_ifc_path = enrich_ifc_with_df(
        ifc_file="path/to/your/model.ifc",
        df_for_ifc_enrichment=df_enrichment,
        key="LongName",  # column name to match IFC elements
        pset_name="Pset_Enrichment"  # optional
    )
    
    print(f"Created enriched IFC file: {enriched_ifc_path}")

if __name__ == "__main__":
    main()

#### Configuration Files

The package uses YAML configuration files to define metrics and enrichment rules. Here's an example metrics configuration:

```yaml
metrics:
  gross_floor_area:
    description: "The gross floor area excluding voids"
    quantity_type: "area"
    ifc_entity: "IfcSpace"
    pset_name: "Qto_SpaceBaseQuantities"
    prop_name: "NetFloorArea"
    include_filter:
      Name: "GrossArea"
    subtract_filter:
      Name: ["LUF", "Void", "Luftraum"]

room_based_metrics:
  windows_area_by_room:
    description: "Get windows grouped by room"
    ifc_entity: "IfcWindow"
    grouping_attribute: "GlobalId"
    pset_name: "Qto_WindowBaseQuantities"
    prop_name: "Area"
```

Key configuration concepts:
- `metrics`: Standard metrics that return a single value for the entire project
- `room_based_metrics`: Metrics calculated per room/space
- Filters can use:
  - Simple key-value pairs: `Name: "GrossArea"`
  - Lists: `Name: ["LUF", "Void"]`
  - Comparisons: `Width: [">", 0.15]`
  - Boolean values: `IsExternal: true`

For more examples and detailed configuration options, check the `configs/` directory in the repository.



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

