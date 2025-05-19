import requests
import dotenv
import os
import json
import time
from pathlib import Path
from typing import Optional
from azure.storage.blob import BlobServiceClient, BlobClient
from datetime import datetime

dotenv.load_dotenv()

# Get the API URL and connection string
abstract_bim_api_url = os.getenv("ABSTRACTBIM_API_URL", "https://abstractbim.azurewebsites.net")
connection_string = os.getenv("BLOB_STORAGE_ABSTRACTBIM_PROD_CONNECTION_STRING")

# Determine environment
dev = os.getenv("ABSTRACTBIM_DEV", "false").lower() == "true"
blobsuffix = "dev" if dev else "prod"
urlprefix = "dev" if dev else ""

def _upload_to_blob(container_name: str, blob_name: str, data: str) -> bool:
    try:
        blob = BlobClient.from_connection_string(
            conn_str=connection_string,
            container_name=container_name,
            blob_name=blob_name
        )
        blob.upload_blob(data)
        return True
    except Exception as e:
        print(f"Upload failed: {str(e)}")
        return False

def process_ifc_file_with_abstractbim_api(input_file: str, output_file: str) -> Optional[str]:
    api_key = os.getenv("ABSTRACTBIM_API_KEY")
    if not api_key:
        raise ValueError("ABSTRACTBIM_API_KEY environment variable is not set")

    headers = {"Authorization": api_key}
    container_name_in = f"abstractbimin{blobsuffix}"
    container_name_out = f"abstractbimout{blobsuffix}"
    
    try:
        # Read IFC file
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        with open(input_path, 'r') as f:
            ifc_data = f.read()

        # Generate unique filename with timestamp for blob storage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{input_path.stem}_{timestamp}"

        # Upload to blob storage
        if not _upload_to_blob(container_name_in, unique_filename, ifc_data):
            return None

        # Prepare request data
        params = {
            "output": ["ifc"],
            "createCoverings": True,
            "create_space_boundaries": True,
            "gross_area_calculation": True,
            "ifc4": True,
            "openings": True
        }

        data = {
            "blob": unique_filename,
            "filename": unique_filename,
            "filetype": "ifc",
            "user": "qto_buccaneer",
            "params": json.dumps(params),
            "project": {"projectname": "qto_buccaneer"}
        }

        # Start normalization process
        response = requests.post(
            f"https://{urlprefix}abstractbim.azurewebsites.net/normalize",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        task_id = result["data"]["task_id"]

        # Poll for completion
        while True:
            time.sleep(5)
            status_response = requests.get(
                f"https://{urlprefix}abstractbim.azurewebsites.net/normalize/status/{task_id}",
                headers=headers
            )
            status_result = status_response.json()
            if status_result["status"] == "finished":
                break

        # Download results
        results = status_result["result"]["normalizeData"]
        output_path = Path(output_file)
        if output_path.is_dir():
            # Use original filename without timestamp for the output file
            output_path = output_path / f"{input_path.stem}_abstractBIM.ifc"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)

        for k, fname in results.items():
            blob = BlobClient.from_connection_string(
                conn_str=connection_string,
                container_name=container_name_out,
                blob_name=fname
            )
            blob_data = blob.download_blob()
            with open(output_path, "wb") as f:
                f.write(blob_data.read())
            
        return str(output_path)

    except (requests.exceptions.RequestException, FileNotFoundError, ValueError) as e:
        print(f"Error processing IFC file: {str(e)}")
        return None

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_file = script_dir / "001_test_building.ifc"
    output_file = script_dir / "001_test_building_abstractBIM.ifc"
    
    result = process_ifc_file_with_abstractbim_api(str(input_file), str(output_file))
    if result:
        print(f"Successfully processed IFC file. Output saved to: {result}")
    else:
        print("Failed to process IFC file")
