#!/bin/bash
# Generate Python protobuf code from proto/geode.proto
#
# Usage: ./scripts/generate_proto.sh
#
# Prerequisites:
#   pip install grpcio-tools
#
# Or run ./scripts/install-protoc.sh first

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_DIR/proto"
OUTPUT_DIR="$PROJECT_DIR/geode_client/proto"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

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
