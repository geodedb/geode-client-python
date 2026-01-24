"""
Benchmarks for query builder operations.

Tests the performance of:
- QueryBuilder construction and building
- PatternBuilder pattern generation
- PredicateBuilder predicate construction
- Complex query composition
"""

import pytest

from geode_client import QueryBuilder, PatternBuilder, PredicateBuilder, EdgeDirection


# ============================================================================
# QueryBuilder benchmarks
# ============================================================================

class TestQueryBuilderBenchmarks:
    """Benchmarks for QueryBuilder operations."""

    def test_empty_builder(self, benchmark):
        """Benchmark creating empty QueryBuilder."""
        benchmark(QueryBuilder)

    def test_simple_return(self, benchmark):
        """Benchmark simple RETURN query."""
        def build():
            return QueryBuilder().return_("1 AS x").build()
        benchmark(build)

    def test_match_return(self, benchmark):
        """Benchmark MATCH-RETURN query."""
        def build():
            return (QueryBuilder()
                    .match("(n:Person)")
                    .return_("n")
                    .build())
        benchmark(build)

    def test_match_where_return(self, benchmark):
        """Benchmark MATCH-WHERE-RETURN query."""
        def build():
            return (QueryBuilder()
                    .match("(n:Person)")
                    .where("n.age > 25")
                    .return_("n")
                    .build())
        benchmark(build)

    def test_full_query(self, benchmark):
        """Benchmark full query with all clauses."""
        def build():
            return (QueryBuilder()
                    .match("(p:Person)")
                    .where("p.age > $minAge")
                    .with_("p.city AS city", "count(p) AS cnt")
                    .return_("city", "cnt")
                    .order_by("cnt DESC")
                    .limit(10)
                    .with_param("minAge", 25)
                    .build())
        benchmark(build)

    def test_create_query(self, benchmark):
        """Benchmark CREATE query."""
        def build():
            return (QueryBuilder()
                    .create("(p:Person {name: $name, age: $age})")
                    .return_("p")
                    .with_params({"name": "Alice", "age": 30})
                    .build())
        benchmark(build)

    def test_multiple_matches(self, benchmark):
        """Benchmark query with multiple MATCH clauses."""
        def build():
            return (QueryBuilder()
                    .match("(a:Person)")
                    .match("(b:Person)")
                    .match("(a)-[:KNOWS]->(b)")
                    .return_("a", "b")
                    .build())
        benchmark(build)

    def test_optional_match(self, benchmark):
        """Benchmark OPTIONAL MATCH query."""
        def build():
            return (QueryBuilder()
                    .match("(p:Person)")
                    .optional_match("(p)-[:KNOWS]->(friend)")
                    .return_("p", "friend")
                    .build())
        benchmark(build)

    def test_union_query(self, benchmark):
        """Benchmark UNION query."""
        def build():
            return (QueryBuilder()
                    .return_("1 AS x")
                    .union()
                    .return_("2 AS x")
                    .build())
        benchmark(build)

    def test_with_many_params(self, benchmark):
        """Benchmark query with many parameters."""
        def build():
            qb = QueryBuilder().match("(n)").return_("n")
            for i in range(20):
                qb.with_param(f"param_{i}", i)
            return qb.build()
        benchmark(build)

    def test_chained_methods(self, benchmark):
        """Benchmark heavily chained method calls."""
        def build():
            return (QueryBuilder()
                    .match("(a)")
                    .match("(b)")
                    .match("(c)")
                    .where("a.x > 1")
                    .where("b.y > 2")
                    .with_("a", "b", "c")
                    .return_("a", "b", "c")
                    .order_by("a.x", "b.y")
                    .limit(100)
                    .offset(50)
                    .build())
        benchmark(build)


# ============================================================================
# PatternBuilder benchmarks
# ============================================================================

class TestPatternBuilderBenchmarks:
    """Benchmarks for PatternBuilder operations."""

    def test_empty_builder(self, benchmark):
        """Benchmark creating empty PatternBuilder."""
        benchmark(PatternBuilder)

    def test_simple_node(self, benchmark):
        """Benchmark simple node pattern."""
        def build():
            return PatternBuilder().node("n").build()
        benchmark(build)

    def test_node_with_label(self, benchmark):
        """Benchmark node with label."""
        def build():
            return PatternBuilder().node("n", "Person").build()
        benchmark(build)

    def test_node_with_properties(self, benchmark):
        """Benchmark node with properties."""
        def build():
            return PatternBuilder().node("n", "Person", {
                "name": "Alice",
                "age": 30,
                "active": True
            }).build()
        benchmark(build)

    def test_simple_edge(self, benchmark):
        """Benchmark simple edge pattern."""
        def build():
            return (PatternBuilder()
                    .node("a")
                    .edge("r", "KNOWS", EdgeDirection.OUTGOING)
                    .node("b")
                    .build())
        benchmark(build)

    def test_edge_with_properties(self, benchmark):
        """Benchmark edge with properties."""
        def build():
            return (PatternBuilder()
                    .node("a", "Person")
                    .edge("r", "KNOWS", EdgeDirection.OUTGOING, {"since": 2020})
                    .node("b", "Person")
                    .build())
        benchmark(build)

    def test_variable_length(self, benchmark):
        """Benchmark variable length pattern."""
        def build():
            return (PatternBuilder()
                    .node("a", "Person")
                    .edge("", "KNOWS", EdgeDirection.UNDIRECTED)
                    .variable_length(1, 6)
                    .node("b", "Person")
                    .build())
        benchmark(build)

    def test_complex_path(self, benchmark):
        """Benchmark complex path pattern."""
        def build():
            return (PatternBuilder()
                    .node("a", "Person", {"name": "$name1"})
                    .edge("r1", "KNOWS", EdgeDirection.OUTGOING)
                    .node("b", "Person")
                    .edge("r2", "WORKS_AT", EdgeDirection.OUTGOING)
                    .node("c", "Company")
                    .build())
        benchmark(build)

    def test_incoming_edge(self, benchmark):
        """Benchmark incoming edge pattern."""
        def build():
            return (PatternBuilder()
                    .node("a")
                    .edge("r", "FOLLOWS", EdgeDirection.INCOMING)
                    .node("b")
                    .build())
        benchmark(build)

    def test_undirected_edge(self, benchmark):
        """Benchmark undirected edge pattern."""
        def build():
            return (PatternBuilder()
                    .node("a")
                    .edge("r", "FRIENDS_WITH", EdgeDirection.UNDIRECTED)
                    .node("b")
                    .build())
        benchmark(build)


# ============================================================================
# PredicateBuilder benchmarks
# ============================================================================

class TestPredicateBuilderBenchmarks:
    """Benchmarks for PredicateBuilder operations."""

    def test_empty_builder(self, benchmark):
        """Benchmark creating empty PredicateBuilder."""
        benchmark(PredicateBuilder)

    def test_equals(self, benchmark):
        """Benchmark equals predicate."""
        def build():
            return PredicateBuilder().equals("n.name", "'Alice'").build_and()
        benchmark(build)

    def test_comparison(self, benchmark):
        """Benchmark comparison predicates."""
        def build():
            return (PredicateBuilder()
                    .greater_than("n.age", "25")
                    .build_and())
        benchmark(build)

    def test_null_check(self, benchmark):
        """Benchmark null check predicate."""
        def build():
            return PredicateBuilder().is_not_null("n.email").build_and()
        benchmark(build)

    def test_in_list(self, benchmark):
        """Benchmark IN predicate."""
        def build():
            return (PredicateBuilder()
                    .in_("n.status", ["active", "pending", "review"])
                    .build_and())
        benchmark(build)

    def test_exists(self, benchmark):
        """Benchmark EXISTS predicate."""
        def build():
            return (PredicateBuilder()
                    .exists("(n)-[:KNOWS]->()")
                    .build_and())
        benchmark(build)

    def test_and_combination(self, benchmark):
        """Benchmark AND combination."""
        def build():
            return (PredicateBuilder()
                    .greater_than("n.age", "25")
                    .less_than("n.age", "65")
                    .is_not_null("n.email")
                    .build_and())
        benchmark(build)

    def test_or_combination(self, benchmark):
        """Benchmark OR combination."""
        def build():
            return (PredicateBuilder()
                    .equals("n.status", "'active'")
                    .equals("n.status", "'pending'")
                    .equals("n.status", "'review'")
                    .build_or())
        benchmark(build)

    def test_many_conditions(self, benchmark):
        """Benchmark many conditions."""
        def build():
            pb = PredicateBuilder()
            for i in range(10):
                pb.greater_than(f"n.field_{i}", str(i))
            return pb.build_and()
        benchmark(build)


# ============================================================================
# Complex composition benchmarks
# ============================================================================

class TestComplexCompositionBenchmarks:
    """Benchmarks for complex query composition."""

    def test_friends_query(self, benchmark):
        """Benchmark building a friends query."""
        def build():
            pattern = (PatternBuilder()
                       .node("p", "Person", {"name": "$name"})
                       .edge("", "KNOWS", EdgeDirection.OUTGOING)
                       .node("friend", "Person")
                       .build())

            return (QueryBuilder()
                    .match(pattern)
                    .return_("friend.name AS name", "friend.age AS age")
                    .order_by("friend.age DESC")
                    .limit(10)
                    .with_param("name", "Alice")
                    .build())
        benchmark(build)

    def test_shortest_path_query(self, benchmark):
        """Benchmark building shortest path query."""
        def build():
            pattern = (PatternBuilder()
                       .node("a", "Person", {"name": "$person1"})
                       .edge("", "KNOWS", EdgeDirection.UNDIRECTED)
                       .variable_length(1, 6)
                       .node("b", "Person", {"name": "$person2"})
                       .build())

            return (QueryBuilder()
                    .match(f"path = {pattern}")
                    .return_("path")
                    .order_by("LENGTH(path)")
                    .limit(1)
                    .with_params({"person1": "Alice", "person2": "Bob"})
                    .build())
        benchmark(build)

    def test_analytics_query(self, benchmark):
        """Benchmark building an analytics query."""
        def build():
            predicate = (PredicateBuilder()
                         .greater_than("p.age", "18")
                         .less_than("p.age", "65")
                         .is_not_null("p.email")
                         .build_and())

            return (QueryBuilder()
                    .match("(p:Person)")
                    .where(predicate)
                    .with_("p.city AS city", "count(p) AS population", "avg(p.age) AS avg_age")
                    .return_("city", "population", "avg_age")
                    .order_by("population DESC")
                    .limit(20)
                    .build())
        benchmark(build)

    def test_create_with_relationships(self, benchmark):
        """Benchmark building create with relationships."""
        def build():
            return (QueryBuilder()
                    .create("(p:Person {name: $name, age: $age})")
                    .merge("(c:Company {name: $company})")
                    .create("(p)-[:WORKS_AT {since: $since}]->(c)")
                    .return_("p", "c")
                    .with_params({
                        "name": "Alice",
                        "age": 30,
                        "company": "Acme Corp",
                        "since": 2020
                    })
                    .build())
        benchmark(build)

    def test_multi_hop_traversal(self, benchmark):
        """Benchmark building multi-hop traversal query."""
        def build():
            return (QueryBuilder()
                    .match("(start:Person {name: $name})")
                    .match("(start)-[:KNOWS*1..3]->(friend)")
                    .where("friend.active = true")
                    .with_("DISTINCT friend")
                    .return_("friend.name AS name", "friend.email AS email")
                    .order_by("friend.name")
                    .limit(50)
                    .with_param("name", "Alice")
                    .build())
        benchmark(build)


# ============================================================================
# Builder reuse benchmarks
# ============================================================================

class TestBuilderReuseBenchmarks:
    """Benchmarks for builder reuse patterns."""

    def test_repeated_builds(self, benchmark):
        """Benchmark building same query multiple times."""
        qb = (QueryBuilder()
              .match("(n:Person)")
              .where("n.age > $age")
              .return_("n")
              .with_param("age", 25))

        benchmark(qb.build)

    def test_pattern_reuse(self, benchmark):
        """Benchmark reusing pattern string."""
        pattern = (PatternBuilder()
                   .node("a", "Person")
                   .edge("r", "KNOWS", EdgeDirection.OUTGOING)
                   .node("b", "Person")
                   .build())

        def use_pattern():
            return (QueryBuilder()
                    .match(pattern)
                    .return_("a", "b")
                    .build())

        benchmark(use_pattern)
