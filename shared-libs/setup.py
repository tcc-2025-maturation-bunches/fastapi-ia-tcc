from setuptools import find_packages, setup

setup(
    name="fruit-detection-shared",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "boto3>=1.38.27",
        "pydantic>=2.9.0",
        "fastapi>=0.115.12",
        "aioboto3>=15.0.0",
    ],
    python_requires=">=3.9",
)
