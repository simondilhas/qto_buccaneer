import os
import shutil
import subprocess
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
AZURE_CONTAINER_NAME = os.getenv('AZURE_CONTAINER_NAME', 'projects')
AZURE_ENVIRONMENT = os.getenv('AZURE_ENVIRONMENT', 'false').lower() == 'true'
PROJECT_NAME = os.getenv('PROJECT_NAME', 'Seefeld__private')

# Source base where all building folders are
SRC_BASE = f"projects/{PROJECT_NAME}/buildings"

def prevent_sleep():
    """Prevent system from sleeping/shutting down"""
    try:
        # For Linux systems
        subprocess.run(['systemctl', 'mask', 'sleep.target', 'suspend.target', 'hibernate.target', 'hybrid-sleep.target'], check=True)
        logger.info("System sleep/shutdown prevented")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Could not prevent system sleep: {e}")

def restore_sleep():
    """Restore normal system sleep behavior"""
    try:
        # For Linux systems
        subprocess.run(['systemctl', 'unmask', 'sleep.target', 'suspend.target', 'hibernate.target', 'hybrid-sleep.target'], check=True)
        logger.info("System sleep behavior restored")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Could not restore system sleep: {e}")

def upload_to_blob_storage(blob_service_client, container_name, local_file_path, blob_name):
    """Upload a file to Azure Blob Storage"""
    try:
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Upload the file
        with open(local_file_path, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data, overwrite=True)
        logger.info(f"Successfully uploaded {local_file_path} to {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Error uploading {local_file_path} to {blob_name}: {str(e)}")
        return False

def main():
    logger.info(f"Starting data upload process. Azure environment: {AZURE_ENVIRONMENT}")
    
    if not AZURE_ENVIRONMENT:
        logger.info("Not in Azure environment, skipping data upload")
        return

    # Prevent system from sleeping
    prevent_sleep()

    # Track upload statistics
    upload_stats = defaultdict(lambda: {'successful': 0, 'failed': 0, 'total': 0})

    try:
        # Validate Azure configuration
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable is not set")
        
        logger.info("Initializing BlobServiceClient")
        # Initialize BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

        # Find all building folders in the source
        building_names = [name for name in os.listdir(SRC_BASE) if os.path.isdir(os.path.join(SRC_BASE, name))]
        logger.info(f"Found {len(building_names)} building folders to process")

        for building in building_names:
            logger.info(f"Processing building: {building}")
            src_building = os.path.join(SRC_BASE, building)
            
            # --- Copy metrics Excel file(s) ---
            src_metrics_dir = os.path.join(src_building, "07_metrics")
            if os.path.isdir(src_metrics_dir):
                logger.info(f"Processing metrics directory for {building}")
                for file in os.listdir(src_metrics_dir):
                    if file.endswith(('.xlsx', '.xls')):
                        local_file_path = os.path.join(src_metrics_dir, file)
                        blob_name = f"buildings/{building}/07_metrics/{file}"
                        logger.info(f"Found metrics file to upload: {file}")
                        if upload_to_blob_storage(blob_service_client, AZURE_CONTAINER_NAME, local_file_path, blob_name):
                            upload_stats[building]['successful'] += 1
                        else:
                            upload_stats[building]['failed'] += 1
                        upload_stats[building]['total'] += 1
            else:
                logger.info(f"No metrics directory found for {building}")

            # --- Copy graph folder ---
            src_graph_dir = os.path.join(src_building, "11_abstractbim_plots")
            if os.path.isdir(src_graph_dir):
                logger.info(f"Processing graph directory for {building}")
                for root, _, files in os.walk(src_graph_dir):
                    for file in files:
                        local_file_path = os.path.join(root, file)
                        # Create relative path for blob storage
                        rel_path = os.path.relpath(local_file_path, src_building)
                        blob_name = f"buildings/{building}/{rel_path}"
                        if upload_to_blob_storage(blob_service_client, AZURE_CONTAINER_NAME, local_file_path, blob_name):
                            upload_stats[building]['successful'] += 1
                        else:
                            upload_stats[building]['failed'] += 1
                        upload_stats[building]['total'] += 1
            else:
                logger.info(f"No graph directory found for {building}")

            # --- Copy check folders ---
            for check_folder in ["09_building_inside_envelope", "09_check_building_inside_envelop"]:
                src_check_dir = os.path.join(src_building, check_folder)
                if os.path.isdir(src_check_dir):
                    logger.info(f"Processing check directory {check_folder} for {building}")
                    for root, _, files in os.walk(src_check_dir):
                        for file in files:
                            local_file_path = os.path.join(root, file)
                            # Create relative path for blob storage
                            rel_path = os.path.relpath(local_file_path, src_building)
                            blob_name = f"buildings/{building}/{rel_path}"
                            if upload_to_blob_storage(blob_service_client, AZURE_CONTAINER_NAME, local_file_path, blob_name):
                                upload_stats[building]['successful'] += 1
                            else:
                                upload_stats[building]['failed'] += 1
                            upload_stats[building]['total'] += 1
                else:
                    logger.info(f"No check directory {check_folder} found for {building}")
            
            logger.info(f"Completed processing building: {building}")

        # Print summary
        logger.info("\n=== Upload Summary ===")
        successful_projects = []
        failed_projects = []
        for building, stats in upload_stats.items():
            if stats['total'] > 0:
                if stats['failed'] == 0:
                    successful_projects.append(building)
                else:
                    failed_projects.append(building)
                logger.info(f"\nBuilding: {building}")
                logger.info(f"  Total files: {stats['total']}")
                logger.info(f"  Successful uploads: {stats['successful']}")
                logger.info(f"  Failed uploads: {stats['failed']}")
        
        logger.info("\n=== Project Status ===")
        if successful_projects:
            logger.info("\nSuccessfully uploaded projects:")
            for project in sorted(successful_projects):
                logger.info(f"  ✓ {project}")
        
        if failed_projects:
            logger.info("\nProjects with failed uploads:")
            for project in sorted(failed_projects):
                logger.info(f"  ✗ {project}")

    except Exception as e:
        logger.error(f"An error occurred during the upload process: {str(e)}")
        raise
    finally:
        # Restore normal system sleep behavior
        restore_sleep()

if __name__ == "__main__":
    main()