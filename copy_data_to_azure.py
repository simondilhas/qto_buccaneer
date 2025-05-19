import os
import shutil
import subprocess
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import logging
from collections import defaultdict
import concurrent.futures
import zipfile
import tempfile
import io

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

# Get workspace root directory (where the script is located)
WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))

# Source base where all building folders are - using absolute path
SRC_BASE = os.path.join(WORKSPACE_ROOT, "projects", PROJECT_NAME, "buildings")

logger.info(f"Using source base directory: {SRC_BASE}")

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

def compress_excel_file(file_path):
    """Compress Excel file if it's not already compressed"""
    if not file_path.endswith(('.xlsx', '.xls')):
        return file_path
        
    try:
        # Create a temporary file for the compressed version
        temp_dir = tempfile.mkdtemp()
        compressed_path = os.path.join(temp_dir, os.path.basename(file_path) + '.zip')
        
        with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, os.path.basename(file_path))
            
        return compressed_path
    except Exception as e:
        logger.warning(f"Failed to compress {file_path}: {e}")
        return file_path

def upload_to_blob_storage(blob_service_client, container_name, local_file_path, blob_name):
    """Upload a file to Azure Blob Storage only if it's newer than the existing blob"""
    try:
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Get local file modification time
        local_mtime = os.path.getmtime(local_file_path)
        
        try:
            # Get blob properties to check last modified time
            blob_properties = blob_client.get_blob_properties()
            blob_mtime = blob_properties.last_modified.timestamp()
            
            # If local file is not newer, skip upload
            if local_mtime <= blob_mtime:
                logger.info(f"Skipping {local_file_path} - no changes detected")
                return True
                
        except Exception as e:
            # If blob doesn't exist or other error, proceed with upload
            logger.info(f"Blob {blob_name} not found or error checking properties: {str(e)}")
        
        # Upload the file
        with open(local_file_path, "rb") as data:
            blob_client.upload_blob(data=data, overwrite=True)
        logger.info(f"Successfully uploaded {local_file_path} to {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Error uploading {local_file_path} to {blob_name}: {str(e)}")
        return False

def delete_blob_directory(blob_service_client, container_name, directory_prefix):
    """Delete all blobs with the given directory prefix"""
    try:
        container_client = blob_service_client.get_container_client(container_name)
        # List all blobs with the prefix
        blobs = container_client.list_blobs(name_starts_with=directory_prefix)
        
        # Delete each blob
        for blob in blobs:
            container_client.delete_blob(blob.name)
            logger.info(f"Deleted blob: {blob.name}")
            
        logger.info(f"Successfully deleted directory: {directory_prefix}")
        return True
    except Exception as e:
        logger.error(f"Error deleting directory {directory_prefix}: {str(e)}")
        return False

def process_project_files(blob_service_client, container_name, project_path):
    """Process project-level files"""
    upload_stats = {'successful': 0, 'failed': 0, 'total': 0}
    files_to_upload = []
    
    # Only process the reports directory
    reports_path = os.path.join(project_path, "reports")
    if os.path.exists(reports_path):
        # First delete the existing reports in the buildings root
        reports_prefix = "buildings/reports"
        delete_blob_directory(blob_service_client, container_name, reports_prefix)
        
        for item in os.listdir(reports_path):
            source = os.path.join(reports_path, item)
            destination = os.path.join(reports_path, item)

            # Check if source and destination are the same
            if os.path.abspath(source) != os.path.abspath(destination):
                shutil.copy2(source, destination)
            else:
                print(f"Skipping copy for {source} as source and destination are the same.")
    
    # Upload files in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_file = {
            executor.submit(
                upload_to_blob_storage,
                blob_service_client,
                container_name,
                local_file_path,
                blob_name
            ): (local_file_path, blob_name)
            for local_file_path, blob_name in files_to_upload
        }
        
        for future in concurrent.futures.as_completed(future_to_file):
            local_file_path, blob_name = future_to_file[future]
            try:
                if future.result():
                    upload_stats['successful'] += 1
                else:
                    upload_stats['failed'] += 1
                upload_stats['total'] += 1
            except Exception as e:
                logger.error(f"Error processing {local_file_path}: {e}")
                upload_stats['failed'] += 1
                upload_stats['total'] += 1
    
    return upload_stats

def process_building(building, blob_service_client, container_name, src_base):
    """Process a single building's files in parallel"""
    upload_stats = {'successful': 0, 'failed': 0, 'total': 0}
    src_building = os.path.join(src_base, building)
    
    # First delete the existing building directory in Azure
    building_prefix = f"buildings/{building}"
    delete_blob_directory(blob_service_client, container_name, building_prefix)
    
    # Collect all files to upload
    files_to_upload = []
    
    # Collect all files and directories within the building folder
    for root, _, files in os.walk(src_building):
        for file in files:
            local_file_path = os.path.join(root, file)
            rel_path = os.path.relpath(local_file_path, src_base)
            blob_name = f"buildings/{rel_path}"
            files_to_upload.append((local_file_path, blob_name))
    
    # Upload files in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_file = {
            executor.submit(
                upload_to_blob_storage,
                blob_service_client,
                container_name,
                local_file_path,
                blob_name
            ): (local_file_path, blob_name)
            for local_file_path, blob_name in files_to_upload
        }
        
        for future in concurrent.futures.as_completed(future_to_file):
            local_file_path, blob_name = future_to_file[future]
            try:
                if future.result():
                    upload_stats['successful'] += 1
                else:
                    upload_stats['failed'] += 1
                upload_stats['total'] += 1
            except Exception as e:
                logger.error(f"Error processing {local_file_path}: {e}")
                upload_stats['failed'] += 1
                upload_stats['total'] += 1
    
    return upload_stats

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

        # Process project files first
        project_path = os.path.join(WORKSPACE_ROOT, "projects", PROJECT_NAME)
        project_stats = process_project_files(blob_service_client, AZURE_CONTAINER_NAME, project_path)
        upload_stats['project_files'] = project_stats
        
        # Find all building folders in the source
        building_names = [name for name in os.listdir(SRC_BASE) if os.path.isdir(os.path.join(SRC_BASE, name))]
        logger.info(f"Found {len(building_names)} building folders to process")

        # Process buildings in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_building = {
                executor.submit(
                    process_building,
                    building,
                    blob_service_client,
                    AZURE_CONTAINER_NAME,
                    SRC_BASE
                ): building
                for building in building_names
            }
            
            for future in concurrent.futures.as_completed(future_to_building):
                building = future_to_building[future]
                try:
                    stats = future.result()
                    upload_stats[building] = stats
                except Exception as e:
                    logger.error(f"Error processing building {building}: {e}")
                    upload_stats[building] = {'successful': 0, 'failed': 0, 'total': 0}

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