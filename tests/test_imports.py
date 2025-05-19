import os
import sys

def test_imports():
    # Print debug information first
    print("\nDEBUG INFO:")
    print(f"Python path: {sys.path}")
    print(f"Working directory: {os.getcwd()}")
    
    import qto_buccaneer
    print(f"qto_buccaneer location: {qto_buccaneer.__file__}")
    print(f"qto_buccaneer path: {qto_buccaneer.__path__}")
    
    import qto_buccaneer.utils
    print("Successfully imported utils")
    print(f"utils location: {qto_buccaneer.utils.__file__}")
    
    assert True