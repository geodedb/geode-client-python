"""
Comprehensive QUIC client example for Geode.

Demonstrates all features of the Python QUIC client.

Note: For authentication examples, set environment variables:
  - GEODE_TEST_USERNAME: Username for testing (default: testuser)
  - GEODE_TEST_PASSWORD: Password for testing (REQUIRED - no default for security)
  - GEODE_TEST_EMAIL: Email for testing (default: test@example.com)
"""

import asyncio
import os
from geode_client import Client, AuthClient, ConnectionPool, QueryBuilder


async def basic_connection_example():
    """Basic connection and query example."""
    print("=== Basic Connection Example ===\n")

    # Create client
    client = Client(host="127.0.0.1", port=8443, skip_verify=True)

    # Connect and execute query
    async with client.connection() as conn:
        print("Connected to Geode via QUIC!")

        # Simple query
        page, _ = await conn.query("RETURN 1 AS x, 'Hello QUIC' AS greeting")
        print(f"\nSimple query results:")
        for row in page.rows:
            x = row["x"].as_int
            greeting = row["greeting"].as_string
            print(f"  x={x}, greeting={greeting}")


async def parameterized_queries():
    """Example of parameterized queries."""
    print("\n=== Parameterized Queries ===\n")

    client = Client(host="127.0.0.1", port=8443, skip_verify=True)

    async with client.connection() as conn:
        # Query with parameters
        query = "RETURN $name AS name, $age AS age, $active AS active"
        params = {
            "name": "Alice",
            "age": 30,
            "active": True
        }

        page, _ = await conn.query(query, params)
        print("Parameterized query results:")
        for row in page.rows:
            name = row["name"].as_string
            age = row["age"].as_int
            active = row["active"].as_bool
            print(f"  name={name}, age={age}, active={active}")


async def transaction_example():
    """Example of transaction management."""
    print("\n=== Transaction Example ===\n")

    client = Client(host="127.0.0.1", port=8443, skip_verify=True)

    async with client.connection() as conn:
        # Begin transaction
        await conn.begin()
        print("Transaction started")

        try:
            # Execute multiple operations
            await conn.execute(
                "CREATE (p:Person {name: $name, age: $age})",
                {"name": "Bob", "age": 25}
            )
            print("  Created person: Bob")

            await conn.execute(
                "CREATE (p:Person {name: $name, age: $age})",
                {"name": "Charlie", "age": 35}
            )
            print("  Created person: Charlie")

            # Commit transaction
            await conn.commit()
            print("Transaction committed successfully!")

        except Exception as e:
            # Rollback on error
            await conn.rollback()
            print(f"Transaction rolled back: {e}")


async def pagination_example():
    """Example of result pagination."""
    print("\n=== Pagination Example ===\n")

    client = Client(host="127.0.0.1", port=8443, skip_verify=True)

    async with client.connection() as conn:
        # Query with pagination
        query = """
        MATCH (n:Person)
        RETURN n.name AS name, n.age AS age
        ORDER BY n.age DESC
        """

        page, pager = await conn.query(query, page_size=5)

        print(f"First page: {len(page.rows)} rows")
        print(f"  Ordered: {page.ordered}")
        print(f"  Final: {page.final}")

        # Process first page
        for i, row in enumerate(page.rows, 1):
            print(f"  Row {i}: {row.get('name', 'N/A')}, age={row.get('age', 0)}")

        # Fetch more pages
        page_num = 2
        async for next_page in pager():
            if page_num > 3:  # Limit for demo
                break

            print(f"\nPage {page_num}: {len(next_page.rows)} rows")
            for i, row in enumerate(next_page.rows, 1):
                print(f"  Row {i}: {row.get('name', 'N/A')}")

            page_num += 1


async def query_builder_example():
    """Example using query builders."""
    print("\n=== Query Builder Example ===\n")

    client = Client(host="127.0.0.1", port=8443, skip_verify=True)

    async with client.connection() as conn:
        # Build query using QueryBuilder
        query_text, params = (
            QueryBuilder()
            .match("(p:Person {name: $name})")
            .return_("p.name AS name", "p.age AS age")
            .with_param("name", "Alice")
            .build()
        )

        print(f"Built query:\n{query_text}")
        print(f"Parameters: {params}\n")

        page, _ = await conn.query(query_text, params)
        print(f"Results: {len(page.rows)} rows")


async def authentication_example():
    """Example of authentication features."""
    print("\n=== Authentication Example ===\n")

    # Get credentials from environment variables (never hardcode in production)
    test_username = os.environ.get("GEODE_TEST_USERNAME", "testuser")
    test_password = os.environ.get("GEODE_TEST_PASSWORD")
    test_email = os.environ.get("GEODE_TEST_EMAIL", "test@example.com")

    if not test_password:
        print("ERROR: GEODE_TEST_PASSWORD environment variable is required")
        print("Set it with: export GEODE_TEST_PASSWORD='your-secure-password'")
        return

    client = Client(host="127.0.0.1", port=8443, skip_verify=True)

    async with client.connection() as conn:
        auth = AuthClient(conn)

        try:
            # Create a user
            user = await auth.create_user(
                username=test_username,
                email=test_email,
                password=test_password,
                roles=["user"],
                metadata={"department": "engineering"}
            )
            print(f"Created user: {user.username} (ID: {user.id})")

            # Login
            session = await auth.login(test_username, test_password)
            print(f"Logged in: {session.username}")
            # Note: Never log or print session tokens in production code
            print(f"  Roles: {session.roles}")
            print(f"  Expires: {session.expires_at}")

            # Check permission
            has_perm = await auth.check_permission(
                user_id=user.id,
                resource="data",
                action="read"
            )
            print(f"  Has read permission: {has_perm}")

            # Logout
            await auth.logout(session.token)
            print("Logged out successfully")

        except Exception as e:
            print(f"Auth error: {e}")


async def connection_pool_example():
    """Example of connection pooling."""
    print("\n=== Connection Pool Example ===\n")

    # Create pool
    pool = ConnectionPool(
        host="127.0.0.1",
        port=8443,
        min_size=2,
        max_size=10,
        skip_verify=True
    )

    async with pool:
        print(f"Pool initialized: size={pool.size}, available={pool.available}")

        # Execute concurrent queries
        async def execute_query(query_id: int):
            async with pool.acquire() as conn:
                page, _ = await conn.query(f"RETURN {query_id} AS id, 'result' AS data")
                result_id = page.rows[0]["id"].as_int
                data = page.rows[0]["data"].as_string
                print(f"  Query {query_id}: id={result_id}, data={data}")
                return result_id

        print("\nExecuting 5 concurrent queries:")
        results = await asyncio.gather(*[
            execute_query(i) for i in range(1, 6)
        ])

        print(f"\nAll results: {results}")
        print(f"Pool status: size={pool.size}, available={pool.available}")


async def advanced_types_example():
    """Example of advanced types."""
    print("\n=== Advanced Types Example ===\n")

    client = Client(host="127.0.0.1", port=8443, skip_verify=True)

    async with client.connection() as conn:
        # Arrays
        page, _ = await conn.query("RETURN [1, 2, 3, 4, 5] AS numbers")
        numbers = page.rows[0]["numbers"].as_array
        print(f"Array: {[n.as_int for n in numbers]}")

        # Objects
        page, _ = await conn.query("RETURN {name: 'Alice', age: 30} AS person")
        person = page.rows[0]["person"].as_object
        print(f"Object: name={person['name'].as_string}, age={person['age'].as_int}")

        # Temporal types
        page, _ = await conn.query("RETURN CURRENT_DATE() AS today")
        today = page.rows[0]["today"]
        print(f"Date: {today.as_date}")


async def error_handling_example():
    """Example of error handling."""
    print("\n=== Error Handling Example ===\n")

    client = Client(host="127.0.0.1", port=8443, skip_verify=True)

    async with client.connection() as conn:
        try:
            # Invalid query
            await conn.query("INVALID QUERY SYNTAX")
        except Exception as e:
            print(f"Caught error: {type(e).__name__}")
            print(f"  Message: {e}")

        # Recovery after error
        try:
            page, _ = await conn.query("RETURN 42 AS answer")
            answer = page.rows[0]["answer"].as_int
            print(f"\nRecovered successfully, answer={answer}")
        except Exception as e:
            print(f"Recovery failed: {e}")


async def main():
    """Run all examples."""
    print("Geode Python QUIC Client - Comprehensive Examples")
    print("=" * 60)

    try:
        await basic_connection_example()
        await parameterized_queries()
        await transaction_example()
        await pagination_example()
        await query_builder_example()
        await authentication_example()
        await connection_pool_example()
        await advanced_types_example()
        await error_handling_example()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
