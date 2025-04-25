#!/bin/bash

# Exit on error
set -e

echo "Setting up project creation scripts..."

# Make scripts executable
chmod +x create_project
chmod +x add_building
chmod +x scripts/create_new_project.py

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    echo "Virtual environment already exists."
fi

echo "Setup complete! You can now use:"
echo "1. './create_project <project_name>' to create new projects"
echo "2. './add_building <project_name> <building_name>' to add buildings to projects"
echo ""
echo "Example usage:"
echo "  ./create_project my_project"
echo "  ./add_building my_project__public building1" 