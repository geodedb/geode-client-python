"""Unit tests for protobuf serialization/deserialization."""

from pathlib import Path


class TestProtobufRoundtrip:
    """Test protobuf message serialization roundtrip."""

    def test_hello_request_roundtrip(self):
        """Test HelloRequest serialization/deserialization."""
        from geode_client.proto import HelloRequest

        original = HelloRequest(
            username="testuser",
            password="testpass",
            client_name="test-client",
            client_version="1.0.0",
            wanted_conformance="min",
        )

        # Serialize
        data = original.SerializeToString()
        assert len(data) > 0

        # Deserialize
        restored = HelloRequest()
        restored.ParseFromString(data)

        assert restored.username == original.username
        assert restored.password == original.password
        assert restored.client_name == original.client_name
        assert restored.client_version == original.client_version
        assert restored.wanted_conformance == original.wanted_conformance

    def test_execute_request_roundtrip(self):
        """Test ExecuteRequest serialization/deserialization."""
        from geode_client.proto import (
            ExecuteRequest,
            IntKind,
            IntValue,
            Param,
            StringKind,
            StringValue,
            Value,
        )

        original = ExecuteRequest(
            session_id="sess_123",
            query="MATCH (n:Person {name: $name}) WHERE n.age > $age RETURN n",
            params=[
                Param(
                    name="name",
                    value=Value(
                        string_val=StringValue(value="Alice", kind=StringKind.STRING)
                    ),
                ),
                Param(
                    name="age",
                    value=Value(int_val=IntValue(value=25, kind=IntKind.INT)),
                ),
            ],
        )

        # Serialize
        data = original.SerializeToString()
        assert len(data) > 0

        # Deserialize
        restored = ExecuteRequest()
        restored.ParseFromString(data)

        assert restored.session_id == original.session_id
        assert restored.query == original.query
        assert len(restored.params) == 2
        assert restored.params[0].name == "name"
        assert restored.params[0].value.string_val.value == "Alice"
        assert restored.params[1].name == "age"
        assert restored.params[1].value.int_val.value == 25

    def test_execution_response_schema_roundtrip(self):
        """Test ExecutionResponse with schema payload."""
        from geode_client.proto import (
            ColumnDefinition,
            ExecutionResponse,
            SchemaDefinition,
            Status,
        )

        original = ExecutionResponse(
            status=Status(status_class="00000"),
            schema=SchemaDefinition(
                columns=[
                    ColumnDefinition(name="id", type="INT"),
                    ColumnDefinition(name="name", type="STRING"),
                    ColumnDefinition(name="age", type="INT"),
                ]
            ),
        )

        # Serialize
        data = original.SerializeToString()

        # Deserialize
        restored = ExecutionResponse()
        restored.ParseFromString(data)

        assert restored.status.status_class == "00000"
        assert restored.HasField("schema")
        assert len(restored.schema.columns) == 3
        assert restored.schema.columns[0].name == "id"
        assert restored.schema.columns[1].name == "name"
        assert restored.schema.columns[2].name == "age"

    def test_execution_response_page_roundtrip(self):
        """Test ExecutionResponse with data page payload."""
        from geode_client.proto import (
            DataPage,
            ExecutionResponse,
            IntKind,
            IntValue,
            Row,
            Status,
            StringKind,
            StringValue,
            Value,
        )

        original = ExecutionResponse(
            status=Status(status_class="00000"),
            page=DataPage(
                rows=[
                    Row(
                        values=[
                            Value(int_val=IntValue(value=1, kind=IntKind.INT)),
                            Value(
                                string_val=StringValue(
                                    value="Alice", kind=StringKind.STRING
                                )
                            ),
                        ]
                    ),
                    Row(
                        values=[
                            Value(int_val=IntValue(value=2, kind=IntKind.INT)),
                            Value(
                                string_val=StringValue(
                                    value="Bob", kind=StringKind.STRING
                                )
                            ),
                        ]
                    ),
                ],
                final=True,
                ordered=False,
            ),
        )

        # Serialize
        data = original.SerializeToString()

        # Deserialize
        restored = ExecutionResponse()
        restored.ParseFromString(data)

        assert restored.HasField("page")
        assert len(restored.page.rows) == 2
        assert restored.page.final is True
        assert restored.page.rows[0].values[0].int_val.value == 1
        assert restored.page.rows[0].values[1].string_val.value == "Alice"

    def test_quic_client_message_roundtrip(self):
        """Test QuicClientMessage wrapper roundtrip."""
        from geode_client.proto import HelloRequest, QuicClientMessage

        original = QuicClientMessage(
            hello=HelloRequest(
                username="test",
                password="pass",
            )
        )

        # Serialize
        data = original.SerializeToString()

        # Deserialize
        restored = QuicClientMessage()
        restored.ParseFromString(data)

        assert restored.HasField("hello")
        assert restored.hello.username == "test"
        assert restored.hello.password == "pass"

    def test_client_packet_roundtrip(self):
        """Test ClientPacket wrapper roundtrip."""
        from geode_client.proto import ClientPacket, PingRequest, QuicClientMessage

        original = ClientPacket(quic=QuicClientMessage(ping=PingRequest()))

        # Serialize
        data = original.SerializeToString()

        # Deserialize
        restored = ClientPacket()
        restored.ParseFromString(data)

        assert restored.HasField("quic")
        assert restored.quic.HasField("ping")

    def test_value_types_roundtrip(self):
        """Test all Value types roundtrip."""
        from geode_client.proto import (
            DoubleValue,
            IntKind,
            IntValue,
            NullValue,
            StringKind,
            StringValue,
            Value,
        )

        # Test null
        null_val = Value(null_val=NullValue())
        data = null_val.SerializeToString()
        restored = Value()
        restored.ParseFromString(data)
        assert restored.HasField("null_val")

        # Test int
        int_val = Value(int_val=IntValue(value=42, kind=IntKind.INT))
        data = int_val.SerializeToString()
        restored = Value()
        restored.ParseFromString(data)
        assert restored.HasField("int_val")
        assert restored.int_val.value == 42

        # Test double
        double_val = Value(double_val=DoubleValue(value=3.14))
        data = double_val.SerializeToString()
        restored = Value()
        restored.ParseFromString(data)
        assert restored.HasField("double_val")
        assert abs(restored.double_val.value - 3.14) < 0.001

        # Test bool (bool_val is a plain bool in the canonical proto oneof)
        bool_val = Value(bool_val=True)
        data = bool_val.SerializeToString()
        restored = Value()
        restored.ParseFromString(data)
        assert restored.HasField("bool_val")
        assert restored.bool_val is True

        # Test string
        str_val = Value(string_val=StringValue(value="hello", kind=StringKind.STRING))
        data = str_val.SerializeToString()
        restored = Value()
        restored.ParseFromString(data)
        assert restored.HasField("string_val")
        assert restored.string_val.value == "hello"


class TestJsonRemovalGuard:
    """Test that legacy JSON protocol code is removed."""

    def test_no_json_protocol_module(self):
        """Verify that old hand-rolled proto.py is removed."""
        from geode_client import client

        # The old proto.py module should not exist
        # Check that client doesn't have the old proto imports
        assert not hasattr(client, "encode_varint")
        assert not hasattr(client, "decode_varint")
        assert not hasattr(client, "WIRE_VARINT")

    def test_no_json_encoding_in_client(self):
        """Verify that client doesn't use JSON encoding."""
        import inspect

        import geode_client.client as client_module

        source = inspect.getsource(client_module)

        # Should not have JSON-specific patterns
        assert "json.dumps" not in source
        assert "json.loads" not in source
        assert '"type": "HELLO"' not in source
        assert '"type": "RUN_GQL"' not in source

    def test_uses_generated_protobuf(self):
        """Verify that client uses generated protobuf code."""
        from geode_client.proto import geode_pb2

        # Should have DESCRIPTOR attribute (generated protobuf)
        assert hasattr(geode_pb2, "DESCRIPTOR")

        # Should have generated message classes
        assert hasattr(geode_pb2, "HelloRequest")
        assert hasattr(geode_pb2, "ExecuteRequest")
        assert hasattr(geode_pb2, "ClientPacket")

    def test_old_proto_py_deleted(self):
        """Verify that the old hand-rolled proto.py file doesn't exist."""
        import geode_client

        package_dir = Path(geode_client.__file__).parent
        old_proto_path = package_dir / "proto.py"

        # Should not exist as a file (it's now a package)
        assert not old_proto_path.exists(), "Old proto.py should be deleted"

    def test_proto_is_package(self):
        """Verify that proto is now a package with generated code."""
        from geode_client import proto

        # proto should be a package (has __path__)
        assert hasattr(proto, "__path__")

        # Should have generated modules
        from geode_client.proto import geode_pb2, geode_pb2_grpc

        assert geode_pb2 is not None
        assert geode_pb2_grpc is not None


class TestGrpcServiceStub:
    """Test gRPC service stub is generated correctly."""

    def test_grpc_stub_exists(self):
        """Verify GeodeServiceStub is available."""
        from geode_client.proto import GeodeServiceStub

        assert GeodeServiceStub is not None

    def test_grpc_servicer_methods(self):
        """Verify GeodeServiceServicer has expected methods."""
        from geode_client.proto.geode_pb2_grpc import GeodeServiceServicer

        # Check that servicer has the expected methods (for server implementation)
        # Note: Pull is QUIC-only; the canonical gRPC service uses Execute streaming
        assert hasattr(GeodeServiceServicer, "Handshake")
        assert hasattr(GeodeServiceServicer, "Execute")
        assert hasattr(GeodeServiceServicer, "Ping")
        assert hasattr(GeodeServiceServicer, "Begin")
        assert hasattr(GeodeServiceServicer, "Commit")
        assert hasattr(GeodeServiceServicer, "Rollback")
        assert hasattr(GeodeServiceServicer, "GetCdcDiagnostics")
        assert hasattr(GeodeServiceServicer, "ControlCdc")
