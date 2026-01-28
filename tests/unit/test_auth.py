"""Unit tests for the auth module."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from geode_client.auth import (
    AuthClient,
    Permission,
    RLSPolicy,
    Role,
    SessionInfo,
    User,
)
from geode_client.client import AuthError


class TestDataclasses:
    """Test auth dataclasses."""

    def test_user_creation(self):
        """Test User dataclass creation."""
        user = User(
            id=1,
            username="alice",
            email="alice@example.com",
            is_active=True,
            created_at=datetime.now(),
            roles=["admin", "user"],
            metadata={"department": "engineering"},
        )
        assert user.id == 1
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.is_active is True
        assert "admin" in user.roles
        assert user.metadata["department"] == "engineering"

    def test_user_default_metadata(self):
        """Test User with default metadata."""
        user = User(
            id=1,
            username="bob",
            email="bob@example.com",
            is_active=True,
            created_at=datetime.now(),
            roles=[],
        )
        assert user.metadata == {}

    def test_role_creation(self):
        """Test Role dataclass creation."""
        role = Role(
            id=1,
            name="admin",
            description="Administrator role",
            permissions=["read", "write", "delete"],
            parent_role=None,
            is_system=True,
            priority=100,
        )
        assert role.id == 1
        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert "read" in role.permissions
        assert role.parent_role is None
        assert role.is_system is True
        assert role.priority == 100

    def test_role_with_parent(self):
        """Test Role with parent role."""
        role = Role(
            id=2,
            name="superadmin",
            description="Super admin",
            permissions=["all"],
            parent_role=1,
            is_system=False,
            priority=200,
        )
        assert role.parent_role == 1

    def test_permission_creation(self):
        """Test Permission dataclass creation."""
        perm = Permission(
            id=1,
            name="read_users",
            resource="users",
            action="read",
        )
        assert perm.id == 1
        assert perm.name == "read_users"
        assert perm.resource == "users"
        assert perm.action == "read"

    def test_rls_policy_creation(self):
        """Test RLSPolicy dataclass creation."""
        policy = RLSPolicy(
            id=1,
            name="user_isolation",
            table="users",
            graph="default",
            operation="SELECT",
            permissive=True,
            roles=[1, 2],
            using_expression="user_id = current_user_id()",
            check_expression="",
            enabled=True,
            data_classification="CONFIDENTIAL",
            audit_level="FULL",
        )
        assert policy.id == 1
        assert policy.name == "user_isolation"
        assert policy.table == "users"
        assert policy.graph == "default"
        assert policy.operation == "SELECT"
        assert policy.permissive is True
        assert 1 in policy.roles
        assert policy.using_expression == "user_id = current_user_id()"
        assert policy.enabled is True
        assert policy.data_classification == "CONFIDENTIAL"
        assert policy.audit_level == "FULL"

    def test_rls_policy_defaults(self):
        """Test RLSPolicy default values."""
        policy = RLSPolicy()
        assert policy.id == 0
        assert policy.name == ""
        assert policy.table == ""
        assert policy.graph == ""
        assert policy.operation == ""
        assert policy.permissive is True
        assert policy.roles == []
        assert policy.using_expression == ""
        assert policy.check_expression == ""
        assert policy.enabled is True
        assert policy.data_classification == ""
        assert policy.audit_level == ""

    def test_session_info_creation(self):
        """Test SessionInfo dataclass creation."""
        expires = datetime.now()
        session = SessionInfo(
            token="abc123",
            user_id=1,
            username="alice",
            expires_at=expires,
            roles=["admin"],
        )
        assert session.token == "abc123"
        assert session.user_id == 1
        assert session.username == "alice"
        assert session.expires_at == expires
        assert "admin" in session.roles


class TestAuthClientInit:
    """Test AuthClient initialization."""

    def test_init_with_connection(self):
        """Test AuthClient initialization."""
        mock_conn = MagicMock()
        client = AuthClient(mock_conn)
        assert client.conn is mock_conn


class TestAuthClientLogin:
    """Test AuthClient login method."""

    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {
                    "token": "test_token",
                    "user_id": 1,
                    "username": "alice",
                    "expires_at": "2026-12-31T23:59:59Z",
                    "roles": ["admin"],
                },
            }
        )

        client = AuthClient(mock_conn)
        session = await client.login("alice", "password123")

        assert session.token == "test_token"
        assert session.user_id == 1
        assert session.username == "alice"
        assert "admin" in session.roles
        mock_conn._write_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_failure(self):
        """Test failed login."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Invalid credentials",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Login failed"):
            await client.login("alice", "wrongpassword")

    @pytest.mark.asyncio
    async def test_login_invalid_expires_at(self):
        """Test login with invalid expires_at format."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {
                    "token": "test_token",
                    "user_id": 1,
                    "username": "alice",
                    "expires_at": "invalid_date",
                    "roles": [],
                },
            }
        )

        client = AuthClient(mock_conn)
        session = await client.login("alice", "password")
        # Should use current datetime when parsing fails
        assert session.token == "test_token"


class TestAuthClientLogout:
    """Test AuthClient logout method."""

    @pytest.mark.asyncio
    async def test_logout_success(self):
        """Test successful logout."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(return_value={"status": "00000"})

        client = AuthClient(mock_conn)
        await client.logout("test_token")
        mock_conn._write_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_failure(self):
        """Test failed logout."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Invalid token",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Logout failed"):
            await client.logout("invalid_token")


class TestAuthClientUserManagement:
    """Test AuthClient user management methods."""

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Test successful user creation."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {
                    "id": 1,
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "is_active": True,
                    "created_at": "2026-01-01T00:00:00Z",
                    "roles": ["user"],
                    "metadata": {},
                },
            }
        )

        client = AuthClient(mock_conn)
        user = await client.create_user(
            username="newuser",
            email="newuser@example.com",
            password="password123",
            roles=["user"],
            metadata={"dept": "eng"},
        )

        assert user.username == "newuser"
        assert user.email == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_create_user_failure(self):
        """Test failed user creation."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Username already exists",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Create user failed"):
            await client.create_user("existing", "test@test.com", "pass")

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """Test successful user deletion."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(return_value={"status": "00000"})

        client = AuthClient(mock_conn)
        await client.delete_user(1)
        mock_conn._write_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_failure(self):
        """Test failed user deletion."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "User not found",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Delete user failed"):
            await client.delete_user(999)

    @pytest.mark.asyncio
    async def test_update_user_success(self):
        """Test successful user update."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {
                    "id": 1,
                    "username": "alice",
                    "email": "newemail@example.com",
                    "is_active": False,
                    "created_at": "2026-01-01T00:00:00Z",
                    "roles": ["admin"],
                    "metadata": {"updated": "true"},
                },
            }
        )

        client = AuthClient(mock_conn)
        user = await client.update_user(
            user_id=1,
            email="newemail@example.com",
            is_active=False,
            roles=["admin"],
            metadata={"updated": "true"},
        )

        assert user.email == "newemail@example.com"
        assert user.is_active is False

    @pytest.mark.asyncio
    async def test_update_user_failure(self):
        """Test failed user update."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "User not found",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Update user failed"):
            await client.update_user(999, email="test@test.com")

    @pytest.mark.asyncio
    async def test_get_user_success(self):
        """Test successful get user."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {
                    "id": 1,
                    "username": "alice",
                    "email": "alice@example.com",
                    "is_active": True,
                    "created_at": "2026-01-01T00:00:00Z",
                    "roles": ["user"],
                    "metadata": {},
                },
            }
        )

        client = AuthClient(mock_conn)
        user = await client.get_user(1)
        assert user.username == "alice"

    @pytest.mark.asyncio
    async def test_get_user_failure(self):
        """Test failed get user."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "User not found",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Get user failed"):
            await client.get_user(999)

    @pytest.mark.asyncio
    async def test_list_users_success(self):
        """Test successful list users."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {
                    "users": [
                        {
                            "id": 1,
                            "username": "alice",
                            "email": "alice@example.com",
                            "is_active": True,
                            "created_at": "2026-01-01T00:00:00Z",
                            "roles": [],
                            "metadata": {},
                        },
                        {
                            "id": 2,
                            "username": "bob",
                            "email": "bob@example.com",
                            "is_active": True,
                            "created_at": "2026-01-02T00:00:00Z",
                            "roles": [],
                            "metadata": {},
                        },
                    ]
                },
            }
        )

        client = AuthClient(mock_conn)
        users = await client.list_users(limit=10, offset=0)
        assert len(users) == 2
        assert users[0].username == "alice"
        assert users[1].username == "bob"

    @pytest.mark.asyncio
    async def test_list_users_failure(self):
        """Test failed list users."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Permission denied",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="List users failed"):
            await client.list_users()


class TestAuthClientRoleManagement:
    """Test AuthClient role management methods."""

    @pytest.mark.asyncio
    async def test_create_role_success(self):
        """Test successful role creation."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {
                    "id": 1,
                    "name": "editor",
                    "description": "Editor role",
                    "permissions": ["read", "write"],
                    "parent_role": None,
                    "is_system": False,
                    "priority": 50,
                },
            }
        )

        client = AuthClient(mock_conn)
        role = await client.create_role(
            name="editor",
            description="Editor role",
            permissions=["read", "write"],
            parent_role=None,
            priority=50,
        )

        assert role.name == "editor"
        assert "read" in role.permissions

    @pytest.mark.asyncio
    async def test_create_role_with_parent(self):
        """Test role creation with parent role."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {
                    "id": 2,
                    "name": "superadmin",
                    "description": "Super admin",
                    "permissions": ["all"],
                    "parent_role": 1,
                    "is_system": False,
                    "priority": 100,
                },
            }
        )

        client = AuthClient(mock_conn)
        role = await client.create_role(
            name="superadmin",
            description="Super admin",
            permissions=["all"],
            parent_role=1,
            priority=100,
        )

        assert role.parent_role == 1

    @pytest.mark.asyncio
    async def test_create_role_failure(self):
        """Test failed role creation."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Role already exists",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Create role failed"):
            await client.create_role("admin", "Admin", [])

    @pytest.mark.asyncio
    async def test_delete_role_success(self):
        """Test successful role deletion."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(return_value={"status": "00000"})

        client = AuthClient(mock_conn)
        await client.delete_role(1)
        mock_conn._write_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_role_failure(self):
        """Test failed role deletion."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Cannot delete system role",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Delete role failed"):
            await client.delete_role(1)


class TestAuthClientPermissionManagement:
    """Test AuthClient permission management methods."""

    @pytest.mark.asyncio
    async def test_grant_permission_success(self):
        """Test successful permission grant."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(return_value={"status": "00000"})

        client = AuthClient(mock_conn)
        await client.grant_permission(role_id=1, permission_id=1)
        mock_conn._write_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_grant_permission_failure(self):
        """Test failed permission grant."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Permission not found",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Grant permission failed"):
            await client.grant_permission(1, 999)

    @pytest.mark.asyncio
    async def test_revoke_permission_success(self):
        """Test successful permission revoke."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(return_value={"status": "00000"})

        client = AuthClient(mock_conn)
        await client.revoke_permission(role_id=1, permission_id=1)
        mock_conn._write_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_permission_failure(self):
        """Test failed permission revoke."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Permission not assigned",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Revoke permission failed"):
            await client.revoke_permission(1, 1)

    @pytest.mark.asyncio
    async def test_check_permission_allowed(self):
        """Test checking permission - allowed."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {"allowed": True},
            }
        )

        client = AuthClient(mock_conn)
        result = await client.check_permission(
            user_id=1,
            resource="users",
            action="read",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_denied(self):
        """Test checking permission - denied."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {"allowed": False},
            }
        )

        client = AuthClient(mock_conn)
        result = await client.check_permission(
            user_id=1,
            resource="admin",
            action="delete",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_failure(self):
        """Test failed permission check."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "User not found",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Check permission failed"):
            await client.check_permission(999, "users", "read")


class TestAuthClientRLSPolicies:
    """Test AuthClient RLS policy methods."""

    @pytest.mark.asyncio
    async def test_create_rls_policy_success(self):
        """Test successful RLS policy creation."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "00000",
                "result": {"id": 1},
            }
        )

        client = AuthClient(mock_conn)
        policy = RLSPolicy(
            name="user_isolation",
            table="users",
            graph="default",
            operation="SELECT",
            permissive=True,
            roles=[1],
            using_expression="user_id = current_user()",
            check_expression="",
            enabled=True,
            data_classification="CONFIDENTIAL",
            audit_level="FULL",
        )
        result = await client.create_rls_policy(policy)
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_create_rls_policy_failure(self):
        """Test failed RLS policy creation."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Invalid policy",
            }
        )

        client = AuthClient(mock_conn)
        policy = RLSPolicy(name="bad_policy", table="users", graph="", operation="")
        with pytest.raises(AuthError, match="Create policy failed"):
            await client.create_rls_policy(policy)

    @pytest.mark.asyncio
    async def test_enable_rls_policy_success(self):
        """Test successful RLS policy enable."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(return_value={"status": "00000"})

        client = AuthClient(mock_conn)
        await client.enable_rls_policy(policy_id=1, enable=True)
        mock_conn._write_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_disable_rls_policy(self):
        """Test disabling RLS policy."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(return_value={"status": "00000"})

        client = AuthClient(mock_conn)
        await client.enable_rls_policy(policy_id=1, enable=False)

        call_args = mock_conn._write_json.call_args[0][0]
        assert call_args["enabled"] is False

    @pytest.mark.asyncio
    async def test_enable_rls_policy_failure(self):
        """Test failed RLS policy enable."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Policy not found",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Enable policy failed"):
            await client.enable_rls_policy(999, True)

    @pytest.mark.asyncio
    async def test_delete_rls_policy_success(self):
        """Test successful RLS policy deletion."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(return_value={"status": "00000"})

        client = AuthClient(mock_conn)
        await client.delete_rls_policy(1)
        mock_conn._write_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_rls_policy_failure(self):
        """Test failed RLS policy deletion."""
        mock_conn = MagicMock()
        mock_conn._lock = asyncio.Lock()
        mock_conn._write_json = AsyncMock()
        mock_conn._read_json = AsyncMock(
            return_value={
                "status": "ERROR",
                "message": "Policy not found",
            }
        )

        client = AuthClient(mock_conn)
        with pytest.raises(AuthError, match="Delete policy failed"):
            await client.delete_rls_policy(999)


class TestAuthClientHelpers:
    """Test AuthClient helper methods."""

    def test_parse_user_valid(self):
        """Test _parse_user with valid data."""
        mock_conn = MagicMock()
        client = AuthClient(mock_conn)

        data = {
            "id": 1,
            "username": "alice",
            "email": "alice@example.com",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
            "roles": ["admin"],
            "metadata": {"key": "value"},
        }

        user = client._parse_user(data)
        assert user.id == 1
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.is_active is True
        assert "admin" in user.roles
        assert user.metadata["key"] == "value"

    def test_parse_user_invalid_date(self):
        """Test _parse_user with invalid created_at."""
        mock_conn = MagicMock()
        client = AuthClient(mock_conn)

        data = {
            "id": 1,
            "username": "alice",
            "email": "alice@example.com",
            "is_active": True,
            "created_at": "not-a-date",
            "roles": [],
            "metadata": {},
        }

        user = client._parse_user(data)
        # Should use datetime.now() for invalid dates
        assert user.created_at is not None

    def test_parse_user_missing_fields(self):
        """Test _parse_user with missing fields."""
        mock_conn = MagicMock()
        client = AuthClient(mock_conn)

        data = {}

        user = client._parse_user(data)
        assert user.id == 0
        assert user.username == ""
        assert user.email == ""
        assert user.is_active is False
        assert user.roles == []
        assert user.metadata == {}

    def test_parse_role_valid(self):
        """Test _parse_role with valid data."""
        mock_conn = MagicMock()
        client = AuthClient(mock_conn)

        data = {
            "id": 1,
            "name": "admin",
            "description": "Administrator",
            "permissions": ["read", "write"],
            "parent_role": 2,
            "is_system": True,
            "priority": 100,
        }

        role = client._parse_role(data)
        assert role.id == 1
        assert role.name == "admin"
        assert role.description == "Administrator"
        assert "read" in role.permissions
        assert role.parent_role == 2
        assert role.is_system is True
        assert role.priority == 100

    def test_parse_role_missing_fields(self):
        """Test _parse_role with missing fields."""
        mock_conn = MagicMock()
        client = AuthClient(mock_conn)

        data = {}

        role = client._parse_role(data)
        assert role.id == 0
        assert role.name == ""
        assert role.description == ""
        assert role.permissions == []
        assert role.parent_role is None
        assert role.is_system is False
        assert role.priority == 0
