"""
Advanced example demonstrating authentication, query builders, and connection pooling.
"""

import asyncio

from geode_client import (
    ConnectionPool,
    EdgeDirection,
    PatternBuilder,
    PredicateBuilder,
    QueryBuilder,
    create_person,
    find_friends,
)


async def query_builder_examples():
    """Demonstrate query builder usage."""
    print("=== Query Builder Examples ===\n")

    # Complex query with multiple clauses
    query, params = (
        QueryBuilder()
        .match("(p:Person)")
        .where("p.age > 25 AND p.city <> 'NYC'")
        .optional_match("(p)-[:WORKS_AT]->(c:Company)")
        .with_("p", "c")
        .match("(p)-[:PURCHASED]->(product:Product)")
        .return_(
            "p.name AS person",
            "c.name AS company",
            "COUNT(product) AS purchase_count",
            "SUM(product.price) AS total_spent",
        )
        .group_by("p.name", "c.name")
        .order_by("total_spent DESC")
        .limit(10)
        .build()
    )

    print("Complex Query:")
    print(query)
    print()

    # Pattern builder for paths
    pattern = (
        PatternBuilder()
        .node("a", "Person", {"name": "$person1"})
        .edge("knows", "KNOWS", EdgeDirection.UNDIRECTED)
        .variable_length(1, 6)
        .node("b", "Person", {"name": "$person2"})
        .build()
    )

    query, params = (
        QueryBuilder()
        .match(f"path = {pattern}")
        .return_("path", "LENGTH(path) AS hops")
        .order_by("hops")
        .limit(1)
        .with_params({"person1": "Alice", "person2": "Bob"})
        .build()
    )

    print("Shortest Path Query:")
    print(query)
    print(f"Params: {params}")
    print()

    # Predicate builder for complex conditions
    predicate = (
        PredicateBuilder()
        .greater_than("p.age", "25")
        .is_not_null("p.email")
        .in_("p.role", ["admin", "moderator", "user"])
        .build_and()
    )

    query, _ = QueryBuilder().match("(p:Person)").where(predicate).return_("p").build()

    print("Query with Predicate Builder:")
    print(query)
    print()

    # Convenience functions
    query, params = find_friends("Alice", limit=20)
    print("Find Friends Query:")
    print(query)
    print(f"Params: {params}")
    print()

    query, params = create_person("David", 35, "TechCorp")
    print("Create Person Query:")
    print(query)
    print(f"Params: {params}")
    print()


async def connection_pool_example():
    """Demonstrate connection pooling."""
    print("=== Connection Pool Example ===\n")

    # Create connection pool
    pool = ConnectionPool(
        dsn="process:./zig-out/bin/geode",
        min_size=2,
        max_size=10,
        timeout=30.0,
    )

    async with pool:
        print("Pool initialized with min_size=2, max_size=10")

        # Execute queries concurrently using the pool
        async def execute_query(query_id: int):
            async with pool.connection() as conn:
                page, _ = await conn.query(f"RETURN {query_id} AS id")
                result = page.rows[0]["id"].as_int
                print(f"  Query {query_id} result: {result}")
                return result

        # Run 5 queries concurrently
        print("\nExecuting 5 concurrent queries:")
        results = await asyncio.gather(*[execute_query(i) for i in range(1, 6)])
        print(f"All results: {results}")


async def auth_example():
    """Demonstrate authentication features."""
    print("\n=== Authentication Example ===\n")

    from geode_client import AuthClient, RLSPolicy, open_database

    client = open_database("process:./zig-out/bin/geode")

    async with client.connection() as conn:
        auth = AuthClient(conn)

        try:
            # Create user
            user = await auth.create_user(
                username="testuser",
                email="test@example.com",
                password="securepassword123",
                roles=["user"],
                metadata={"department": "engineering"},
            )
            print(f"Created user: {user.username} (ID: {user.id})")

            # Login
            session = await auth.login("testuser", "securepassword123")
            print(f"Logged in: {session.username}, token: {session.token[:20]}...")

            # Create role
            role = await auth.create_role(
                name="analyst",
                description="Data analyst role",
                permissions=["read:data", "analyze:data"],
            )
            print(f"Created role: {role.name} (ID: {role.id})")

            # Create RLS policy
            policy = RLSPolicy(
                id=0,
                name="user_data_policy",
                table="user_data",
                graph="main",
                operation="SELECT",
                permissive=True,
                roles=[role.id],
                using_expression="user_id = current_user_id()",
                enabled=True,
                audit_level="READ",
            )
            await auth.create_rls_policy(policy)
            print(f"Created RLS policy: {policy.name}")

            # Check permission
            has_perm = await auth.check_permission(
                user_id=user.id,
                resource="data",
                action="read",
            )
            print(f"User has read permission: {has_perm}")

            # Logout
            await auth.logout(session.token)
            print("Logged out successfully")

        except Exception as e:
            print(f"Auth error: {e}")


async def main():
    """Run all examples."""
    try:
        await query_builder_examples()
        await connection_pool_example()
        await auth_example()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
