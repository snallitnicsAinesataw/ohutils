# setup.py
from setuptools import setup, find_packages

setup(
    name="ohutils",
    version="0.9.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests",
        "cryptography",
    ],
    extras_require={
        "video": ["imageio-ffmpeg"],
    },
    python_requires=">=3.8",
)
