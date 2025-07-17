from setuptools import setup, find_packages

setup(
    name="fruit-detection-shared",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "boto3>=1.35.0",
        "pydantic>=2.9.0",
        "python-dateutil>=2.9.0",
    ],
    python_requires=">=3.9",
)