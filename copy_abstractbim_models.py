import os
import shutil
from glob import glob

# Source pattern and destination directory
source_pattern = os.path.join('buildings', '*', '03_abstractbim_model')
dest_dir = os.path.join('projects', 'Seefeld__private', 'all_models_abstractBIM__private')

# Create destination directory if it doesn't exist
os.makedirs(dest_dir, exist_ok=True)

# Find all matching source directories
source_dirs = glob(source_pattern)

for src_dir in source_dirs:
    if os.path.isdir(src_dir):
        for filename in os.listdir(src_dir):
            src_file = os.path.join(src_dir, filename)
            dest_file = os.path.join(dest_dir, filename)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dest_file)
                print(f"Copied {src_file} to {dest_file}") 