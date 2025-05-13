from qto_buccaneer._utils.abstract.abstractbim_upload import process_ifc_file_with_abstractbim_api

def get_abstractbim_from_api(ifc_path: str, output_path: str) -> str:
    """
    Upload an IFC file to AbstractBIM and return the path to the processed file.
    To use this function, you need to set the ABSTRACTBIM_API_KEY environment variable.
    You can get the API by contacting Simon Dilhas at simon.dilhas@abstractbim.com
    
    Args:
        ifc_path: Path to the IFC file to upload.
        output_path: Path to save the processed IFC file.
        
    Returns:
        str: Path to the processed IFC file.
    """
    return process_ifc_file_with_abstractbim_api(ifc_path, output_path)




