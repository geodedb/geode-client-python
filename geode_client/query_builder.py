"""
Query builder for constructing GQL queries programmatically.
"""

from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union


class EdgeDirection(Enum):
    """Direction of an edge in a pattern."""
    OUTGOING = auto()
    INCOMING = auto()
    UNDIRECTED = auto()


class QueryBuilder:
    """
    Fluent interface for building GQL queries.

    Example:
        query = (QueryBuilder()
            .match("(p:Person {name: $name})-[:KNOWS]->(friend:Person)")
            .where("friend.age > 25")
            .return_("friend.name AS name", "friend.age AS age")
            .order_by("friend.age DESC")
            .limit(10)
            .with_param("name", "Alice")
        )
        text, params = query.build()
    """

    def __init__(self):
        self._clauses: List[tuple[str, str]] = []
        self._params: Dict[str, Any] = {}

    def match(self, pattern: str) -> 'QueryBuilder':
        """Add a MATCH clause."""
        self._clauses.append(("MATCH", pattern))
        return self

    def optional_match(self, pattern: str) -> 'QueryBuilder':
        """Add an OPTIONAL MATCH clause."""
        self._clauses.append(("OPTIONAL MATCH", pattern))
        return self

    def where(self, condition: str) -> 'QueryBuilder':
        """Add a WHERE clause."""
        self._clauses.append(("WHERE", condition))
        return self

    def with_(self, *expressions: str) -> 'QueryBuilder':
        """Add a WITH clause."""
        self._clauses.append(("WITH", ", ".join(expressions)))
        return self

    def return_(self, *expressions: str) -> 'QueryBuilder':
        """Add a RETURN clause."""
        self._clauses.append(("RETURN", ", ".join(expressions)))
        return self

    def order_by(self, *expressions: str) -> 'QueryBuilder':
        """Add an ORDER BY clause."""
        self._clauses.append(("ORDER BY", ", ".join(expressions)))
        return self

    def limit(self, n: int) -> 'QueryBuilder':
        """Add a LIMIT clause."""
        self._clauses.append(("LIMIT", str(n)))
        return self

    def offset(self, n: int) -> 'QueryBuilder':
        """Add an OFFSET clause."""
        self._clauses.append(("OFFSET", str(n)))
        return self

    def create(self, pattern: str) -> 'QueryBuilder':
        """Add a CREATE clause."""
        self._clauses.append(("CREATE", pattern))
        return self

    def merge(self, pattern: str) -> 'QueryBuilder':
        """Add a MERGE clause."""
        self._clauses.append(("MERGE", pattern))
        return self

    def set_(self, *assignments: str) -> 'QueryBuilder':
        """Add a SET clause."""
        self._clauses.append(("SET", ", ".join(assignments)))
        return self

    def delete(self, *variables: str) -> 'QueryBuilder':
        """Add a DELETE clause."""
        self._clauses.append(("DELETE", ", ".join(variables)))
        return self

    def union(self) -> 'QueryBuilder':
        """Add a UNION clause."""
        self._clauses.append(("UNION", ""))
        return self

    def group_by(self, *expressions: str) -> 'QueryBuilder':
        """Add a GROUP BY clause."""
        self._clauses.append(("GROUP BY", ", ".join(expressions)))
        return self

    def with_param(self, name: str, value: Any) -> 'QueryBuilder':
        """Add a query parameter."""
        self._params[name] = value
        return self

    def with_params(self, params: Dict[str, Any]) -> 'QueryBuilder':
        """Add multiple query parameters."""
        self._params.update(params)
        return self

    def build(self) -> tuple[str, Dict[str, Any]]:
        """
        Build the final query string and parameters.

        Returns:
            Tuple of (query_text, parameters)
        """
        parts = []
        for clause_type, content in self._clauses:
            if content:
                parts.append(f"{clause_type} {content}")
            else:
                parts.append(clause_type)

        return "\n".join(parts), self._params.copy()


class PatternBuilder:
    """
    Helper for building graph patterns.

    Example:
        pattern = (PatternBuilder()
            .node("a", "Person", {"name": "$person1"})
            .edge("", "KNOWS", EdgeDirection.UNDIRECTED)
            .variable_length(1, 6)
            .node("b", "Person", {"name": "$person2"})
            .build()
        )
    """

    def __init__(self):
        self._elements: List[str] = []

    def node(
        self,
        variable: str = "",
        label: str = "",
        properties: Optional[Dict[str, Any]] = None,
    ) -> 'PatternBuilder':
        """Add a node pattern."""
        pattern = "("

        if variable:
            pattern += variable

        if label:
            pattern += f":{label}"

        if properties:
            props = []
            for key, value in properties.items():
                props.append(f"{key}: {self._format_value(value)}")
            pattern += f" {{{', '.join(props)}}}"

        pattern += ")"
        self._elements.append(pattern)
        return self

    def edge(
        self,
        variable: str = "",
        edge_type: str = "",
        direction: EdgeDirection = EdgeDirection.OUTGOING,
        properties: Optional[Dict[str, Any]] = None,
    ) -> 'PatternBuilder':
        """Add an edge pattern."""
        pattern = ""

        # Start with direction prefix
        if direction == EdgeDirection.INCOMING:
            pattern = "<-"
        else:
            pattern = "-"

        # Add edge details if any
        if variable or edge_type or properties:
            pattern += "["

            if variable:
                pattern += variable

            if edge_type:
                pattern += f":{edge_type}"

            if properties:
                props = []
                for key, value in properties.items():
                    props.append(f"{key}: {self._format_value(value)}")
                pattern += f" {{{', '.join(props)}}}"

            pattern += "]"

        # Add direction suffix
        if direction == EdgeDirection.OUTGOING:
            pattern += "->"
        elif direction == EdgeDirection.UNDIRECTED:
            pattern += "-"

        self._elements.append(pattern)
        return self

    def variable_length(self, min_hops: int = 0, max_hops: int = 0) -> 'PatternBuilder':
        """Add variable length to the last edge."""
        if self._elements:
            edge = self._elements[-1]
            # Insert variable length before the closing bracket
            if "]" in edge:
                idx = edge.rfind("]")
                if min_hops == 0 and max_hops == 0:
                    length_spec = "*"
                elif max_hops == 0:
                    length_spec = f"*{min_hops}.."
                else:
                    length_spec = f"*{min_hops}..{max_hops}"
                self._elements[-1] = edge[:idx] + length_spec + edge[idx:]

        return self

    def build(self) -> str:
        """Build the pattern string."""
        return "".join(self._elements)

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a value for GQL."""
        if isinstance(value, str):
            if value.startswith("$"):
                return value  # Parameter reference
            return f"'{value.replace(chr(39), chr(92) + chr(39))}'"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif value is None:
            return "null"
        else:
            return str(value)


class PredicateBuilder:
    """
    Helper for building WHERE conditions.

    Example:
        predicate = (PredicateBuilder()
            .greater_than("p.age", "25")
            .not_equals("p.city", "'NYC'")
            .is_not_null("p.email")
            .build_and()
        )
    """

    def __init__(self):
        self._conditions: List[str] = []

    def equals(self, left: str, right: str) -> 'PredicateBuilder':
        """Add an equality condition."""
        self._conditions.append(f"{left} = {right}")
        return self

    def not_equals(self, left: str, right: str) -> 'PredicateBuilder':
        """Add an inequality condition."""
        self._conditions.append(f"{left} <> {right}")
        return self

    def greater_than(self, left: str, right: str) -> 'PredicateBuilder':
        """Add a greater than condition."""
        self._conditions.append(f"{left} > {right}")
        return self

    def less_than(self, left: str, right: str) -> 'PredicateBuilder':
        """Add a less than condition."""
        self._conditions.append(f"{left} < {right}")
        return self

    def greater_equal(self, left: str, right: str) -> 'PredicateBuilder':
        """Add a greater than or equal condition."""
        self._conditions.append(f"{left} >= {right}")
        return self

    def less_equal(self, left: str, right: str) -> 'PredicateBuilder':
        """Add a less than or equal condition."""
        self._conditions.append(f"{left} <= {right}")
        return self

    def in_(self, expr: str, values: List[Any]) -> 'PredicateBuilder':
        """Add an IN condition."""
        formatted = [PatternBuilder._format_value(v) for v in values]
        self._conditions.append(f"{expr} IN [{', '.join(formatted)}]")
        return self

    def is_null(self, expr: str) -> 'PredicateBuilder':
        """Add an IS NULL condition."""
        self._conditions.append(f"{expr} IS NULL")
        return self

    def is_not_null(self, expr: str) -> 'PredicateBuilder':
        """Add an IS NOT NULL condition."""
        self._conditions.append(f"{expr} IS NOT NULL")
        return self

    def exists(self, pattern: str) -> 'PredicateBuilder':
        """Add an EXISTS condition."""
        self._conditions.append(f"EXISTS {{ {pattern} }}")
        return self

    def build_and(self) -> str:
        """Build conditions combined with AND."""
        return " AND ".join(self._conditions)

    def build_or(self) -> str:
        """Build conditions combined with OR."""
        return " OR ".join(self._conditions)


# Convenience functions for common queries

def find_friends(person_name: str, limit: int = 10) -> tuple[str, Dict[str, Any]]:
    """
    Build a query to find friends of a person.

    Args:
        person_name: Name of the person
        limit: Maximum number of results

    Returns:
        Tuple of (query_text, parameters)
    """
    return (
        QueryBuilder()
        .match("(p:Person {name: $name})-[:KNOWS]->(friend:Person)")
        .return_("friend.name AS name", "friend.age AS age")
        .order_by("friend.age DESC")
        .limit(limit)
        .with_param("name", person_name)
        .build()
    )


def create_person(
    name: str,
    age: int,
    company: str,
) -> tuple[str, Dict[str, Any]]:
    """
    Build a query to create a person with relationships.

    Args:
        name: Person's name
        age: Person's age
        company: Company name

    Returns:
        Tuple of (query_text, parameters)
    """
    return (
        QueryBuilder()
        .create("(p:Person {name: $name, age: $age})")
        .merge("(c:Company {name: $company})")
        .create("(p)-[:WORKS_AT]->(c)")
        .return_("p", "c")
        .with_params({"name": name, "age": age, "company": company})
        .build()
    )


def find_shortest_path(
    person1: str,
    person2: str,
) -> tuple[str, Dict[str, Any]]:
    """
    Build a query to find the shortest path between two people.

    Args:
        person1: First person's name
        person2: Second person's name

    Returns:
        Tuple of (query_text, parameters)
    """
    pattern = (
        PatternBuilder()
        .node("a", "Person", {"name": "$person1"})
        .edge("", "KNOWS", EdgeDirection.UNDIRECTED)
        .variable_length(1, 6)
        .node("b", "Person", {"name": "$person2"})
        .build()
    )

    return (
        QueryBuilder()
        .match(f"path = {pattern}")
        .return_("path")
        .order_by("LENGTH(path)")
        .limit(1)
        .with_params({"person1": person1, "person2": person2})
        .build()
    )
