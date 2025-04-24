"""
🏴‍☠️ IFC-to-JSON Converter — Fast Lane or Forge Your Own

This optional module converts your IFC model into structured JSON — 
including geometry and metadata — to power metrics, visualizations, and model logic.

**Option 1: Take the Fast Lane**
Use the abstractBIM IFC-to-JSON API to extract clean, ready-to-use geometry 
and metadata without the headache of local setup.

  Pros:
    - No configuration required
    - API returns clean spatial data and geometry
    - Ideal for quick dashboards, floorplans, or metrics pipelines

  ⚓ Access by request: simon.dilhas@abstract.build

**Option 2: Build Your Own Converter**
Set up your own local IFC-to-JSON pipeline using `ifcopenshell.geom`:

  - Install IfcOpenShell with geometry support (OCC backend required)
  - Use `ifcopenshell.geom.create_shape()` to extract meshes
  - Structure the results as JSON for your needs

  Pros:
    - Full control over geometry parsing
    - Zero API dependency
    - Perfect for offline workflows or custom pipelines

📦 Expected Input: Clean IFC file with spatial hierarchy (like abstractBIM templates)
📄 Output: JSON file with

**Option 3: Use IFC Converter**
Use the IFC Converter to convert your IFC file to JSON (I did not test it yet, but it should work with some post conversion data reorganisation)

https://docs.ifcopenshell.org/ifcconvert.html
 '''BASH
ifcconvert --ifc-file input.ifc --export-json output.json
'''


"""

import sys
from pathlib import Path
from qto_buccaneer.utils.ifc_to_json_converter import upload_ifc_file
from dotenv import load_dotenv
import os

# Add src directory to path
src_dir = str(Path(__file__).parent.parent / "src")

load_dotenv()

API_KEY = os.getenv("IFC_TO_JSON_API_KEY")
API_URL = os.getenv("IFC_TO_JSON_API_URL")
API_KEY_NAME = os.getenv('API_KEY_NAME')
project_name = "001_example_project__public"
project_dir = Path(__file__).parent.parent / "projects" / project_name
ifc_file_name = "Mustermodell V1_abstractBIM"
ifc_file_for_conversion = project_dir / "output" / "02_above_below_ground" / f"{ifc_file_name}_enriched_sd.ifc"
output_dir = project_dir / "output" / "04_json_geometry (optional)"

sys.argv.extend([
    '--debug',
    '--url', 'http://localhost:8000',
    '--api-key', os.getenv(API_KEY_NAME, API_KEY)
])



# Example usage
upload_ifc_file(
    file_path=ifc_file_for_conversion,
    api_key=API_KEY,
    base_url="http://0.0.0.0:8000",
    include_geometry=True,
    include_metadata=True,
    output_dir=output_dir,
    debug=True
)