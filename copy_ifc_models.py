import os
import shutil
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Source and destination paths
SOURCE_BASE = "/home/simondilhas/Programmierung/qto_buccaneer/projects/Seefeld__private/buildings"
DESTINATION_DIR = "/home/simondilhas/Programmierung/qto_buccaneer/projects/Seefeld__private/QS20240518"

def copy_ifc_models():
    # Create destination directory if it doesn't exist
    os.makedirs(DESTINATION_DIR, exist_ok=True)
    
    # Get all building directories
    building_dirs = [d for d in os.listdir(SOURCE_BASE) if os.path.isdir(os.path.join(SOURCE_BASE, d))]
    
    total_files_copied = 0
    
    for building in building_dirs:
        source_dir = os.path.join(SOURCE_BASE, building, "04_enriched_ifc_with_spatial_data")
        
        if not os.path.exists(source_dir):
            logger.warning(f"Source directory not found for building {building}: {source_dir}")
            continue
            
        # Find all IFC files in the source directory
        ifc_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.ifc')]
        
        for ifc_file in ifc_files:
            source_path = os.path.join(source_dir, ifc_file)
            # Create a unique destination filename using building name
            dest_filename = f"{building}_{ifc_file}"
            dest_path = os.path.join(DESTINATION_DIR, dest_filename)
            
            try:
                shutil.copy2(source_path, dest_path)
                logger.info(f"Copied {ifc_file} from {building} to {dest_filename}")
                total_files_copied += 1
            except Exception as e:
                logger.error(f"Error copying {ifc_file} from {building}: {str(e)}")
    
    logger.info(f"\nCopy operation completed. Total files copied: {total_files_copied}")

if __name__ == "__main__":
    copy_ifc_models() 