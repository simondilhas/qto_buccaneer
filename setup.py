from setuptools import setup, find_namespace_packages

setup(
    name="qto_buccaneer",
    version="0.1.1",
    package_dir={"": "src"},
    packages=find_namespace_packages(
        where="src",
        include=["qto_buccaneer*"]
    ),
    install_requires=[
        "ifcopenshell>=0.8.1",
        "pandas>=2.2.3",
        "pyyaml>=6.0.2",
        "numpy>=2.2.4",
        "python-dotenv>=1.1.0",
        "openpyxl>=3.1.5",
        "shapely>=2.0.7",
        "plotly>=6.0.1",
        "trimesh>=4.8.3",
        "manifold3d>=3.2.1",
        "scipy>=1.15.0",
        "requests>=2.32.0",
        "pyarrow>=10.0.0",
    ],
    extras_require={
        "docs": [
            "pdoc3>=0.11.6",
            "sphinx>=8.2.3",
            "sphinx-rtd-theme>=3.0.2",
        ],
    },
    python_requires=">=3.8",
) 