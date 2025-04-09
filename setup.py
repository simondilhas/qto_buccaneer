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
        "ifcopenshell",
        "pandas",
        "pyyaml",
        "pdoc3",
    ],
    python_requires=">=3.8",
) 