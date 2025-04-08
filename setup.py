from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]




setup(
    name="qto_buccaneer",
    version=VERSION,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "ifcopenshell",
        "pandas",
        "pyyaml",
    ],
    extras_require={
        "docs": [
            "pdoc3",
        ],
    },
    python_requires=">=3.8",  # specify minimum Python version if needed
) 