from setuptools import setup, find_packages

setup(
    name="hardwareless-ai",
    version="0.3.0",
    description="A GPU/CPU-less AI framework that moves with the data flow using HDC.",
    packages=find_packages(exclude=["tests*", "scripts*"]),
    install_requires=[
        "numpy==1.26.4", 
        "networkx==3.2.1", 
        "psutil==5.9.8", 
        "fastapi==0.111.0", 
        "uvicorn==0.29.0"
    ],
    author="Luke West",
)
