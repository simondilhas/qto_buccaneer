import requests
import dotenv
import os
from pathlib import Path
from typing import Optional

def find_env_file():
    # Try current working directory first
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env
    
    # Try project root (where the package is installed)
    project_root = Path(__file__).parent.parent.parent.parent.parent
    project_env = project_root / ".env"
    if project_env.exists():
        return project_env
    
    # Try going up from current working directory
    current = Path.cwd()
    while current != current.parent:  # Stop at root directory
        env_file = current / ".env"
        if env_file.exists():
            return env_file
        current = current.parent
    
    return None

# Find and load .env file
env_path = find_env_file()
if env_path:
    print(f"Found .env file at: {env_path}")
    # Print contents of .env file for debugging
    with open(env_path, 'r') as f:
        print("Contents of .env file:")
        for line in f:
            if 'ABSTRACTBIM_API_URL' in line:
                print(line.strip())
    
    # Force reload of environment variables
    dotenv.load_dotenv(env_path, override=True)
else:
    print("Warning: No .env file found in any parent directory")

# Get the API URL and print debug info
abstract_bim_api_url = os.getenv("ABSTRACTBIM_API_URL")
print(f"Loaded ABSTRACTBIM_API_URL: {abstract_bim_api_url}")
print(f"Environment variables after loading: {dict(os.environ)}")

def _upload_blob(sas_url: str, data: bytes) -> bool:
    headers = {"x-ms-blob-type": "BlockBlob"}
    try:
        response = requests.put(sas_url, data=data, headers=headers, timeout=600)
        response.raise_for_status()
        print("Upload successful!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Upload failed: {str(e)}")
        return False

def process_ifc_file_with_abstractbim_api(input_file: str, output_file: str) -> Optional[str]:
    api_key = os.getenv("ABSTRACTBIM_API_KEY")
    if not api_key:
        raise ValueError("ABSTRACTBIM_API_KEY environment variable is not set")

    headers = {"Authorization": api_key}
    
    try:
        # Get upload URL
        response = requests.get(
            f"{abstract_bim_api_url}/generic/upload_url",
            headers=headers,
            timeout=1000
        )
        response.raise_for_status()
        url = response.text

        # Read and upload IFC file
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        with open(input_path, 'rb') as f:
            ifc_data = f.read()
        
        if not _upload_blob(url, ifc_data):
            return None

        # Process IFC file
        data = {"url": url}
        response = requests.post(
            f"{abstract_bim_api_url}/generic/normalize_ifc",
            json=data,
            headers=headers,
            timeout=1000
        )
        response.raise_for_status()
        result = response.json()

        # Download processed file
        response = requests.get(result["ifc"], timeout=300)
        response.raise_for_status()
        
        output_path = Path(output_file)
        if output_path.is_dir():
            # If output path is a directory, create a new filename based on input file
            input_filename = Path(input_file).stem
            output_path = output_path / f"{input_filename}_abstractBIM.ifc"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(response.text)
            
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
