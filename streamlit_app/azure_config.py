"""
Azure deployment configuration
"""
import os

# Azure specific settings
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING', '')
AZURE_CONTAINER_NAME = os.getenv('AZURE_CONTAINER_NAME', 'projects')

# Project paths for Azure
AZURE_PROJECT_BASE_PATH = os.getenv('AZURE_PROJECT_BASE_PATH', '/mnt/data/projects/Seefeld__private')

# Environment detection
def is_azure_environment():
    """Check if running in Azure environment"""
    return os.getenv('AZURE_ENVIRONMENT', 'false').lower() == 'true'

# Get the appropriate base path based on environment
def get_base_project_path():
    """Get the base project path based on the environment"""
    if is_azure_environment():
        return AZURE_PROJECT_BASE_PATH
    return os.getenv('PROJECT_BASE_PATH', '/home/simondilhas/Programmierung/qto_buccaneer/projects/Seefeld__private') 