"""
Azure deployment configuration
"""
import os
import streamlit as st
from azure.storage.blob import BlobServiceClient

# Azure specific settings
AZURE_STORAGE_CONNECTION_STRING = st.secrets.get('AZURE_STORAGE_CONNECTION_STRING', '')
AZURE_CONTAINER_NAME = st.secrets.get('AZURE_CONTAINER_NAME', 'projects')

# Project paths for Azure
AZURE_PROJECT_BASE_PATH = st.secrets.get('AZURE_PROJECT_BASE_PATH', '/mnt/data/projects/Seefeld__private')

# Environment detection
def is_azure_environment():
    """Check if running in Azure environment"""
    azure_env = st.secrets.get('AZURE_ENVIRONMENT', False)
    if isinstance(azure_env, str):
        return azure_env.lower() == 'true'
    return bool(azure_env)

def get_blob_service_client():
    """Get Azure Blob Service Client"""
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING secret is not set")
    return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

def get_container_client():
    """Get Azure Container Client"""
    blob_service_client = get_blob_service_client()
    return blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

def get_base_project_path():
    """Get the appropriate base path based on the environment"""
    if is_azure_environment():
        return get_container_client()
    return st.secrets.get('PROJECT_BASE_PATH', '/home/simondilhas/Programmierung/qto_buccaneer/projects/Seefeld__private') 