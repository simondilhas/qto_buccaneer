"""
IFC Download and Loading Module for qto_buccaneer Viewer
Handles downloading and loading IFC files from URLs or local paths.
"""

import ifcopenshell
import requests
from pathlib import Path


class IFCDownloader:
    """Handles downloading and loading IFC files."""
    
    @staticmethod
    def download_and_load(source):
        """
        Download and load an IFC file from URL or local path.
        
        Parameters:
        -----------
        source : str
            URL or local file path to IFC file
            
        Returns:
        --------
        ifcopenshell.file
            Loaded IFC model
        """
        try:
            # Check if source is a URL
            if source.startswith('http://') or source.startswith('https://'):
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                temp_path = Path("temp.ifc")
                with open(temp_path, "wb") as f:
                    f.write(response.content)
                model = ifcopenshell.open(str(temp_path))
            else:
                # Load from local path
                model = ifcopenshell.open(source)
            
            return model
        except requests.RequestException as e:
            raise Exception(f"Error downloading IFC file: {e}")
        except Exception as e:
            raise Exception(f"Error processing IFC file: {e}")
