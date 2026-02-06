#!/bin/bash
# Generate Python protobuf code from the canonical geode.proto
#
# Usage: ./scripts/generate_proto.sh
#
# Prerequisites:
#   pip install grpcio-tools
#
# This script copies the canonical proto from the server source and generates
# Python protobuf + gRPC stubs.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_DIR/proto"
OUTPUT_DIR="$PROJECT_DIR/geode_client/proto"
CANONICAL_PROTO="$PROJECT_DIR/../geode/src/proto/geode.proto"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"
mkdir -p "$PROTO_DIR"

# Copy canonical proto if available
if [ -f "$CANONICAL_PROTO" ]; then
    echo "Copying canonical proto from $CANONICAL_PROTO"
    cp "$CANONICAL_PROTO" "$PROTO_DIR/geode.proto"
else
    echo "Warning: Canonical proto not found at $CANONICAL_PROTO"
    echo "Using existing proto at $PROTO_DIR/geode.proto"
fi

if [ ! -f "$PROTO_DIR/geode.proto" ]; then
    echo "Error: No proto file found at $PROTO_DIR/geode.proto"
    exit 1
fi

echo "Generating Python protobuf code..."
echo "  Proto file: $PROTO_DIR/geode.proto"
echo "  Output dir: $OUTPUT_DIR"

# Generate protobuf and gRPC code
python -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$OUTPUT_DIR" \
    --pyi_out="$OUTPUT_DIR" \
    --grpc_python_out="$OUTPUT_DIR" \
    "$PROTO_DIR/geode.proto"

# Fix the import in the generated gRPC file
# Change: import geode_pb2 as geode__pb2
# To:     from . import geode_pb2 as geode__pb2
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' 's/^import geode_pb2 as geode__pb2$/from . import geode_pb2 as geode__pb2/' "$OUTPUT_DIR/geode_pb2_grpc.py"
else
    # Linux
    sed -i 's/^import geode_pb2 as geode__pb2$/from . import geode_pb2 as geode__pb2/' "$OUTPUT_DIR/geode_pb2_grpc.py"
fi

echo "Done! Generated files:"
ls -la "$OUTPUT_DIR"/*.py "$OUTPUT_DIR"/*.pyi 2>/dev/null || true
