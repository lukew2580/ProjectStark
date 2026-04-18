from setuptools import setup, find_packages

setup(
    name="hardwareless-ai",
    version="0.3.0",
    description="🧠 GPU/CPU-less hypervector intelligence platform",
    author="Luke West",
    packages=find_packages(exclude=["tests*", "scripts*", "frontend*"]),
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.26",
        "networkx>=3.2",
        "psutil>=5.9",
        "fastapi>=0.104",
        "uvicorn>=0.24",
    ],
    extras_require={
        "all": [
            "aiohttp>=3.9",
            "ctranslate2>=4.0",
            "transformers>=4.36",
            "sentencepiece>=0.1",
        ],
        "discord": ["discord.py>=2.0"],
        "telegram": ["python-telegram-bot>=20.0"],
        "test": [  # Testing dependencies
            "pytest>=8.0.0",
            "pytest-asyncio>=1.2.0",
            "pytest-mock>=3.12.0",
            "pytest-cov>=6.0.0",
            "hypothesis>=6.0.0",
            "locust>=2.0.0",
            "atheris>=2.0.0; python_version>='3.10'",
        ],
    },
    entry_points={
        "console_scripts": [
            "hardwareless=hardwareless.__main__:main",
            "hw-phases=core_engine.setup_manager:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)