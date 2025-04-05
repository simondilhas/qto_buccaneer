"""
Documentation generation script for QTO Buccaneer.
"""
import os
import subprocess

def generate_docs():
    """Generate HTML documentation using pdoc."""
    # Get the absolute path to the source directory
    src_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '..',
        'src',
        'qto_buccaneer'
    ))
    
    # Create docs directory if it doesn't exist
    docs_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '..',
        'docs'
    ))
    if not os.path.exists(docs_path):
        os.makedirs(docs_path)
    
    # Generate documentation
    print(f"Generating documentation for: {src_path}")
    print(f"Output directory: {docs_path}")
    
    try:
        result = subprocess.run([
            'pdoc',
            '--html',
            '--output-dir', docs_path,
            '--force',
            src_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Documentation generated successfully!")
        else:
            print("Error generating documentation:")
            print(result.stderr)
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    generate_docs() 