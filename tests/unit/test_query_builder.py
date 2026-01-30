"""Unit tests for Geode query builder."""

import pytest
from geode_client import QueryBuilder, PatternBuilder, PredicateBuilder, EdgeDirection
from geode_client.query_builder import find_friends, create_person, find_shortest_path


class TestQueryBuilderBasic:
    """Tests for basic QueryBuilder operations."""

    def test_empty_builder(self):
        """Test empty query builder."""
        qb = QueryBuilder()
        text, params = qb.build()
        assert text == ""
        assert params == {}

    def test_simple_return(self):
        """Test simple RETURN query."""
        qb = QueryBuilder().return_("1 AS x")
        text, params = qb.build()
        assert text == "RETURN 1 AS x"
        assert params == {}

    def test_return_multiple(self):
        """Test RETURN with multiple expressions."""
        qb = QueryBuilder().return_("a", "b", "c")
        text, params = qb.build()
        assert text == "RETURN a, b, c"


class TestQueryBuilderMatch:
    """Tests for MATCH clause."""

    def test_match_basic(self):
        """Test basic MATCH clause."""
        qb = QueryBuilder().match("(n)").return_("n")
        text, params = qb.build()
        assert "MATCH (n)" in text
        assert "RETURN n" in text

    def test_match_with_labels(self):
        """Test MATCH with node labels."""
        qb = QueryBuilder().match("(p:Person)").return_("p")
        text, _ = qb.build()
        assert "MATCH (p:Person)" in text

    def test_match_with_properties(self):
        """Test MATCH with properties."""
        qb = QueryBuilder().match("(p:Person {name: 'Alice'})").return_("p")
        text, _ = qb.build()
        assert "(p:Person {name: 'Alice'})" in text

    def test_match_relationship(self):
        """Test MATCH with relationship."""
        qb = QueryBuilder().match("(a)-[r:KNOWS]->(b)").return_("a", "b")
        text, _ = qb.build()
        assert "MATCH (a)-[r:KNOWS]->(b)" in text


class TestQueryBuilderOptionalMatch:
    """Tests for OPTIONAL MATCH clause."""

    def test_optional_match(self):
        """Test OPTIONAL MATCH clause."""
        qb = QueryBuilder().match("(p:Person)").optional_match("(p)-[:KNOWS]->(friend)").return_("p", "friend")
        text, _ = qb.build()
        assert "MATCH (p:Person)" in text
        assert "OPTIONAL MATCH (p)-[:KNOWS]->(friend)" in text

    def test_optional_match_alone(self):
        """Test OPTIONAL MATCH without regular MATCH."""
        qb = QueryBuilder().optional_match("(n)").return_("n")
        text, _ = qb.build()
        assert text.startswith("OPTIONAL MATCH")


class TestQueryBuilderWhere:
    """Tests for WHERE clause."""

    def test_where_simple(self):
        """Test simple WHERE clause."""
        qb = QueryBuilder().match("(n)").where("n.age > 25").return_("n")
        text, _ = qb.build()
        assert "WHERE n.age > 25" in text

    def test_where_compound(self):
        """Test compound WHERE clause."""
        qb = QueryBuilder().match("(n)").where("n.age > 25 AND n.name = 'Alice'").return_("n")
        text, _ = qb.build()
        assert "AND" in text

    def test_where_with_parameter(self):
        """Test WHERE with parameter reference."""
        qb = QueryBuilder().match("(n)").where("n.age > $minAge").return_("n")
        text, _ = qb.build()
        assert "$minAge" in text


class TestQueryBuilderWith:
    """Tests for WITH clause."""

    def test_with_basic(self):
        """Test basic WITH clause."""
        qb = QueryBuilder().match("(n)").with_("n", "count(*) AS cnt").return_("n", "cnt")
        text, _ = qb.build()
        assert "WITH n, count(*) AS cnt" in text

    def test_with_aggregation(self):
        """Test WITH with aggregation."""
        qb = (QueryBuilder()
              .match("(n:Person)")
              .with_("n.city AS city", "count(n) AS cnt")
              .return_("city", "cnt"))
        text, _ = qb.build()
        assert "WITH n.city AS city, count(n) AS cnt" in text


class TestQueryBuilderOrderBy:
    """Tests for ORDER BY clause."""

    def test_order_by_single(self):
        """Test single ORDER BY."""
        qb = QueryBuilder().match("(n)").return_("n").order_by("n.name")
        text, _ = qb.build()
        assert "ORDER BY n.name" in text

    def test_order_by_multiple(self):
        """Test multiple ORDER BY."""
        qb = QueryBuilder().match("(n)").return_("n").order_by("n.age DESC", "n.name ASC")
        text, _ = qb.build()
        assert "ORDER BY n.age DESC, n.name ASC" in text

    def test_order_by_desc(self):
        """Test ORDER BY DESC."""
        qb = QueryBuilder().match("(n)").return_("n").order_by("n.age DESC")
        text, _ = qb.build()
        assert "DESC" in text


class TestQueryBuilderLimit:
    """Tests for LIMIT clause."""

    def test_limit(self):
        """Test LIMIT clause."""
        qb = QueryBuilder().match("(n)").return_("n").limit(10)
        text, _ = qb.build()
        assert "LIMIT 10" in text

    def test_limit_one(self):
        """Test LIMIT 1."""
        qb = QueryBuilder().match("(n)").return_("n").limit(1)
        text, _ = qb.build()
        assert "LIMIT 1" in text

    def test_limit_zero(self):
        """Test LIMIT 0 is valid."""
        qb = QueryBuilder().match("(n)").return_("n").limit(0)
        text, _ = qb.build()
        assert "LIMIT 0" in text

    def test_limit_negative_raises(self):
        """Test negative LIMIT raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            QueryBuilder().limit(-1)

    def test_limit_float_raises(self):
        """Test float LIMIT raises ValueError."""
        with pytest.raises(ValueError, match="integer"):
            QueryBuilder().limit(10.5)

    def test_limit_string_raises(self):
        """Test string LIMIT raises ValueError."""
        with pytest.raises(ValueError, match="integer"):
            QueryBuilder().limit("10")

    def test_limit_bool_raises(self):
        """Test bool LIMIT raises ValueError (bool is int subclass)."""
        with pytest.raises(ValueError, match="integer"):
            QueryBuilder().limit(True)


class TestQueryBuilderOffset:
    """Tests for OFFSET clause."""

    def test_offset(self):
        """Test OFFSET clause."""
        qb = QueryBuilder().match("(n)").return_("n").offset(5)
        text, _ = qb.build()
        assert "OFFSET 5" in text

    def test_limit_offset_combination(self):
        """Test LIMIT and OFFSET together."""
        qb = QueryBuilder().match("(n)").return_("n").limit(10).offset(20)
        text, _ = qb.build()
        assert "LIMIT 10" in text
        assert "OFFSET 20" in text

    def test_offset_zero(self):
        """Test OFFSET 0 is valid."""
        qb = QueryBuilder().match("(n)").return_("n").offset(0)
        text, _ = qb.build()
        assert "OFFSET 0" in text

    def test_offset_negative_raises(self):
        """Test negative OFFSET raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            QueryBuilder().offset(-5)

    def test_offset_float_raises(self):
        """Test float OFFSET raises ValueError."""
        with pytest.raises(ValueError, match="integer"):
            QueryBuilder().offset(5.5)

    def test_offset_string_raises(self):
        """Test string OFFSET raises ValueError."""
        with pytest.raises(ValueError, match="integer"):
            QueryBuilder().offset("5")

    def test_offset_bool_raises(self):
        """Test bool OFFSET raises ValueError (bool is int subclass)."""
        with pytest.raises(ValueError, match="integer"):
            QueryBuilder().offset(False)


class TestQueryBuilderCreate:
    """Tests for CREATE clause."""

    def test_create_node(self):
        """Test CREATE node."""
        qb = QueryBuilder().create("(n:Person {name: 'Alice'})").return_("n")
        text, _ = qb.build()
        assert "CREATE (n:Person {name: 'Alice'})" in text

    def test_create_relationship(self):
        """Test CREATE relationship."""
        qb = (QueryBuilder()
              .match("(a:Person {name: 'Alice'})")
              .match("(b:Person {name: 'Bob'})")
              .create("(a)-[:KNOWS]->(b)"))
        text, _ = qb.build()
        assert "CREATE (a)-[:KNOWS]->(b)" in text


class TestQueryBuilderMerge:
    """Tests for MERGE clause."""

    def test_merge_node(self):
        """Test MERGE node."""
        qb = QueryBuilder().merge("(n:Person {name: 'Alice'})").return_("n")
        text, _ = qb.build()
        assert "MERGE (n:Person {name: 'Alice'})" in text


class TestQueryBuilderSet:
    """Tests for SET clause."""

    def test_set_single(self):
        """Test SET single property."""
        qb = QueryBuilder().match("(n)").set_("n.updated = true").return_("n")
        text, _ = qb.build()
        assert "SET n.updated = true" in text

    def test_set_multiple(self):
        """Test SET multiple properties."""
        qb = QueryBuilder().match("(n)").set_("n.a = 1", "n.b = 2").return_("n")
        text, _ = qb.build()
        assert "SET n.a = 1, n.b = 2" in text


class TestQueryBuilderDelete:
    """Tests for DELETE clause."""

    def test_delete_node(self):
        """Test DELETE node."""
        qb = QueryBuilder().match("(n:Person {name: 'Alice'})").delete("n")
        text, _ = qb.build()
        assert "DELETE n" in text

    def test_delete_multiple(self):
        """Test DELETE multiple."""
        qb = QueryBuilder().match("(n)-[r]->(m)").delete("r", "n", "m")
        text, _ = qb.build()
        assert "DELETE r, n, m" in text


class TestQueryBuilderUnion:
    """Tests for UNION clause."""

    def test_union(self):
        """Test UNION clause."""
        qb = (QueryBuilder()
              .return_("1 AS x")
              .union()
              .return_("2 AS x"))
        text, _ = qb.build()
        assert "UNION" in text


class TestQueryBuilderGroupBy:
    """Tests for GROUP BY clause."""

    def test_group_by(self):
        """Test GROUP BY clause."""
        qb = (QueryBuilder()
              .match("(n:Person)")
              .return_("n.city", "count(*)")
              .group_by("n.city"))
        text, _ = qb.build()
        assert "GROUP BY n.city" in text


class TestQueryBuilderParameters:
    """Tests for query parameters."""

    def test_with_param(self):
        """Test adding single parameter."""
        qb = (QueryBuilder()
              .match("(n:Person {name: $name})")
              .return_("n")
              .with_param("name", "Alice"))
        text, params = qb.build()
        assert "$name" in text
        assert params == {"name": "Alice"}

    def test_with_params(self):
        """Test adding multiple parameters."""
        qb = (QueryBuilder()
              .match("(n:Person)")
              .where("n.age > $minAge AND n.age < $maxAge")
              .return_("n")
              .with_params({"minAge": 25, "maxAge": 65}))
        text, params = qb.build()
        assert params == {"minAge": 25, "maxAge": 65}

    def test_params_preserved(self):
        """Test that params are preserved on build."""
        qb = QueryBuilder().with_param("a", 1).with_param("b", 2)
        _, params1 = qb.build()
        _, params2 = qb.build()
        assert params1 == {"a": 1, "b": 2}
        assert params2 == {"a": 1, "b": 2}
        # Modifying returned params shouldn't affect builder
        params1["c"] = 3
        _, params3 = qb.build()
        assert "c" not in params3


class TestQueryBuilderComplex:
    """Tests for complex query composition."""

    def test_full_query(self):
        """Test complex query with all clauses."""
        qb = (QueryBuilder()
              .match("(p:Person)")
              .where("p.age > $minAge")
              .with_("p.city AS city", "count(p) AS cnt")
              .return_("city", "cnt")
              .order_by("cnt DESC")
              .limit(10)
              .with_param("minAge", 25))
        text, params = qb.build()

        assert "MATCH (p:Person)" in text
        assert "WHERE p.age > $minAge" in text
        assert "WITH p.city AS city, count(p) AS cnt" in text
        assert "RETURN city, cnt" in text
        assert "ORDER BY cnt DESC" in text
        assert "LIMIT 10" in text
        assert params == {"minAge": 25}

    def test_chained_matches(self):
        """Test chained MATCH clauses."""
        qb = (QueryBuilder()
              .match("(a:Person {name: 'Alice'})")
              .match("(b:Person {name: 'Bob'})")
              .match("(a)-[r:KNOWS]->(b)")
              .return_("r"))
        text, _ = qb.build()
        # All matches should be present
        assert text.count("MATCH") == 3


class TestPatternBuilderNode:
    """Tests for PatternBuilder node patterns."""

    def test_node_simple(self):
        """Test simple node pattern."""
        pb = PatternBuilder().node("n")
        assert pb.build() == "(n)"

    def test_node_with_label(self):
        """Test node with label."""
        pb = PatternBuilder().node("n", "Person")
        assert pb.build() == "(n:Person)"

    def test_node_with_properties(self):
        """Test node with properties."""
        pb = PatternBuilder().node("n", "Person", {"name": "Alice"})
        result = pb.build()
        assert "(n:Person" in result
        assert "name:" in result
        assert "'Alice'" in result

    def test_node_empty(self):
        """Test anonymous node."""
        pb = PatternBuilder().node()
        assert pb.build() == "()"

    def test_node_label_only(self):
        """Test node with label only."""
        pb = PatternBuilder().node(label="Person")
        assert pb.build() == "(:Person)"

    def test_node_property_types(self):
        """Test various property types."""
        pb = PatternBuilder().node("n", properties={
            "name": "Alice",
            "age": 30,
            "active": True,
            "score": 3.14,
            "nothing": None,
        })
        result = pb.build()
        assert "'Alice'" in result
        assert "30" in result
        assert "true" in result
        assert "3.14" in result
        assert "null" in result

    def test_node_parameter_reference(self):
        """Test node with parameter reference."""
        pb = PatternBuilder().node("n", "Person", {"name": "$name"})
        result = pb.build()
        assert "$name" in result
        assert "'" not in result.split("$name")[0].split("name:")[-1]  # No quote before $


class TestPatternBuilderEdge:
    """Tests for PatternBuilder edge patterns."""

    def test_edge_outgoing(self):
        """Test outgoing edge."""
        pb = (PatternBuilder()
              .node("a")
              .edge("r", "KNOWS", EdgeDirection.OUTGOING)
              .node("b"))
        assert pb.build() == "(a)-[r:KNOWS]->(b)"

    def test_edge_incoming(self):
        """Test incoming edge."""
        pb = (PatternBuilder()
              .node("a")
              .edge("r", "KNOWS", EdgeDirection.INCOMING)
              .node("b"))
        assert pb.build() == "(a)<-[r:KNOWS](b)"

    def test_edge_undirected(self):
        """Test undirected edge."""
        pb = (PatternBuilder()
              .node("a")
              .edge("r", "KNOWS", EdgeDirection.UNDIRECTED)
              .node("b"))
        assert pb.build() == "(a)-[r:KNOWS]-(b)"

    def test_edge_anonymous(self):
        """Test anonymous edge."""
        pb = (PatternBuilder()
              .node("a")
              .edge()
              .node("b"))
        result = pb.build()
        assert "(a)-" in result
        assert "->(b)" in result

    def test_edge_type_only(self):
        """Test edge with type only."""
        pb = (PatternBuilder()
              .node("a")
              .edge(edge_type="KNOWS")
              .node("b"))
        result = pb.build()
        assert "[:KNOWS]" in result

    def test_edge_with_properties(self):
        """Test edge with properties."""
        pb = (PatternBuilder()
              .node("a")
              .edge("r", "KNOWS", EdgeDirection.OUTGOING, {"since": 2020})
              .node("b"))
        result = pb.build()
        assert "since:" in result
        assert "2020" in result


class TestPatternBuilderVariableLength:
    """Tests for variable length patterns."""

    def test_variable_length_unbounded(self):
        """Test unbounded variable length."""
        pb = (PatternBuilder()
              .node("a")
              .edge("", "KNOWS", EdgeDirection.UNDIRECTED)
              .variable_length()
              .node("b"))
        result = pb.build()
        assert "*]" in result

    def test_variable_length_min_only(self):
        """Test variable length with minimum."""
        pb = (PatternBuilder()
              .node("a")
              .edge("", "KNOWS", EdgeDirection.UNDIRECTED)
              .variable_length(min_hops=2)
              .node("b"))
        result = pb.build()
        assert "*2..]" in result

    def test_variable_length_range(self):
        """Test variable length with range."""
        pb = (PatternBuilder()
              .node("a")
              .edge("", "KNOWS", EdgeDirection.UNDIRECTED)
              .variable_length(min_hops=1, max_hops=5)
              .node("b"))
        result = pb.build()
        assert "*1..5]" in result

    def test_variable_length_exact(self):
        """Test variable length exact (min=max)."""
        pb = (PatternBuilder()
              .node("a")
              .edge("", "KNOWS", EdgeDirection.UNDIRECTED)
              .variable_length(min_hops=3, max_hops=3)
              .node("b"))
        result = pb.build()
        assert "*3..3]" in result


class TestPatternBuilderComplex:
    """Tests for complex patterns."""

    def test_path_pattern(self):
        """Test multi-hop path pattern."""
        pb = (PatternBuilder()
              .node("a", "Person")
              .edge("", "KNOWS", EdgeDirection.OUTGOING)
              .node("b", "Person")
              .edge("", "WORKS_AT", EdgeDirection.OUTGOING)
              .node("c", "Company"))
        result = pb.build()
        assert "(a:Person)" in result
        assert "(b:Person)" in result
        assert "(c:Company)" in result
        assert "KNOWS" in result
        assert "WORKS_AT" in result


class TestPredicateBuilderBasic:
    """Tests for basic PredicateBuilder operations."""

    def test_empty_builder(self):
        """Test empty predicate builder."""
        pb = PredicateBuilder()
        assert pb.build_and() == ""
        assert pb.build_or() == ""

    def test_equals(self):
        """Test equals predicate."""
        pb = PredicateBuilder().equals("n.name", "'Alice'")
        assert pb.build_and() == "n.name = 'Alice'"

    def test_not_equals(self):
        """Test not equals predicate."""
        pb = PredicateBuilder().not_equals("n.status", "'INACTIVE'")
        assert pb.build_and() == "n.status <> 'INACTIVE'"

    def test_greater_than(self):
        """Test greater than predicate."""
        pb = PredicateBuilder().greater_than("n.age", "25")
        assert pb.build_and() == "n.age > 25"

    def test_less_than(self):
        """Test less than predicate."""
        pb = PredicateBuilder().less_than("n.age", "65")
        assert pb.build_and() == "n.age < 65"

    def test_greater_equal(self):
        """Test greater or equal predicate."""
        pb = PredicateBuilder().greater_equal("n.score", "80")
        assert pb.build_and() == "n.score >= 80"

    def test_less_equal(self):
        """Test less or equal predicate."""
        pb = PredicateBuilder().less_equal("n.score", "100")
        assert pb.build_and() == "n.score <= 100"


class TestPredicateBuilderNull:
    """Tests for NULL predicates."""

    def test_is_null(self):
        """Test IS NULL predicate."""
        pb = PredicateBuilder().is_null("n.email")
        assert pb.build_and() == "n.email IS NULL"

    def test_is_not_null(self):
        """Test IS NOT NULL predicate."""
        pb = PredicateBuilder().is_not_null("n.email")
        assert pb.build_and() == "n.email IS NOT NULL"


class TestPredicateBuilderIn:
    """Tests for IN predicate."""

    def test_in_strings(self):
        """Test IN with strings."""
        pb = PredicateBuilder().in_("n.city", ["NYC", "LA", "Chicago"])
        result = pb.build_and()
        assert "n.city IN [" in result
        assert "'NYC'" in result
        assert "'LA'" in result
        assert "'Chicago'" in result

    def test_in_numbers(self):
        """Test IN with numbers."""
        pb = PredicateBuilder().in_("n.status", [1, 2, 3])
        result = pb.build_and()
        assert "n.status IN [" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result


class TestPredicateBuilderExists:
    """Tests for EXISTS predicate."""

    def test_exists(self):
        """Test EXISTS predicate."""
        pb = PredicateBuilder().exists("(n)-[:KNOWS]->()")
        assert pb.build_and() == "EXISTS { (n)-[:KNOWS]->() }"


class TestPredicateBuilderCombinations:
    """Tests for combining predicates."""

    def test_build_and(self):
        """Test combining with AND."""
        pb = (PredicateBuilder()
              .greater_than("n.age", "25")
              .less_than("n.age", "65"))
        assert pb.build_and() == "n.age > 25 AND n.age < 65"

    def test_build_or(self):
        """Test combining with OR."""
        pb = (PredicateBuilder()
              .equals("n.status", "'ACTIVE'")
              .equals("n.status", "'PENDING'"))
        assert pb.build_or() == "n.status = 'ACTIVE' OR n.status = 'PENDING'"

    def test_multiple_conditions(self):
        """Test multiple conditions."""
        pb = (PredicateBuilder()
              .greater_than("n.age", "25")
              .less_than("n.age", "65")
              .is_not_null("n.email")
              .equals("n.active", "true"))
        result = pb.build_and()
        assert result.count(" AND ") == 3


class TestConvenienceFunctions:
    """Tests for convenience query functions."""

    def test_find_friends(self):
        """Test find_friends function."""
        text, params = find_friends("Alice", limit=5)
        assert "MATCH" in text
        assert "KNOWS" in text
        assert "RETURN" in text
        assert "LIMIT 5" in text
        assert params == {"name": "Alice"}

    def test_create_person(self):
        """Test create_person function."""
        text, params = create_person("Bob", 35, "Acme Corp")
        assert "CREATE" in text
        assert "MERGE" in text
        assert "Person" in text
        assert "Company" in text
        assert "WORKS_AT" in text
        assert params == {"name": "Bob", "age": 35, "company": "Acme Corp"}

    def test_find_shortest_path(self):
        """Test find_shortest_path function."""
        text, params = find_shortest_path("Alice", "Bob")
        assert "MATCH" in text
        assert "path" in text
        assert "RETURN" in text
        assert "LENGTH" in text
        assert "LIMIT 1" in text
        assert params == {"person1": "Alice", "person2": "Bob"}


class TestEdgeDirection:
    """Tests for EdgeDirection enum."""

    def test_all_directions(self):
        """Test all EdgeDirection values exist."""
        assert EdgeDirection.OUTGOING
        assert EdgeDirection.INCOMING
        assert EdgeDirection.UNDIRECTED

    def test_directions_distinct(self):
        """Test EdgeDirection values are distinct."""
        assert EdgeDirection.OUTGOING != EdgeDirection.INCOMING
        assert EdgeDirection.INCOMING != EdgeDirection.UNDIRECTED
        assert EdgeDirection.OUTGOING != EdgeDirection.UNDIRECTED


class TestQueryBuilderChaining:
    """Tests for fluent chaining behavior."""

    def test_returns_self(self):
        """Test all methods return self for chaining."""
        qb = QueryBuilder()
        assert qb.match("(n)") is qb
        assert qb.optional_match("(m)") is qb
        assert qb.where("n.x = 1") is qb
        assert qb.with_("n") is qb
        assert qb.return_("n") is qb
        assert qb.order_by("n.x") is qb
        assert qb.limit(10) is qb
        assert qb.offset(5) is qb
        assert qb.create("(n)") is qb
        assert qb.merge("(n)") is qb
        assert qb.set_("n.x = 1") is qb
        assert qb.delete("n") is qb
        assert qb.union() is qb
        assert qb.group_by("n.x") is qb
        assert qb.with_param("x", 1) is qb
        assert qb.with_params({"y": 2}) is qb

    def test_pattern_builder_returns_self(self):
        """Test PatternBuilder methods return self."""
        pb = PatternBuilder()
        assert pb.node("n") is pb
        assert pb.edge() is pb
        assert pb.variable_length() is pb

    def test_predicate_builder_returns_self(self):
        """Test PredicateBuilder methods return self."""
        pb = PredicateBuilder()
        assert pb.equals("a", "b") is pb
        assert pb.not_equals("a", "b") is pb
        assert pb.greater_than("a", "b") is pb
        assert pb.less_than("a", "b") is pb
        assert pb.greater_equal("a", "b") is pb
        assert pb.less_equal("a", "b") is pb
        assert pb.is_null("a") is pb
        assert pb.is_not_null("a") is pb
        assert pb.exists("()") is pb
        assert pb.in_("a", [1]) is pb


class TestFormatValueEscaping:
    """Tests for _format_value string escaping (security-related)."""

    def test_escape_single_quote(self):
        """Test that single quotes are escaped."""
        pb = PatternBuilder().node("n", properties={"name": "O'Brien"})
        result = pb.build()
        # Single quote should be escaped as \'
        assert "O\\'Brien" in result

    def test_escape_backslash(self):
        """Test that backslashes are escaped."""
        pb = PatternBuilder().node("n", properties={"path": "C:\\Users\\test"})
        result = pb.build()
        # Backslashes should be doubled
        assert "C:\\\\Users\\\\test" in result

    def test_escape_backslash_before_quote(self):
        """Test backslash followed by quote is handled correctly."""
        # This tests against injection via "value\'" which could escape the closing quote
        pb = PatternBuilder().node("n", properties={"data": "test\\'"})
        result = pb.build()
        # Should be: 'test\\\'', meaning backslash escaped, then quote escaped
        assert "test\\\\\\'" in result

    def test_escape_preserves_other_characters(self):
        """Test that other special characters are not over-escaped."""
        pb = PatternBuilder().node("n", properties={"name": "Hello\nWorld\t!"})
        result = pb.build()
        # Newline and tab should be preserved as-is (they're valid in GQL strings)
        assert "Hello\nWorld\t!" in result

    def test_parameter_reference_not_escaped(self):
        """Test that parameter references ($param) are not quoted."""
        pb = PatternBuilder().node("n", properties={"name": "$userName"})
        result = pb.build()
        # Parameter should not be wrapped in quotes
        assert "$userName" in result
        assert "'$userName'" not in result

    def test_boolean_values(self):
        """Test boolean value formatting."""
        pb = PatternBuilder().node("n", properties={"active": True, "deleted": False})
        result = pb.build()
        assert "true" in result
        assert "false" in result

    def test_numeric_values(self):
        """Test numeric value formatting."""
        pb = PatternBuilder().node("n", properties={"count": 42, "score": 3.14})
        result = pb.build()
        assert "42" in result
        assert "3.14" in result

    def test_null_value(self):
        """Test null value formatting."""
        pb = PatternBuilder().node("n", properties={"data": None})
        result = pb.build()
        assert "null" in result

    def test_complex_injection_attempt(self):
        """Test complex injection attempt is properly escaped."""
        # Attempt to break out of string and inject GQL
        malicious = "'; DELETE (n) WHERE true; RETURN '"
        pb = PatternBuilder().node("n", properties={"name": malicious})
        result = pb.build()
        # All single quotes should be escaped
        assert "\\'" in result
        # The result should still be a valid string literal (starts and ends with quote)
        # and the injection should be neutralized
        name_part = result.split("name:")[1].split("}")[0].strip()
        assert name_part.startswith("'")
        assert name_part.endswith("'")

    def test_in_predicate_escaping(self):
        """Test that IN predicate values are properly escaped."""
        pb = PredicateBuilder().in_("n.name", ["O'Brien", "test\\path"])
        result = pb.build_and()
        assert "O\\'Brien" in result
        assert "test\\\\path" in result


class TestPredicateBuilderSafeMethods:
    """Tests for safe_* methods that escape values (SEC-013)."""

    def test_safe_equals_string(self):
        """Test safe_equals with string value."""
        pb = PredicateBuilder().safe_equals("n.name", "Alice")
        result = pb.build_and()
        assert result == "n.name = 'Alice'"

    def test_safe_equals_string_with_quote(self):
        """Test safe_equals escapes single quotes."""
        pb = PredicateBuilder().safe_equals("n.name", "O'Brien")
        result = pb.build_and()
        assert result == "n.name = 'O\\'Brien'"

    def test_safe_equals_string_with_backslash(self):
        """Test safe_equals escapes backslashes."""
        pb = PredicateBuilder().safe_equals("n.path", "C:\\Users")
        result = pb.build_and()
        assert result == "n.path = 'C:\\\\Users'"

    def test_safe_equals_integer(self):
        """Test safe_equals with integer value."""
        pb = PredicateBuilder().safe_equals("n.age", 25)
        result = pb.build_and()
        assert result == "n.age = 25"

    def test_safe_equals_boolean(self):
        """Test safe_equals with boolean value."""
        pb = PredicateBuilder().safe_equals("n.active", True)
        result = pb.build_and()
        assert result == "n.active = true"

    def test_safe_equals_none(self):
        """Test safe_equals with None value."""
        pb = PredicateBuilder().safe_equals("n.data", None)
        result = pb.build_and()
        assert result == "n.data = null"

    def test_safe_not_equals_string(self):
        """Test safe_not_equals with string value."""
        pb = PredicateBuilder().safe_not_equals("n.status", "deleted")
        result = pb.build_and()
        assert result == "n.status <> 'deleted'"

    def test_safe_not_equals_escapes_injection(self):
        """Test safe_not_equals escapes injection attempt."""
        malicious = "'; DELETE (n); RETURN '"
        pb = PredicateBuilder().safe_not_equals("n.name", malicious)
        result = pb.build_and()
        # All single quotes in the value should be escaped as \'
        assert "\\'" in result
        # Should not contain unescaped injection - verify proper structure
        assert "DELETE" in result  # Still present but as escaped string
        # The escaped result should have the injection neutralized:
        # n.name <> '\'; DELETE (n); RETURN \''
        # The internal quotes are escaped, so the string literal is intact
        assert result.startswith("n.name <> '")
        assert result.endswith("'")

    def test_safe_greater_than_integer(self):
        """Test safe_greater_than with integer value."""
        pb = PredicateBuilder().safe_greater_than("n.age", 18)
        result = pb.build_and()
        assert result == "n.age > 18"

    def test_safe_greater_than_float(self):
        """Test safe_greater_than with float value."""
        pb = PredicateBuilder().safe_greater_than("n.score", 3.14)
        result = pb.build_and()
        assert result == "n.score > 3.14"

    def test_safe_less_than_integer(self):
        """Test safe_less_than with integer value."""
        pb = PredicateBuilder().safe_less_than("n.count", 100)
        result = pb.build_and()
        assert result == "n.count < 100"

    def test_safe_methods_chaining(self):
        """Test that safe methods can be chained."""
        pb = (PredicateBuilder()
              .safe_greater_than("n.age", 18)
              .safe_less_than("n.age", 65)
              .safe_equals("n.active", True))
        result = pb.build_and()
        assert "n.age > 18" in result
        assert "n.age < 65" in result
        assert "n.active = true" in result
        assert result.count(" AND ") == 2

    def test_safe_equals_returns_self(self):
        """Test safe_equals returns self for chaining."""
        pb = PredicateBuilder()
        assert pb.safe_equals("a", "b") is pb

    def test_safe_not_equals_returns_self(self):
        """Test safe_not_equals returns self for chaining."""
        pb = PredicateBuilder()
        assert pb.safe_not_equals("a", "b") is pb

    def test_safe_greater_than_returns_self(self):
        """Test safe_greater_than returns self for chaining."""
        pb = PredicateBuilder()
        assert pb.safe_greater_than("a", 1) is pb

    def test_safe_less_than_returns_self(self):
        """Test safe_less_than returns self for chaining."""
        pb = PredicateBuilder()
        assert pb.safe_less_than("a", 1) is pb

    def test_safe_equals_complex_injection(self):
        """Test safe_equals handles complex injection attempts."""
        # Attempt backslash-quote escape sequence attack
        malicious = "value\\'"
        pb = PredicateBuilder().safe_equals("n.field", malicious)
        result = pb.build_and()
        # Backslash should be escaped first, then quote
        assert "value\\\\\\'" in result
