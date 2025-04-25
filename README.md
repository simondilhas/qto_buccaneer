# QTO Buccaneer  
*Quantity Takeoff tools for data-savvy BIM rebels*

Ahoy! Tired of manual takeoffs and spreadsheet gymnastics? QTO Buccaneer is your Python-powered toolkit for exploring, extracting, and calculating quantities from IFC models. Built for architects, engineers, and construction pros who know their way around Excel more than Python. If you've wrangled a spreadsheet before — you're already 80% there. The rest? This library will help you plunder it with ease.


## 📑 Table of Contents
- [What This Is](#-what-this-is)
- [Designed for IFC, optimized for abstractBIM Data](#-designed-for-abstractbim-data)
- [Quick Start](#-quick-start)
  - [Tutorial for Programming Landlubbers](#tutorial-for-programming-landlubbers)
  - [The Workflow System](#the-workflow-system)
    - [Project Structure](#-project-structure-1)
    - [How It Works](#-how-it-works)
    - [Getting Started with Projects](#-getting-started-with-projects)
  - [Installation](#installation-for-non-landlubbers)
  - [Development Setup](#development-setup)
  - [Usage Examples](#usage-examples)
    - [Calculate Metrics](#calculate-metrics)
    - [Enrich IFC Model](#enrich-ifc-model)
    - [Configuration Files](#configuration-files)
- [Project Structure](#-project-structure)
- [Dependencies](#dependencies)
  - [Core Dependencies](#core-dependencies)
  - [Python Package Dependencies](#python-package-dependencies)
  - [Optional Dependencies](#optional-dependencies)
  - [Version Requirements](#version-requirements)
- [Development Pipeline](#️-development-pipeline)
- [Contributing](#-contributing)

## ⚓ What This Is

A general-purpose Python library for calculating and managing quantity takeoffs from IFC models using open standards and open-source tools.

What QTO Buccaneer lets you do:

- Calculate project-wide metrics based on your own definition- 
- Calculate metrics per room or space
- Benchmark different projects to spot trends and outlier- 
- Export results to Excel and other report formats used by your team 
- Create beautiful reports with plans, making information visible and manageable 
- Define metric logic using a user-friendly YAML config file — no need to write code or click through complex software 
- Enrich and clean up IFC files more easily than working directly with raw ifcopenshell
- Build up project specific workflows and apply the same rules consecutive to the models. E.g. 
   - For architectural competitions
   - Benchmarking Portfolios
   - Calculating costs in different project phases / times
   - Doing design to cost


## 🧭 Philosophy: Independence First — Tools for the Bold

QTO Buccaneer is built for those who believe in **owning their workflow**.  
You don't need paid services to sail these seas:  
Everything you need to calculate metrics, enrich models, and create reports is included here — free, open-source, and ready for action.

Our compass points to **open standards**, **hands-on knowledge**, and **giving you full control** over your quantity takeoffs.

> True pirates don't depend on kings.  
> They build their own ships — and borrow a map when it saves time.

---

## 🚀 Fast Lanes: Smooth Sailing When You Want It

While QTO Buccaneer is fully independent, some parts of the journey can be rough:

| Challenge | Fast Lane Solution |
|:----------|:-------------------|
| Getting clean, consistent architectural models is hard. | 👉 **abstractBIM templates** provide clean IFC models with predictable naming, structure, and geometry. |
| Extracting structured geometry from IFC files is tedious and messy. | 👉 **abstractBIM IFC-to-JSON API** delivers clean, structured model data ready for figures and floorplan visualizations. |

> **These fast lanes are optional.**  
> You can always chart your own course — but when you want smoother sailing, they're ready for you.

---

## 🗺️ Available Fast Lanes

### 🏛️ abstractBIM
- Convert any architectural BIM with Spaces into a consistent ifc with walls, slabs, ...
- Clean IFC models
- Consistent structure
- Predictable naming conventions
- Optimized for automation

👉 [Try abstractBIM](www.abstractBIM.com)

*Alternative:* 
*- Good modeling practice that provides consistent clean data.*

---

### 📡 IFC-to-JSON Web Service
- Transform raw IFC into clean structured JSON
- Quickly generate floorplans, element overviews, and spatial figures
- Skip the tedious IFC parsing setups

👉 [Contact Simon Dilhas for access to the api](mailto:simon.dilhas@abstract.build) 

*Alternative:*
*- Set up your own, converter with IfcOpenshell Geom modul.*
*- BlenderBIM -> dotBIM -> to expected Json format (converter will come)*

## 🚀 Quick Start

### Tutorial for Programming Landlubbers

Welcome aboard — and congrats on making it this far!
Ten years ago, I was right where you are now. The black screens, the weird acronyms, the cryptic error messages — they all freaked me out too. It took time (and plenty of coffee) to feel at home with code. And honestly? I'm still learning new tricks every day.

That's exactly why I am the right pirate to guide you. I know the waters, I've hit the reefs — and I've mapped a path to help you sail around the fear and dive straight into the good stuff.

This tutorial is your first step into a world that's surprisingly rewarding — and not nearly as scary as it seems.

I believe in hands-on learning. That means you're gonna roll up your sleeves and set up your environment.

Check out this video for a quick start: [Webinar](https://www.youtube.com/watch?v=O9jkSgPl_Hg)

#### **Step 1: Set Sail on Colab**

Head over to [Google Colab](https://colab.research.google.com) — this will be your coding playground, no installations needed. It's like a Notebook in the cloud that can execute code and document transparently the steps you take. 

*Pro Lingo Tip: These kind of Notebooks are called Jupyter notebooks

#### Step 2: Open the Jupyter Notebook

- Click **"Open Notebook"**.
- Navigate to the **GitHub** tab.
- Paste the following URL into the search bar:

  https://github.com/simondilhas/qto_buccaneer/blob/main/tutorial/Intro/QTO_Buccaneer_Intro_Tutorial.ipynb 
  
- The notebook will open.

> **Pro Lingo Tip:** GitHub is like a pirate's cloud vault for code — it tracks changes, keeps everything versioned, and makes collaboration easy across your crew.

---

#### 🧭 Step 3: Follow the Notebook's Commands Like a Good Deckhand

Once the notebook is open, you're in the captain's seat. You'll:

- Get introduced to **pandas** — the data wrangler's version of Excel (but with more firepower).
- Calculate quantity metrics using the general tools of panda.
- Open a BIM model and use the built-in **QTO Buccaneer shortcuts** to speed up your takeoff workflow.


   ```

### Installation (for non landlubbers)

```bash
# Option 1: Clone and install locally
git clone https://github.com/simondilhas/qto-buccaneer.git
cd qto-buccaneer
pip install -r requirements.txt

# Option 2: Install directly from GitHub
pip install git+https://github.com/simondilhas/qto-buccaneer.git
```

### Development Setup

For developers who want to work on the codebase:

1. Clone the repository:
```bash
git clone https://github.com/simondilhas/qto-buccaneer.git
cd qto-buccaneer
```

2. Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

3. Install development dependencies:
```bash
# Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel

# Install the package in development mode
pip install -e .

# Install development dependencies
pip install -r requirements_dev.txt
```

Now you can:
- Import the package from anywhere in your code: `from qto_buccaneer import ...`
- Make changes to the code and see them reflected immediately
- Run tests and contribute to the project

## Project Creation Scripts

The repository includes scripts to help you create new projects based on templates. To set up these scripts:

1. Make the setup script executable and run it:
   ```bash
   chmod +x setup_scripts.sh
   ./setup_scripts.sh
   ```

2. This will:
   - Make the project creation scripts executable
   - Set up a virtual environment if one doesn't exist
   - Install required dependencies

3. You can then create new projects using:
   ```bash
   ./create_project my_new_project
   ```
   
   Or specify a different template:
   ```bash
   ./create_project my_new_project --template custom_template
   ```

The script will create a new project in the `projects` directory based on the specified template.

### Usage Examples

Look bellow or in the folder examples for more detailed once or in the documentation: 

https://simondilhas.github.io/qto_buccaneer/qto_buccaneer/index.html

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

## 📁 Project Structure

```bash
qto-buccaneer/
├── src/
│   └── qto_buccaneer/
│       ├── configs/                                  # Configuration files
│       ├── plots_utils/                              # Plotting utilities
│       ├── scripts/                                  # Utility scripts
│       ├── utils/                                    # Utility functions
│       ├── __init__.py                              # Package initialization
│       ├── _version.py                              # Version information
│       ├── enrich.py                                # IFC enrichment functionality
│       ├── geometry.py                              # Geometry processing
│       ├── metrics.py                               # Main metrics calculation interface
│       ├── plots.py                                 # Plotting functionality
│       ├── preprocess_ifc.py                        # IFC preprocessing utilities
│       ├── reports.py                               # Report generation
│       └── test.py                                  # Test utilities
├── projects/                                        # Project directories
│   ├── 00_run_create_new_project.py                # Project creation script
│   ├── 002_example_project__public/                # Example project
│   └── __init__                                    # Package marker
├── templates/                                       # Template files
├── tests/                                          # Test files
├── tutorial/                                       # Tutorial materials
├── docs/                                           # Documentation
├── examples/                                       # Example scripts
├── .github/                                        # GitHub configuration
├── .vscode/                                        # VS Code configuration
├── .env                                            # Environment variables
├── .env.example                                    # Example environment variables
├── .gitignore                                      # Git ignore rules
├── CONTRIBUTING.md                                 # Contribution guidelines
├── LICENSE.md                                      # License information
├── README.md                                       # Project documentation
├── add_building                                    # Building addition script
├── create_project                                  # Project creation script
├── pyproject.toml                                  # Project configuration
├── pytest.ini                                      # Pytest configuration
├── requirements.txt                                # Project dependencies
├── requirements_dev.txt                            # Development dependencies
├── setup.py                                        # Package installation configuration
└── setup_scripts.sh                                # Setup scripts
```

## Dependencies

This project relies on several key dependencies:

### Core Dependencies
- [IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell): Open-source library for working with IFC files
  - License: [GNU Lesser General Public License v3.0](https://www.gnu.org/licenses/lgpl-3.0.html)
  - Used for: IFC file parsing and geometric operations

### Python Package Dependencies
- `pandas`: Data manipulation and analysis
- `numpy`: Numerical computations
- `pyyaml`: YAML configuration file handling
- `typing`: Type hints support

### Optional Dependencies
- `pytest`: For running the test suite
- `black`: Code formatting
- `mypy`: Static type checking
- `sphinx`: Documentation generation

### Version Requirements
- Python >= 3.8
- IfcOpenShell >= 0.7.0

### Installation

You can install all required dependencies using:
```bash
pip install -r requirements.txt
```

For development dependencies:
```bash
pip install -r requirements-dev.txt
```

Note: IfcOpenShell might require additional system-level dependencies depending on your operating system. Please refer to the [IfcOpenShell installation guide](https://github.com/IfcOpenShell/IfcOpenShell) for platform-specific instructions.

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

