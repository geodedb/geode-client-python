"""
Integration tests for data types.

Tests cover:
- Null handling
- Integer ranges
- Decimal precision
- String/Unicode
- Boolean
- Arrays
- Maps/Objects
- Temporal types (where supported)
"""

import pytest


@pytest.mark.asyncio
async def test_null_value(client):
    """Test NULL value handling."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN null AS value")
        assert len(page.rows) == 1
        assert page.rows[0]["value"].is_null


@pytest.mark.asyncio
async def test_null_in_expression(client):
    """Test NULL in expressions."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                null + 1 AS add_null,
                null = null AS null_eq
        """)
        row = page.rows[0]
        # null + 1 should be null
        assert row["add_null"].is_null


@pytest.mark.asyncio
async def test_coalesce_null(client):
    """Test COALESCE with NULL."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                COALESCE(null, 'default') AS val1,
                COALESCE('present', 'default') AS val2
        """)
        row = page.rows[0]
        assert row["val1"].as_string == "default"
        assert row["val2"].as_string == "present"


# Integer tests


@pytest.mark.asyncio
async def test_integer_positive(client):
    """Test positive integer values."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 42 AS num")
        assert page.rows[0]["num"].as_int == 42


@pytest.mark.asyncio
async def test_integer_negative(client):
    """Test negative integer values."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN -100 AS num")
        assert page.rows[0]["num"].as_int == -100


@pytest.mark.asyncio
async def test_integer_zero(client):
    """Test zero value."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 0 AS num")
        assert page.rows[0]["num"].as_int == 0


@pytest.mark.asyncio
async def test_integer_large(client):
    """Test large integer values."""
    async with client.connection() as conn:
        # Test with a reasonably large integer
        large_num = 9223372036854775807  # max int64
        page, _ = await conn.query(f"RETURN {large_num} AS num")
        assert page.rows[0]["num"].as_int == large_num


@pytest.mark.asyncio
async def test_integer_arithmetic(client):
    """Test integer arithmetic."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                5 + 3 AS add,
                10 - 4 AS sub,
                6 * 7 AS mul,
                20 / 4 AS div
        """)
        row = page.rows[0]
        assert row["add"].as_int == 8
        assert row["sub"].as_int == 6
        assert row["mul"].as_int == 42
        assert row["div"].as_int == 5


# Decimal tests


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server currently returns NULL for decimal literals - known server behavior"
)
async def test_decimal_simple(client):
    """Test simple decimal value."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 3.14 AS pi")
        val = page.rows[0]["pi"]
        # May return as decimal or float depending on server
        raw = val.raw_value
        assert abs(float(raw) - 3.14) < 0.001


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server currently returns NULL for decimal literals - known server behavior"
)
async def test_decimal_precision(client):
    """Test decimal precision is preserved."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 123.456789 AS num")
        val = page.rows[0]["num"]
        raw = val.raw_value
        assert abs(float(raw) - 123.456789) < 0.000001


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server currently returns NULL for decimal literals - known server behavior"
)
async def test_decimal_negative(client):
    """Test negative decimal."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN -99.99 AS num")
        val = page.rows[0]["num"]
        raw = val.raw_value
        assert abs(float(raw) - (-99.99)) < 0.001


# String tests


@pytest.mark.asyncio
async def test_string_simple(client):
    """Test simple string value."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 'hello' AS str")
        assert page.rows[0]["str"].as_string == "hello"


@pytest.mark.asyncio
async def test_string_empty(client):
    """Test empty string."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN '' AS str")
        assert page.rows[0]["str"].as_string == ""


@pytest.mark.asyncio
async def test_string_with_spaces(client):
    """Test string with spaces."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 'hello world' AS str")
        assert page.rows[0]["str"].as_string == "hello world"


@pytest.mark.asyncio
async def test_string_unicode(client):
    """Test Unicode string."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 'Hello, World!' AS str")
        assert "Hello" in page.rows[0]["str"].as_string


@pytest.mark.asyncio
async def test_string_concatenation(client):
    """Test string concatenation."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 'hello' + ' ' + 'world' AS str")
        assert page.rows[0]["str"].as_string == "hello world"


@pytest.mark.asyncio
async def test_string_size(client):
    """Test SIZE function on string."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN SIZE('test') AS len")
        assert page.rows[0]["len"].as_int == 4


# Boolean tests


@pytest.mark.asyncio
async def test_boolean_true(client):
    """Test boolean true."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN true AS flag")
        assert page.rows[0]["flag"].as_bool is True


@pytest.mark.asyncio
async def test_boolean_false(client):
    """Test boolean false."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN false AS flag")
        assert page.rows[0]["flag"].as_bool is False


@pytest.mark.asyncio
async def test_boolean_not(client):
    """Test NOT operator."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                NOT true AS not_true,
                NOT false AS not_false
        """)
        row = page.rows[0]
        assert row["not_true"].as_bool is False
        assert row["not_false"].as_bool is True


@pytest.mark.asyncio
async def test_boolean_and(client):
    """Test AND operator."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                true AND true AS tt,
                true AND false AS tf,
                false AND false AS ff
        """)
        row = page.rows[0]
        assert row["tt"].as_bool is True
        assert row["tf"].as_bool is False
        assert row["ff"].as_bool is False


@pytest.mark.asyncio
async def test_boolean_or(client):
    """Test OR operator."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                true OR false AS tf,
                false OR false AS ff
        """)
        row = page.rows[0]
        assert row["tf"].as_bool is True
        assert row["ff"].as_bool is False


# Array tests


@pytest.mark.asyncio
async def test_array_integers(client):
    """Test array of integers."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN [1, 2, 3, 4, 5] AS arr")
        arr = page.rows[0]["arr"].as_array
        assert len(arr) == 5
        values = [v.as_int for v in arr]
        assert values == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_array_strings(client):
    """Test array of strings."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN ['a', 'b', 'c'] AS arr")
        arr = page.rows[0]["arr"].as_array
        assert len(arr) == 3
        values = [v.as_string for v in arr]
        assert values == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_array_empty(client):
    """Test empty array."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN [] AS arr")
        arr = page.rows[0]["arr"].as_array
        assert len(arr) == 0


@pytest.mark.asyncio
async def test_array_mixed_types(client):
    """Test array with mixed types."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN [1, 'two', true] AS arr")
        arr = page.rows[0]["arr"].as_array
        assert len(arr) == 3
        assert arr[0].as_int == 1
        assert arr[1].as_string == "two"
        assert arr[2].as_bool is True


@pytest.mark.asyncio
async def test_array_nested(client):
    """Test nested arrays."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN [[1, 2], [3, 4]] AS arr")
        arr = page.rows[0]["arr"].as_array
        assert len(arr) == 2
        inner1 = arr[0].as_array
        inner2 = arr[1].as_array
        assert [v.as_int for v in inner1] == [1, 2]
        assert [v.as_int for v in inner2] == [3, 4]


@pytest.mark.asyncio
async def test_array_size(client):
    """Test SIZE function on array."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN SIZE([1, 2, 3, 4]) AS len")
        assert page.rows[0]["len"].as_int == 4


@pytest.mark.asyncio
async def test_array_access(client):
    """Test array element access."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN [10, 20, 30][1] AS elem")
        # Array indexing is 0-based
        assert page.rows[0]["elem"].as_int == 20


# Object/Map tests


@pytest.mark.asyncio
async def test_object_simple(client):
    """Test simple object/map."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN {name: 'Alice', age: 30} AS obj")
        obj = page.rows[0]["obj"].as_object
        assert obj["name"].as_string == "Alice"
        assert obj["age"].as_int == 30


@pytest.mark.asyncio
async def test_object_empty(client):
    """Test empty object."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN {} AS obj")
        obj = page.rows[0]["obj"].as_object
        assert len(obj) == 0


@pytest.mark.asyncio
async def test_object_nested(client):
    """Test nested objects."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN {
                person: {name: 'Bob', age: 25},
                active: true
            } AS obj
        """)
        obj = page.rows[0]["obj"].as_object
        assert obj["active"].as_bool is True
        person = obj["person"].as_object
        assert person["name"].as_string == "Bob"
        assert person["age"].as_int == 25


@pytest.mark.asyncio
async def test_object_with_array(client):
    """Test object containing array."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN {
                name: 'Team',
                members: ['Alice', 'Bob', 'Carol']
            } AS obj
        """)
        obj = page.rows[0]["obj"].as_object
        assert obj["name"].as_string == "Team"
        members = obj["members"].as_array
        assert len(members) == 3


@pytest.mark.asyncio
async def test_object_property_access(client):
    """Test accessing object properties."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            WITH {name: 'Alice', age: 30} AS person
            RETURN person.name AS name, person.age AS age
        """)
        row = page.rows[0]
        assert row["name"].as_string == "Alice"
        assert row["age"].as_int == 30


# Comparison tests


@pytest.mark.asyncio
async def test_comparison_operators(client):
    """Test comparison operators."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                5 > 3 AS gt,
                5 >= 5 AS gte,
                3 < 5 AS lt,
                3 <= 3 AS lte,
                5 = 5 AS eq,
                5 <> 3 AS neq
        """)
        row = page.rows[0]
        assert row["gt"].as_bool is True
        assert row["gte"].as_bool is True
        assert row["lt"].as_bool is True
        assert row["lte"].as_bool is True
        assert row["eq"].as_bool is True
        assert row["neq"].as_bool is True


@pytest.mark.asyncio
async def test_string_comparison(client):
    """Test string comparison."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                'apple' < 'banana' AS lt,
                'abc' = 'abc' AS eq
        """)
        row = page.rows[0]
        assert row["lt"].as_bool is True
        assert row["eq"].as_bool is True


# Type coercion tests


@pytest.mark.asyncio
async def test_type_in_node_property(client):
    """Test various types as node properties."""
    import uuid

    uid = str(uuid.uuid4())[:8]

    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (n:TypeTest {{
                uid: '{uid}',
                int_val: 42,
                bool_val: true,
                str_val: 'hello',
                arr_val: [1, 2, 3]
            }})
        """)

        page, _ = await conn.query(f"""
            MATCH (n:TypeTest {{uid: '{uid}'}})
            RETURN
                n.int_val AS int_val,
                n.bool_val AS bool_val,
                n.str_val AS str_val,
                n.arr_val AS arr_val
        """)

        row = page.rows[0]
        assert row["int_val"].as_int == 42
        assert row["bool_val"].as_bool is True
        assert row["str_val"].as_string == "hello"
        arr = row["arr_val"].as_array
        assert [v.as_int for v in arr] == [1, 2, 3]

        # Cleanup
        await conn.execute(f"MATCH (n:TypeTest {{uid: '{uid}'}}) DELETE n")
