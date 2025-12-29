"""
Setup script for Geode Python client.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="geode-client",
    version="0.1.0",
    author="Geode Contributors",
    author_email="contact@example.com",
    description="Python QUIC client library for Geode graph database",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/devnw/geode/geode-client-python",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.9",
    install_requires=[
        "aioquic>=0.9.0",  # QUIC support (required)
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [],
    },
)
