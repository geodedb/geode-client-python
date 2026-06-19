"""Unit tests for Node/Edge/Path typed values and converters."""

import pytest

from geode_client import Edge, Node, Path, Value, ValueKind, as_edge, as_node, as_path


def _node_value(node_id, labels, props):
    return Value(
        kind=ValueKind.NODE,
        object_value={
            "id": Value(kind=ValueKind.INT, int_value=node_id),
            "labels": Value(
                kind=ValueKind.ARRAY,
                array_value=[
                    Value(kind=ValueKind.STRING, str_value=label) for label in labels
                ],
            ),
            "properties": Value(
                kind=ValueKind.OBJECT,
                object_value={
                    k: Value(kind=ValueKind.STRING, str_value=v)
                    for k, v in props.items()
                },
            ),
        },
    )


def _edge_value(edge_id, start, end, etype, props):
    return Value(
        kind=ValueKind.EDGE,
        object_value={
            "id": Value(kind=ValueKind.INT, int_value=edge_id),
            "start_node": Value(kind=ValueKind.INT, int_value=start),
            "end_node": Value(kind=ValueKind.INT, int_value=end),
            "type": Value(kind=ValueKind.STRING, str_value=etype),
            "properties": Value(
                kind=ValueKind.OBJECT,
                object_value={
                    k: Value(kind=ValueKind.STRING, str_value=v)
                    for k, v in props.items()
                },
            ),
        },
    )


class TestAsNode:
    def test_basic(self):
        node = as_node(_node_value(1, ["Person", "User"], {"name": "Alice"}))
        assert isinstance(node, Node)
        assert node.id == 1
        assert node.labels == ["Person", "User"]
        assert node.properties == {"name": "Alice"}

    def test_wrong_kind_raises(self):
        with pytest.raises(ValueError):
            as_node(Value(kind=ValueKind.INT, int_value=1))


class TestAsEdge:
    def test_basic(self):
        edge = as_edge(_edge_value(10, 1, 2, "KNOWS", {"since": "2020"}))
        assert isinstance(edge, Edge)
        assert edge.id == 10
        assert edge.start_node == 1
        assert edge.end_node == 2
        assert edge.type == "KNOWS"
        assert edge.properties == {"since": "2020"}

    def test_wrong_kind_raises(self):
        with pytest.raises(ValueError):
            as_edge(Value(kind=ValueKind.STRING, str_value="x"))


class TestAsPath:
    def test_nested_assembly(self):
        n1 = _node_value(1, ["Person"], {"name": "A"})
        n2 = _node_value(2, ["Person"], {"name": "B"})
        e1 = _edge_value(10, 1, 2, "KNOWS", {})
        path_val = Value(
            kind=ValueKind.PATH,
            object_value={
                "nodes": Value(kind=ValueKind.ARRAY, array_value=[n1, n2]),
                "edges": Value(kind=ValueKind.ARRAY, array_value=[e1]),
            },
        )
        path = as_path(path_val)
        assert isinstance(path, Path)
        assert [n.id for n in path.nodes] == [1, 2]
        assert len(path.edges) == 1
        assert path.edges[0].type == "KNOWS"
        assert isinstance(path.nodes[0], Node)
        assert isinstance(path.edges[0], Edge)

    def test_empty_path(self):
        path_val = Value(
            kind=ValueKind.PATH,
            object_value={
                "nodes": Value(kind=ValueKind.ARRAY, array_value=[]),
                "edges": Value(kind=ValueKind.ARRAY, array_value=[]),
            },
        )
        path = as_path(path_val)
        assert path.nodes == []
        assert path.edges == []

    def test_wrong_kind_raises(self):
        with pytest.raises(ValueError):
            as_path(Value(kind=ValueKind.OBJECT, object_value={}))
