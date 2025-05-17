import os
import shutil
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
AZURE_CONTAINER_NAME = os.getenv('AZURE_CONTAINER_NAME', 'projects')

# Source base where all building folders are
SRC_BASE = "projects/Seefeld__private/buildings"

def upload_to_blob_storage(blob_service_client, container_name, local_file_path, blob_name):
    """Upload a file to Azure Blob Storage"""
    try:
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Upload the file
        with open(local_file_path, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data, overwrite=True)
        print(f"Uploaded {local_file_path} to {blob_name}")
    except Exception as e:
        print(f"Error uploading {local_file_path}: {str(e)}")

def main():
    # Validate Azure configuration
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable is not set")

    # Initialize BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

    # Find all building folders in the source
    building_names = [name for name in os.listdir(SRC_BASE) if os.path.isdir(os.path.join(SRC_BASE, name))]

    for building in building_names:
        src_building = os.path.join(SRC_BASE, building)
        
        # --- Copy metrics Excel file(s) ---
        src_metrics_dir = os.path.join(src_building, "07_metrics")
        if os.path.isdir(src_metrics_dir):
            for file in os.listdir(src_metrics_dir):
                if file.endswith(('.xlsx', '.xls')):
                    local_file_path = os.path.join(src_metrics_dir, file)
                    blob_name = f"buildings/{building}/07_metrics/{file}"
                    upload_to_blob_storage(blob_service_client, AZURE_CONTAINER_NAME, local_file_path, blob_name)

        # --- Copy graph folder ---
        src_graph_dir = os.path.join(src_building, "11_abstractbim_plots")
        if os.path.isdir(src_graph_dir):
            for root, _, files in os.walk(src_graph_dir):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    # Create relative path for blob storage
                    rel_path = os.path.relpath(local_file_path, src_building)
                    blob_name = f"buildings/{building}/{rel_path}"
                    upload_to_blob_storage(blob_service_client, AZURE_CONTAINER_NAME, local_file_path, blob_name)

        # --- Copy check folders ---
        for check_folder in ["09_building_inside_envelope", "09_check_building_inside_envelop"]:
            src_check_dir = os.path.join(src_building, check_folder)
            if os.path.isdir(src_check_dir):
                for root, _, files in os.walk(src_check_dir):
                    for file in files:
                        local_file_path = os.path.join(root, file)
                        # Create relative path for blob storage
                        rel_path = os.path.relpath(local_file_path, src_building)
                        blob_name = f"buildings/{building}/{rel_path}"
                        upload_to_blob_storage(blob_service_client, AZURE_CONTAINER_NAME, local_file_path, blob_name)

if __name__ == "__main__":
    main() 