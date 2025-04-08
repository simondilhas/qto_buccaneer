from setuptools import setup, find_packages
from pathlib import Path
import os

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Import version from _version.py
with open(os.path.join("src", "qto_buccaneer", "_version.py")) as f:
    exec(f.read())

setup(
    name="qto_buccaneer",
    version=__version__,  # Use the imported version
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=requirements,  # Use the requirements from requirements.txt
    extras_require={
        "docs": [
            "pdoc3",
        ],
    },
    python_requires=">=3.8",  # specify minimum Python version if needed
) 