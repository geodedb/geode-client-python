"""
Transaction and savepoint example for Geode Python client.

Demonstrates:
- Transaction management (BEGIN, COMMIT, ROLLBACK)
- Savepoints for partial rollback
- Error handling with rollback
- Connection pooling with transactions
"""

import asyncio
from geode_client import Client, ConnectionPool


async def basic_transaction_example():
    """Demonstrate basic transaction usage."""
    print("=== Basic Transaction Example ===\n")

    client = Client(host="127.0.0.1", port=3141, skip_verify=True)

    async with client.connection() as conn:
        # Start a transaction
        await conn.begin()

        try:
            # Create some nodes
            await conn.execute("CREATE (p:Person {name: 'Alice', age: 30})")
            await conn.execute("CREATE (p:Person {name: 'Bob', age: 25})")

            # Query within transaction
            page, _ = await conn.query("MATCH (p:Person) RETURN p.name AS name, p.age AS age")

            print("Created persons:")
            for row in page.rows:
                name = row['name'].value
                age = row['age'].value
                print(f"  - {name}, age {age}")

            # Commit the transaction
            await conn.commit()
            print("\nTransaction committed successfully!\n")

        except Exception as e:
            # Rollback on error
            await conn.rollback()
            print(f"Transaction rolled back due to error: {e}\n")
            raise


async def savepoint_example():
    """Demonstrate savepoint usage for partial rollback."""
    print("=== Savepoint Example ===\n")

    client = Client(host="127.0.0.1", port=3141, skip_verify=True)

    async with client.connection() as conn:
        # Start a transaction
        await conn.begin()

        # Create initial data
        await conn.execute("CREATE (p:Person {name: 'Charlie', age: 35, city: 'NYC'})")
        print("Created person: Charlie, age 35, city NYC")

        # Create a savepoint before making changes
        sp1 = await conn.savepoint("before_update")
        print("Created savepoint: before_update")

        # Make some changes
        await conn.execute("MATCH (p:Person {name: 'Charlie'}) SET p.age = 40")
        print("Updated Charlie's age to 40")

        # Create another savepoint
        sp2 = await conn.savepoint("before_city_update")
        print("Created savepoint: before_city_update")

        # Make more changes
        await conn.execute("MATCH (p:Person {name: 'Charlie'}) SET p.city = 'SF'")
        print("Updated Charlie's city to SF")

        # Rollback to sp2 (undoes city change)
        await conn.rollback_to(sp2)
        print("\nRolled back to savepoint: before_city_update")
        print("Charlie's city is still NYC, age is still 40")

        # We can still rollback to sp1 if needed
        # await conn.rollback_to(sp1)  # Would undo age change too

        # Commit the transaction
        await conn.commit()
        print("\nTransaction committed!\n")

        # Verify final state
        page, _ = await conn.query(
            "MATCH (p:Person {name: 'Charlie'}) RETURN p.age AS age, p.city AS city"
        )
        if page.rows:
            row = page.rows[0]
            print(f"Final state: age={row['age'].value}, city={row['city'].value}")


async def nested_savepoints_example():
    """Demonstrate nested savepoints for complex transaction logic."""
    print("\n=== Nested Savepoints Example ===\n")

    client = Client(host="127.0.0.1", port=3141, skip_verify=True)

    async with client.connection() as conn:
        await conn.begin()

        # Level 0: Initial state
        await conn.execute("CREATE (org:Organization {name: 'Acme Corp'})")
        print("Created organization: Acme Corp")

        # Level 1: Add departments
        sp_depts = await conn.savepoint("departments")
        await conn.execute(
            "MATCH (org:Organization {name: 'Acme Corp'}) "
            "CREATE (org)-[:HAS_DEPT]->(d:Department {name: 'Engineering'})"
        )
        await conn.execute(
            "MATCH (org:Organization {name: 'Acme Corp'}) "
            "CREATE (org)-[:HAS_DEPT]->(d:Department {name: 'Sales'})"
        )
        print("Added departments: Engineering, Sales")

        # Level 2: Add employees
        sp_employees = await conn.savepoint("employees")
        await conn.execute(
            "MATCH (d:Department {name: 'Engineering'}) "
            "CREATE (d)-[:HAS_EMPLOYEE]->(e:Employee {name: 'Alice'})"
        )
        await conn.execute(
            "MATCH (d:Department {name: 'Engineering'}) "
            "CREATE (d)-[:HAS_EMPLOYEE]->(e:Employee {name: 'Bob'})"
        )
        print("Added employees to Engineering: Alice, Bob")

        # Level 3: Add projects
        sp_projects = await conn.savepoint("projects")
        await conn.execute(
            "MATCH (e:Employee {name: 'Alice'}) "
            "CREATE (e)-[:WORKS_ON]->(p:Project {name: 'Project X'})"
        )
        print("Added project: Project X for Alice")

        # Oops, we don't want projects yet - rollback to employees level
        await conn.rollback_to(sp_employees)
        print("\nRolled back to 'employees' savepoint (removed projects)")

        # We can continue from the employees level
        await conn.execute(
            "MATCH (d:Department {name: 'Sales'}) "
            "CREATE (d)-[:HAS_EMPLOYEE]->(e:Employee {name: 'Charlie'})"
        )
        print("Added employee to Sales: Charlie")

        # Commit everything
        await conn.commit()
        print("\nTransaction committed!\n")


async def pool_with_transactions_example():
    """Demonstrate using connection pool with transactions."""
    print("=== Connection Pool with Transactions ===\n")

    pool = ConnectionPool(
        host="127.0.0.1",
        port=3141,
        min_size=2,
        max_size=10,
        skip_verify=True
    )

    async with pool:
        # Simulate concurrent transactions
        async def create_person(name: str, age: int):
            async with pool.acquire() as conn:
                await conn.begin()
                try:
                    await conn.execute(
                        f"CREATE (p:Person {{name: '{name}', age: {age}}})"
                    )
                    await conn.commit()
                    print(f"Created person: {name}, age {age}")
                except Exception as e:
                    await conn.rollback()
                    print(f"Failed to create {name}: {e}")

        # Create multiple persons concurrently
        await asyncio.gather(
            create_person("David", 28),
            create_person("Emma", 32),
            create_person("Frank", 45),
        )

        print(f"\nPool stats: size={pool.size}, available={pool.available}")


async def error_handling_example():
    """Demonstrate transaction error handling."""
    print("\n=== Error Handling Example ===\n")

    client = Client(host="127.0.0.1", port=3141, skip_verify=True)

    async with client.connection() as conn:
        await conn.begin()

        try:
            # This will succeed
            await conn.execute("CREATE (p:Person {name: 'Grace', age: 27})")
            print("Created person: Grace")

            # Create a savepoint before risky operation
            sp = await conn.savepoint("before_risky_op")

            try:
                # This might fail (invalid syntax)
                await conn.execute("CREATE (INVALID SYNTAX")
            except Exception as e:
                print(f"Caught error in risky operation: {e}")
                # Rollback to savepoint, keeping Grace
                await conn.rollback_to(sp)
                print("Rolled back risky operation, Grace is still there")

            # Continue with valid operations
            await conn.execute("CREATE (p:Person {name: 'Henry', age: 29})")
            print("Created person: Henry")

            # Commit the transaction
            await conn.commit()
            print("\nTransaction committed (Grace and Henry created)\n")

        except Exception as e:
            # If anything goes wrong, rollback everything
            await conn.rollback()
            print(f"Entire transaction rolled back: {e}\n")
            raise


async def main():
    """Run all examples."""
    try:
        await basic_transaction_example()
        await savepoint_example()
        await nested_savepoints_example()
        await pool_with_transactions_example()
        await error_handling_example()

        print("\n✅ All transaction examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
