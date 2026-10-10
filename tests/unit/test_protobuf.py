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

    def test_hello_request_has_tenant_id_and_role_fields(self):
        """GAP-0841: HelloRequest carries tenant_id (field 3) and role (field 8).

        These optional fields enable multi-tenant isolation (tenant_id) and
        FLE field-level access control (role) from the Python client.
        """
        from geode_client.proto import HelloRequest

        fields = HelloRequest.DESCRIPTOR.fields_by_name
        assert "tenant_id" in fields, "HelloRequest missing tenant_id field"
        assert fields["tenant_id"].number == 3
        assert "role" in fields, "HelloRequest missing role field (GAP-0841)"
        assert fields["role"].number == 8

        # Both are proto3 `optional`, so they have explicit presence.
        assert fields["tenant_id"].has_presence
        assert fields["role"].has_presence

    def test_hello_request_tenant_role_roundtrip(self):
        """GAP-0841: tenant_id + role survive a serialization roundtrip."""
        from geode_client.proto import HelloRequest

        original = HelloRequest(
            username="testuser",
            password="testpass",
            client_name="test-client",
            client_version="1.0.0",
            wanted_conformance="min",
            tenant_id="acme",
            role="analyst",
        )

        restored = HelloRequest()
        restored.ParseFromString(original.SerializeToString())

        assert restored.HasField("tenant_id")
        assert restored.tenant_id == "acme"
        assert restored.HasField("role")
        assert restored.role == "analyst"

    def test_hello_request_tenant_role_optional_presence(self):
        """GAP-0841: unset tenant_id/role are not serialized (optional presence)."""
        from geode_client.proto import HelloRequest

        original = HelloRequest(username="u", password="p")
        restored = HelloRequest()
        restored.ParseFromString(original.SerializeToString())

        assert not restored.HasField("tenant_id")
        assert not restored.HasField("role")

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


class TestProtoDrift:
    """GAP-0841: guard the vendored proto against the canonical server proto."""

    def _repo_root(self) -> Path:
        # tests/unit/test_protobuf.py -> repo root is two parents up.
        return Path(__file__).resolve().parents[2]

    def test_vendored_proto_declares_role_field(self):
        """The vendored proto/geode.proto must declare HelloRequest.role = 8."""
        proto_path = self._repo_root() / "proto" / "geode.proto"
        text = proto_path.read_text()

        # Isolate the HelloRequest message body.
        start = text.index("message HelloRequest")
        body = text[start : text.index("}", start)]
        assert "tenant_id = 3" in body, "vendored HelloRequest missing tenant_id = 3"
        assert "role = 8" in body, "vendored HelloRequest missing role = 8 (GAP-0841)"

    def test_vendored_hello_request_matches_canonical(self):
        """If the canonical server proto is reachable, HelloRequest fields match.

        Detects drift between the vendored proto and the server source. Skips
        when the sibling geode server checkout is not present (e.g. in CI that
        only clones the client repo).
        """
        canonical = self._repo_root().parent / "geode" / "src" / "proto" / "geode.proto"
        if not canonical.exists():
            import pytest

            pytest.skip(f"canonical server proto not found at {canonical}")

        def hello_fields(text: str) -> set[str]:
            start = text.index("message HelloRequest")
            body = text[start : text.index("}", start)]
            fields = set()
            for line in body.splitlines():
                line = line.split("//")[0].strip().rstrip(";")
                if "=" in line and line:
                    # e.g. "optional string role = 8" -> ("name", "number")
                    decl, num = line.rsplit("=", 1)
                    name = decl.split()[-1]
                    fields.add(f"{name}={num.strip()}")
            return fields

        vendored = (self._repo_root() / "proto" / "geode.proto").read_text()
        server = canonical.read_text()
        assert hello_fields(vendored) == hello_fields(server), (
            "vendored HelloRequest has drifted from the canonical server proto"
        )


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


class TestProtoValueConversion:
    """Tests for _proto_value_to_python complex type handling."""

    def _make_conn(self):
        from geode_client.client import Connection

        return Connection.__new__(Connection)

    def test_edge_val_conversion(self):
        """Test that edge_val proto is converted with correct field names."""
        from geode_client.proto import EdgeValue, IntValue, MapEntry
        from geode_client.proto import Value as ProtoValue
        from geode_client.types import ValueKind

        edge = EdgeValue(
            id=100,
            from_id=1,
            to_id=2,
            label="KNOWS",
            properties=[
                MapEntry(key="since", value=ProtoValue(int_val=IntValue(value=2020)))
            ],
        )
        proto_val = ProtoValue(edge_val=edge)

        conn = self._make_conn()
        val = conn._proto_value_to_python(proto_val, "EDGE")

        assert val.kind == ValueKind.EDGE
        raw = val.raw_value
        assert raw["type"] == "KNOWS"
        assert raw["start_node"] == 1
        assert raw["end_node"] == 2
        assert raw["id"] == 100
        assert raw["properties"]["since"] == 2020
        assert "label" not in raw
        assert "from_id" not in raw

    def test_node_val_conversion(self):
        """Test that node_val proto is converted correctly."""
        from geode_client.proto import MapEntry, NodeValue, StringValue
        from geode_client.proto import Value as ProtoValue
        from geode_client.types import ValueKind

        node = NodeValue(
            id=42,
            labels=["Person"],
            properties=[
                MapEntry(
                    key="name", value=ProtoValue(string_val=StringValue(value="Alice"))
                )
            ],
        )
        proto_val = ProtoValue(node_val=node)

        conn = self._make_conn()
        val = conn._proto_value_to_python(proto_val, "NODE")

        assert val.kind == ValueKind.NODE
        raw = val.raw_value
        assert raw["id"] == 42
        assert raw["labels"] == ["Person"]
        assert raw["properties"]["name"] == "Alice"

    def test_list_val_conversion(self):
        """Test that list_val proto is converted to ARRAY."""
        from geode_client.proto import IntValue, ListValue
        from geode_client.proto import Value as ProtoValue
        from geode_client.types import ValueKind

        list_val = ListValue(
            values=[
                ProtoValue(int_val=IntValue(value=1)),
                ProtoValue(int_val=IntValue(value=2)),
            ]
        )
        proto_val = ProtoValue(list_val=list_val)

        conn = self._make_conn()
        val = conn._proto_value_to_python(proto_val, "")

        assert val.kind == ValueKind.ARRAY
        assert len(val.array_value) == 2
        assert val.array_value[0].int_value == 1

    def test_map_val_conversion(self):
        """Test that map_val proto is converted to OBJECT."""
        from geode_client.proto import MapEntry, MapValue, StringValue
        from geode_client.proto import Value as ProtoValue
        from geode_client.types import ValueKind

        map_val = MapValue(
            entries=[
                MapEntry(
                    key="color", value=ProtoValue(string_val=StringValue(value="red"))
                ),
            ]
        )
        proto_val = ProtoValue(map_val=map_val)

        conn = self._make_conn()
        val = conn._proto_value_to_python(proto_val, "")

        assert val.kind == ValueKind.OBJECT
        assert val.object_value["color"].str_value == "red"

    def test_path_val_conversion(self):
        """Test that path_val proto is converted correctly."""
        from geode_client.proto import EdgeValue, NodeValue, PathValue
        from geode_client.proto import Value as ProtoValue
        from geode_client.types import ValueKind

        path = PathValue(
            nodes=[NodeValue(id=1, labels=["A"]), NodeValue(id=2, labels=["B"])],
            edges=[EdgeValue(id=10, from_id=1, to_id=2, label="REL")],
        )
        proto_val = ProtoValue(path_val=path)

        conn = self._make_conn()
        val = conn._proto_value_to_python(proto_val, "PATH")

        assert val.kind == ValueKind.PATH
        raw = val.raw_value
        assert len(raw["nodes"]) == 2
        assert len(raw["edges"]) == 1
        assert raw["edges"][0]["type"] == "REL"
        assert raw["edges"][0]["start_node"] == 1
