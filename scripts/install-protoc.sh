#!/bin/bash
# Install protoc and generate Python code from geode.proto
set -e

PROTOC_VERSION="28.3"

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

if [ "$ARCH" = "x86_64" ]; then
    ARCH="x86_64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    ARCH="aarch_64"
fi

if [ "$OS" = "darwin" ]; then
    OS="osx"
fi

# Download protoc
PROTOC_ZIP="protoc-${PROTOC_VERSION}-${OS}-${ARCH}.zip"
PROTOC_URL="https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/${PROTOC_ZIP}"

echo "Downloading protoc from ${PROTOC_URL}..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="${PROJECT_DIR}/.tools"

mkdir -p "${TOOLS_DIR}"
cd "${TOOLS_DIR}"

if [ ! -f "protoc/bin/protoc" ]; then
    curl -LO "${PROTOC_URL}"
    unzip -o "${PROTOC_ZIP}" -d protoc
    rm -f "${PROTOC_ZIP}"
fi

export PATH="${TOOLS_DIR}/protoc/bin:$PATH"

# Install Python protobuf
echo "Installing Python protobuf dependencies..."
pip install protobuf grpcio-tools

# Create proto directory
mkdir -p "${PROJECT_DIR}/proto"
mkdir -p "${PROJECT_DIR}/geode_client/proto"

# Copy proto file if not exists
if [ ! -f "${PROJECT_DIR}/proto/geode.proto" ]; then
    echo "Proto file not found. Please copy geode.proto to proto/ directory."
    exit 1
fi

# Generate Python code
echo "Generating Python protobuf code..."
cd "${PROJECT_DIR}"
python -m grpc_tools.protoc -I proto --python_out=geode_client/proto --pyi_out=geode_client/proto proto/geode.proto

# Create __init__.py
touch "${PROJECT_DIR}/geode_client/proto/__init__.py"

echo "Done! Protobuf code generated at geode_client/proto/geode_pb2.py"
