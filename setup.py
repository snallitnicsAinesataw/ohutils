# setup.py
from setuptools import setup, find_packages

setup(
    name="ohutils",
    version="0.7.0",
    packages=find_packages(where="."),
    package_dir={"": "."},
    install_requires=[
        "requests",
        "cryptography"
    ],
    python_requires=">=3.8",
)
