"""
Test script pentru integrarea în qto_buccaneer
"""

import sys
sys.path.insert(0, 'src')

from qto_buccaneer import visualize_ifc

# IFC file URL
ifc_url = "https://raw.githubusercontent.com/ionuting/qto_test/refs/heads/main/tutorial/Intro/simple_model_abstractBIM.ifc"

print("🚀 Testing qto_buccaneer library integration...")
print("="*80 + "\n")

# Test 1: Verifică că funcția există
print("✅ Test 1: Import successful")
print(f"   Function: {visualize_ifc.__name__}")
print(f"   Module: {visualize_ifc.__module__}")

# Test 2: Vizualizare cu statistici (3 linii de cod!)
print("\n✅ Test 2: Visualization with statistics (3-line usage)")
print("="*80 + "\n")

visualize_ifc(ifc_url, show_statistics=True)
