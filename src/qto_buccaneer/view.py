import subprocess
import sys
from pathlib import Path

#Does not work at the moment

def convert_ifc_to_xkt(ifc_path):
    ifc_file = Path(ifc_path)
    
    if not ifc_file.exists():
        print(f"❌ File not found: {ifc_file}")
        sys.exit(1)

    xkt_file = ifc_file.with_suffix('.xkt')  # same name, different extension

    # Build the command correctly
    cmd = [
        "xeokit-convert",
        "-s", str(ifc_file),
        "-o", str(xkt_file)
    ]

    try:
        print(f"🚀 Converting {ifc_file} to {xkt_file}...")
        subprocess.run(cmd, check=True)
        print(f"✅ Conversion finished: {xkt_file}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Conversion failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert.py your_model.ifc")
        sys.exit(1)

    convert_ifc_to_xkt(sys.argv[1])
