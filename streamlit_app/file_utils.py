"""
File utilities for handling both filesystem and Azure Blob Storage
"""
import os
from pathlib import Path
from typing import Union, List, BinaryIO
from azure.storage.blob import ContainerClient, BlobClient

def list_files(base_path: Union[str, ContainerClient], path: str, delimiter: str = None) -> Union[List[str], dict]:
    """
    List files in a directory, handling both filesystem and Azure Blob Storage.
    If delimiter is provided, returns a dict with 'files' and 'prefixes' (virtual directories).
    """
    if isinstance(base_path, ContainerClient):
        # Azure Blob Storage
        prefix = path.lstrip('/')
        if delimiter:
            # Use delimiter to get virtual directory structure
            result = base_path.walk_blobs(name_starts_with=prefix, delimiter=delimiter)
            files = []
            prefixes = []
            for item in result:
                if hasattr(item, 'prefix'):
                    # This is a virtual directory
                    prefixes.append(item.prefix.rstrip('/'))
                else:
                    # This is a file
                    files.append(item.name)
            return {'files': files, 'prefixes': prefixes}
        else:
            # Return full paths of files
            blobs = base_path.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]  # Return full path instead of just filename
    else:
        # Filesystem
        full_path = os.path.join(base_path, path)
        if delimiter:
            # For filesystem, we'll return both files and directories
            files = []
            prefixes = []
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                if os.path.isfile(item_path):
                    files.append(item)
                elif os.path.isdir(item_path):
                    prefixes.append(item)
            return {'files': files, 'prefixes': prefixes}
        else:
            return [os.path.join(path, f) for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]

def read_file(base_path: Union[str, ContainerClient], path: str) -> bytes:
    """Read a file, handling both filesystem and Azure Blob Storage"""
    if isinstance(base_path, ContainerClient):
        # Azure Blob Storage
        blob_client = base_path.get_blob_client(path.lstrip('/'))
        return blob_client.download_blob().readall()
    else:
        # Filesystem
        full_path = os.path.join(base_path, path)
        with open(full_path, 'rb') as f:
            return f.read()

def write_file(base_path: Union[str, ContainerClient], path: str, data: Union[bytes, BinaryIO]) -> None:
    """Write a file, handling both filesystem and Azure Blob Storage"""
    if isinstance(base_path, ContainerClient):
        # Azure Blob Storage
        blob_client = base_path.get_blob_client(path.lstrip('/'))
        if isinstance(data, bytes):
            blob_client.upload_blob(data, overwrite=True)
        else:
            blob_client.upload_blob(data.read(), overwrite=True)
    else:
        # Filesystem
        full_path = os.path.join(base_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            if isinstance(data, bytes):
                f.write(data)
            else:
                f.write(data.read())

def exists(base_path: Union[str, ContainerClient], path: str) -> bool:
    """Check if a file exists, handling both filesystem and Azure Blob Storage"""
    if isinstance(base_path, ContainerClient):
        # Azure Blob Storage
        blob_client = base_path.get_blob_client(path.lstrip('/'))
        return blob_client.exists()
    else:
        # Filesystem
        full_path = os.path.join(base_path, path)
        return os.path.exists(full_path)

def is_dir(base_path: Union[str, ContainerClient], path: str) -> bool:
    """Check if a path is a directory, handling both filesystem and Azure Blob Storage"""
    if isinstance(base_path, ContainerClient):
        # Azure Blob Storage
        prefix = path.lstrip('/')
        if not prefix.endswith('/'):
            prefix += '/'
        blobs = list(base_path.list_blobs(name_starts_with=prefix))
        return len(blobs) > 0
    else:
        # Filesystem
        full_path = os.path.join(base_path, path)
        return os.path.isdir(full_path)

def join_paths(*paths: str) -> str:
    """Join paths, handling both filesystem and Azure Blob Storage"""
    # Remove leading and trailing slashes from all parts
    cleaned_paths = [p.strip('/') for p in paths if p]
    # Join with forward slashes
    return '/'.join(cleaned_paths) 