# QTO Buccaneer  
*Quantity Takeoff tools for data-savvy BIM rebels*

Ahoy! This Python library is your toolkit for exploring, extracting, and calculating quantities from IFC models—ideal for anyone in construction, architecture, or BIM who’s tired of manual takeoffs and spreadsheet acrobatics.

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

## ⚙️ Installation

```bash
git clone https://github.com/yourusername/qto-buccaneer.git
cd qto-buccaneer
pip install -r requirements.txt
