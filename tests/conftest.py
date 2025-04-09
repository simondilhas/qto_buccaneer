import os
import sys
import pytest

def pytest_configure(config):
    """Print debug info at start of test session."""
    print("\nTest Session Debug Info:")
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    try:
        import qto_buccaneer
        print(f"qto_buccaneer location: {qto_buccaneer.__file__}")
    except ImportError as e:
        print(f"Failed to import qto_buccaneer: {e}") 