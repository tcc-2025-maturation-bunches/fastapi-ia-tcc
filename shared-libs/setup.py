from setuptools import find_packages, setup

setup(
    name="fruit-detection-shared",
    version="0.1.0",
    description="Biblioteca compartilhada para sistema de detecção de frutas",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "boto3>=1.38.27",
        "aioboto3>=15.0.0",
        "pydantic>=2.9.0",
        "fastapi>=0.115.12",
    ],
    python_requires=">=3.9",
    author="tcc-2025-maturation-bunches",
)