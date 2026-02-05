"""
Setup script for Geode Python client.
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="geode-client",
    version="0.3.10",
    author="CodePros",
    author_email="codepros@devnw.com",
    description="Python QUIC/gRPC client library for Geode graph database",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/devnw/codepros/geode/geode-client-python",
    project_urls={
        "Homepage": "https://gitlab.com/devnw/codepros/geode",
        "Bug Tracker": "https://gitlab.com/devnw/codepros/geode/geode-client-python/-/issues",
        "Repository": "https://gitlab.com/devnw/codepros/geode/geode-client-python",
        "Documentation": "https://gitlab.com/devnw/codepros/geode/geode-client-python/-/blob/main/README.md",
    },
    license="Apache-2.0",
    packages=find_packages(),
    package_data={
        "geode_client": ["proto/*.py", "proto/*.pyi"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.9",
    install_requires=[
        "aioquic>=0.9.0",  # QUIC transport
        "protobuf>=6.31.0",  # Protobuf wire format (generated with 6.31.1)
        "grpcio>=1.50.0",  # gRPC transport
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-benchmark>=4.0.0",
            "hypothesis>=6.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
            "pre-commit>=3.0.0",
            "commitizen>=3.0.0",
            "grpcio-tools>=1.50.0",  # For protobuf code generation
        ],
        "integration": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
        "benchmark": [
            "pytest>=7.0.0",
            "pytest-benchmark>=4.0.0",
        ],
        "property": [
            "pytest>=7.0.0",
            "hypothesis>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [],
    },
)
