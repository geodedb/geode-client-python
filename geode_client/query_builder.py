"""
Query builder for constructing GQL queries programmatically.
"""

from enum import Enum, auto
from typing import Any, Dict, List, Optional


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

    def __init__(self) -> None:
        self._clauses: List[tuple[str, str]] = []
        self._params: Dict[str, Any] = {}

    def match(self, pattern: str) -> "QueryBuilder":
        """Add a MATCH clause."""
        self._clauses.append(("MATCH", pattern))
        return self

    def optional_match(self, pattern: str) -> "QueryBuilder":
        """Add an OPTIONAL MATCH clause."""
        self._clauses.append(("OPTIONAL MATCH", pattern))
        return self

    def where(self, condition: str) -> "QueryBuilder":
        """Add a WHERE clause."""
        self._clauses.append(("WHERE", condition))
        return self

    def with_(self, *expressions: str) -> "QueryBuilder":
        """Add a WITH clause."""
        self._clauses.append(("WITH", ", ".join(expressions)))
        return self

    def return_(self, *expressions: str) -> "QueryBuilder":
        """Add a RETURN clause."""
        self._clauses.append(("RETURN", ", ".join(expressions)))
        return self

    def order_by(self, *expressions: str) -> "QueryBuilder":
        """Add an ORDER BY clause."""
        self._clauses.append(("ORDER BY", ", ".join(expressions)))
        return self

    def limit(self, n: int) -> "QueryBuilder":
        """
        Add a LIMIT clause.

        Args:
            n: Maximum number of results (must be non-negative integer)

        Raises:
            ValueError: If n is negative or not an integer
        """
        if not isinstance(n, int) or isinstance(n, bool):
            raise ValueError(f"limit must be an integer, got {type(n).__name__}")
        if n < 0:
            raise ValueError(f"limit must be non-negative, got {n}")
        self._clauses.append(("LIMIT", str(n)))
        return self

    def offset(self, n: int) -> "QueryBuilder":
        """
        Add an OFFSET clause.

        Args:
            n: Number of results to skip (must be non-negative integer)

        Raises:
            ValueError: If n is negative or not an integer
        """
        if not isinstance(n, int) or isinstance(n, bool):
            raise ValueError(f"offset must be an integer, got {type(n).__name__}")
        if n < 0:
            raise ValueError(f"offset must be non-negative, got {n}")
        self._clauses.append(("OFFSET", str(n)))
        return self

    def create(self, pattern: str) -> "QueryBuilder":
        """Add a CREATE clause."""
        self._clauses.append(("CREATE", pattern))
        return self

    def merge(self, pattern: str) -> "QueryBuilder":
        """Add a MERGE clause."""
        self._clauses.append(("MERGE", pattern))
        return self

    def set_(self, *assignments: str) -> "QueryBuilder":
        """Add a SET clause."""
        self._clauses.append(("SET", ", ".join(assignments)))
        return self

    def delete(self, *variables: str) -> "QueryBuilder":
        """Add a DELETE clause."""
        self._clauses.append(("DELETE", ", ".join(variables)))
        return self

    def union(self) -> "QueryBuilder":
        """Add a UNION clause."""
        self._clauses.append(("UNION", ""))
        return self

    def group_by(self, *expressions: str) -> "QueryBuilder":
        """Add a GROUP BY clause."""
        self._clauses.append(("GROUP BY", ", ".join(expressions)))
        return self

    def with_param(self, name: str, value: Any) -> "QueryBuilder":
        """Add a query parameter."""
        self._params[name] = value
        return self

    def with_params(self, params: Dict[str, Any]) -> "QueryBuilder":
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

    def __init__(self) -> None:
        self._elements: List[str] = []

    def node(
        self,
        variable: str = "",
        label: str = "",
        properties: Optional[Dict[str, Any]] = None,
    ) -> "PatternBuilder":
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
    ) -> "PatternBuilder":
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

    def variable_length(self, min_hops: int = 0, max_hops: int = 0) -> "PatternBuilder":
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
        """
        Format a value for GQL.

        Security Note:
            String values are escaped to prevent GQL injection attacks.
            Both backslashes and single quotes are escaped properly.
            For user-provided values, consider using parameterized queries
            instead (e.g., with_param()) for defense in depth.
        """
        if isinstance(value, str):
            if value.startswith("$"):
                return value  # Parameter reference
            # Escape backslash first, then single quote
            # This prevents injection via escape sequence manipulation
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            return f"'{escaped}'"
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

    Security Warning:
        The comparison methods (equals, not_equals, greater_than, etc.) accept
        raw string parameters that are concatenated directly into the query.
        Do NOT pass untrusted user input to these methods, as this can lead
        to GQL injection attacks.

        For user-provided values, use one of these safe approaches:

        1. Use parameterized queries with QueryBuilder.with_param():
           ```python
           QueryBuilder()
               .match("(p:Person)")
               .where("p.name = $name")
               .with_param("name", user_input)
               .build()
           ```

        2. Use the safe_* methods that escape values:
           ```python
           PredicateBuilder()
               .safe_equals("p.name", user_input)  # Escapes the value
               .build_and()
           ```

    Example (trusted input only):
        predicate = (PredicateBuilder()
            .greater_than("p.age", "25")
            .not_equals("p.city", "'NYC'")
            .is_not_null("p.email")
            .build_and()
        )
    """

    def __init__(self) -> None:
        self._conditions: List[str] = []

    def equals(self, left: str, right: str) -> "PredicateBuilder":
        """
        Add an equality condition.

        Warning:
            Both parameters are inserted directly without escaping.
            Do NOT pass untrusted input. Use safe_equals() for user values.
        """
        self._conditions.append(f"{left} = {right}")
        return self

    def not_equals(self, left: str, right: str) -> "PredicateBuilder":
        """
        Add an inequality condition.

        Warning:
            Both parameters are inserted directly without escaping.
            Do NOT pass untrusted input. Use safe_not_equals() for user values.
        """
        self._conditions.append(f"{left} <> {right}")
        return self

    def greater_than(self, left: str, right: str) -> "PredicateBuilder":
        """
        Add a greater than condition.

        Warning:
            Both parameters are inserted directly without escaping.
            Do NOT pass untrusted input. Use safe_greater_than() for user values.
        """
        self._conditions.append(f"{left} > {right}")
        return self

    def less_than(self, left: str, right: str) -> "PredicateBuilder":
        """
        Add a less than condition.

        Warning:
            Both parameters are inserted directly without escaping.
            Do NOT pass untrusted input. Use safe_less_than() for user values.
        """
        self._conditions.append(f"{left} < {right}")
        return self

    def greater_equal(self, left: str, right: str) -> "PredicateBuilder":
        """
        Add a greater than or equal condition.

        Warning:
            Both parameters are inserted directly without escaping.
            Do NOT pass untrusted input.
        """
        self._conditions.append(f"{left} >= {right}")
        return self

    def less_equal(self, left: str, right: str) -> "PredicateBuilder":
        """
        Add a less than or equal condition.

        Warning:
            Both parameters are inserted directly without escaping.
            Do NOT pass untrusted input.
        """
        self._conditions.append(f"{left} <= {right}")
        return self

    def safe_equals(self, property_path: str, value: Any) -> "PredicateBuilder":
        """
        Add an equality condition with safe value escaping.

        This method safely escapes the value parameter, making it safe
        for use with untrusted user input.

        Args:
            property_path: The property to compare (e.g., "p.name")
            value: The value to compare against (will be escaped)

        Example:
            predicate = PredicateBuilder().safe_equals("p.name", user_input)
        """
        formatted = PatternBuilder._format_value(value)
        self._conditions.append(f"{property_path} = {formatted}")
        return self

    def safe_not_equals(self, property_path: str, value: Any) -> "PredicateBuilder":
        """
        Add an inequality condition with safe value escaping.

        This method safely escapes the value parameter, making it safe
        for use with untrusted user input.

        Args:
            property_path: The property to compare (e.g., "p.name")
            value: The value to compare against (will be escaped)
        """
        formatted = PatternBuilder._format_value(value)
        self._conditions.append(f"{property_path} <> {formatted}")
        return self

    def safe_greater_than(self, property_path: str, value: Any) -> "PredicateBuilder":
        """
        Add a greater than condition with safe value escaping.

        Args:
            property_path: The property to compare (e.g., "p.age")
            value: The value to compare against (will be escaped)
        """
        formatted = PatternBuilder._format_value(value)
        self._conditions.append(f"{property_path} > {formatted}")
        return self

    def safe_less_than(self, property_path: str, value: Any) -> "PredicateBuilder":
        """
        Add a less than condition with safe value escaping.

        Args:
            property_path: The property to compare (e.g., "p.age")
            value: The value to compare against (will be escaped)
        """
        formatted = PatternBuilder._format_value(value)
        self._conditions.append(f"{property_path} < {formatted}")
        return self

    def in_(self, expr: str, values: List[Any]) -> "PredicateBuilder":
        """
        Add an IN condition.

        Note: Values are escaped via _format_value(), making this safe
        for user input in the values list. The expr parameter should
        still be trusted input (e.g., a property path).
        """
        formatted = [PatternBuilder._format_value(v) for v in values]
        self._conditions.append(f"{expr} IN [{', '.join(formatted)}]")
        return self

    def is_null(self, expr: str) -> "PredicateBuilder":
        """
        Add an IS NULL condition.

        Warning:
            The expr parameter is inserted directly without escaping.
            Only use trusted property paths (e.g., "p.email").
        """
        self._conditions.append(f"{expr} IS NULL")
        return self

    def is_not_null(self, expr: str) -> "PredicateBuilder":
        """
        Add an IS NOT NULL condition.

        Warning:
            The expr parameter is inserted directly without escaping.
            Only use trusted property paths (e.g., "p.email").
        """
        self._conditions.append(f"{expr} IS NOT NULL")
        return self

    def exists(self, pattern: str) -> "PredicateBuilder":
        """
        Add an EXISTS condition.

        Warning:
            The pattern parameter is inserted directly without escaping.
            Only use trusted patterns built programmatically.
        """
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
