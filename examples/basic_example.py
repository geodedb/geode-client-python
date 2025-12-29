"""
Basic example of using the Geode Python client.
"""

import asyncio
from geode_client import open_database, QueryBuilder


async def main():
    # Open database connection
    client = open_database("process:./zig-out/bin/geode?page_size=100")

    # Use connection with async context manager
    async with client.connection() as conn:
        print("Connected to Geode!")

        # Simple query
        page, _ = await conn.query("RETURN 1 AS x, 'Hello' AS greeting")
        print(f"\nSimple query results:")
        for row in page.rows:
            x = row["x"].as_int
            greeting = row["greeting"].as_string
            print(f"  x={x}, greeting={greeting}")

        # Query with parameters
        query = "RETURN $name AS name, $age AS age"
        params = {"name": "Alice", "age": 30}
        page, _ = await conn.query(query, params)
        print(f"\nParameterized query results:")
        for row in page.rows:
            print(f"  name={row['name'].as_string}, age={row['age'].as_int}")

        # Using query builder
        query_text, params = (
            QueryBuilder()
            .match("(p:Person {name: $name})")
            .return_("p.name AS name", "p.age AS age")
            .with_param("name", "Bob")
            .build()
        )
        print(f"\nQuery builder generated:")
        print(f"  Query: {query_text}")
        print(f"  Params: {params}")

        # Transaction example
        await conn.begin()
        try:
            await conn.query(
                "CREATE (p:Person {name: $name, age: $age})",
                {"name": "Charlie", "age": 25},
            )
            await conn.commit()
            print("\nTransaction committed successfully")
        except Exception as e:
            await conn.rollback()
            print(f"\nTransaction rolled back: {e}")

        # Pagination example
        query = """
        MATCH (n:Person)
        RETURN n.name AS name, n.age AS age
        ORDER BY n.age DESC
        """
        page, pager = await conn.query(query, page_size=10)
        print(f"\nFirst page: {len(page.rows)} rows")

        # Fetch more pages
        page_count = 1
        async for next_page in pager():
            page_count += 1
            print(f"Page {page_count}: {len(next_page.rows)} rows")
            if page_count >= 5:  # Limit for demo
                break


if __name__ == "__main__":
    asyncio.run(main())
