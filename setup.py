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
    version="0.5.1",
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
        # Floors must match requirements.txt and are proven importable by
        # scripts/check_min_deps.py (CI job test:min-deps), SONNY-6723.
        "aioquic>=0.9.22",  # QUIC transport (StopSendingReceived added in 0.9.22)
        # Gencode 6.31.0 needs runtime >=6.31.0; 6.33.5 fixes CVE-2025-4565 and
        # CVE-2026-0994. Runtime 7.x accepts this gencode.
        "protobuf>=6.33.5",
        # geode_pb2_grpc.py raises at import below GRPC_GENERATED_VERSION.
        "grpcio>=1.73.1",  # gRPC transport
        # CVE-2026-27459/27448 fixed in 26.0.0; 26.4.0 admits cryptography 50.
        "pyOpenSSL>=26.4.0",
        "cryptography>=50.0.0",  # CVE-2026-69247/69248/69249 fixes
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-benchmark>=4.0.0",
            "hypothesis>=6.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
            "Pygments>=2.19.0",  # CVE fix: ReDoS
            "black>=25.0.0",  # CVE fix
            "pre-commit>=3.0.0",
            "commitizen>=3.0.0",
            "grpcio-tools>=1.73.1",  # Generator of the committed stubs
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
