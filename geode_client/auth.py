"""
Authentication and authorization client for Geode.

Provides full RBAC, user management, and RLS policy support.

Security Notes:
    - Credentials are transmitted over TLS. Ensure skip_verify=False in production.
    - Client-side rate limiting is implemented to protect against brute force attacks.
    - Server-side rate limiting should also be configured for defense in depth.

Rate Limiting Limitations:
    The client-side rate limiting implemented in this module has inherent limitations:

    1. Per-Instance: Rate limiting state is stored per AuthClient instance. Creating
       a new AuthClient instance resets the counter, allowing bypass.

    2. Client-Side: Sophisticated attackers can modify or disable client-side checks
       entirely by using their own client implementation.

    3. Memory-Only: Rate limit state is not persisted. Restarting the application
       clears all lockouts.

    For these reasons, client-side rate limiting should be considered a convenience
    feature that provides basic protection against accidental brute force attempts
    (e.g., scripts in a loop). It is NOT a substitute for server-side rate limiting.

    Always ensure the Geode server has proper rate limiting configured for
    authentication endpoints.
"""

import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from . import validate
from .client import AuthError, Connection, SecurityWarning

# Rate limiting configuration
_DEFAULT_MAX_ATTEMPTS = 5
_DEFAULT_LOCKOUT_DURATION = timedelta(minutes=15)
_DEFAULT_ATTEMPT_WINDOW = timedelta(minutes=5)


@dataclass
class User:
    """Represents a user in the system."""

    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    roles: List[str]
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Role:
    """Represents a role in the RBAC system."""

    id: int
    name: str
    description: str
    permissions: List[str]
    parent_role: Optional[int] = None
    is_system: bool = False
    priority: int = 0


@dataclass
class Permission:
    """Represents a permission in the system."""

    id: int
    name: str
    resource: str
    action: str


@dataclass
class RLSPolicy:
    """Represents a Row-Level Security policy."""

    id: int = 0
    name: str = ""
    table: str = ""
    graph: str = ""
    operation: str = ""
    permissive: bool = True
    roles: List[int] = field(default_factory=list)
    using_expression: str = ""
    check_expression: str = ""
    enabled: bool = True
    data_classification: str = ""
    audit_level: str = ""


@dataclass
class SessionInfo:
    """Contains session information."""

    token: str
    user_id: int
    username: str
    expires_at: datetime
    roles: List[str]


class AuthClient:
    """
    Authentication and authorization client.

    Provides methods for user management, RBAC, and RLS policies.

    Rate Limiting:
        Client-side rate limiting is implemented to protect against brute force
        attacks. After max_attempts failed login attempts within attempt_window,
        the client will block further attempts for lockout_duration.

        **Important Limitations**: Client-side rate limiting is per-instance only.
        Attackers can bypass it by creating new AuthClient instances. This feature
        provides basic protection against accidental brute force (e.g., scripts in
        a loop) but is NOT a substitute for server-side rate limiting. Always ensure
        the Geode server has proper rate limiting configured.
    """

    def __init__(
        self,
        conn: Connection,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        lockout_duration: timedelta = _DEFAULT_LOCKOUT_DURATION,
        attempt_window: timedelta = _DEFAULT_ATTEMPT_WINDOW,
    ):
        """
        Initialize auth client with a connection.

        Args:
            conn: Active connection to Geode server
            max_attempts: Maximum failed login attempts before lockout
            lockout_duration: How long to lock out after max attempts
            attempt_window: Time window for counting failed attempts
        """
        self.conn = conn
        self._max_attempts = max_attempts
        self._lockout_duration = lockout_duration
        self._attempt_window = attempt_window
        self._failed_attempts: List[datetime] = []
        self._lockout_until: Optional[datetime] = None

    def _check_rate_limit(self) -> None:
        """
        Check if rate limit has been exceeded.

        Raises:
            AuthError: If currently locked out due to too many failed attempts
        """
        now = datetime.now()

        # Check if currently locked out
        if self._lockout_until and now < self._lockout_until:
            remaining = (self._lockout_until - now).total_seconds()
            raise AuthError(
                f"Too many failed login attempts. Try again in {int(remaining)} seconds."
            )

        # Clear expired lockout
        if self._lockout_until and now >= self._lockout_until:
            self._lockout_until = None
            self._failed_attempts.clear()

        # Clean up old attempts outside the window
        cutoff = now - self._attempt_window
        self._failed_attempts = [t for t in self._failed_attempts if t > cutoff]

    def _record_failed_attempt(self) -> None:
        """Record a failed login attempt and apply lockout if threshold reached."""
        now = datetime.now()
        self._failed_attempts.append(now)

        if len(self._failed_attempts) >= self._max_attempts:
            self._lockout_until = now + self._lockout_duration
            self._failed_attempts.clear()

    def _record_successful_login(self) -> None:
        """Clear failed attempts on successful login."""
        self._failed_attempts.clear()
        self._lockout_until = None

    async def login(self, username: str, password: str) -> SessionInfo:
        """
        Authenticate a user and return a session token.

        Args:
            username: Username
            password: Password

        Returns:
            SessionInfo with token and user details

        Raises:
            AuthError: If authentication fails or rate limit exceeded

        Security:
            - Credentials are transmitted over TLS. If TLS verification is
              disabled, a warning will be emitted.
            - Client-side rate limiting protects against brute force attacks.
        """
        # Warn if TLS verification is disabled
        if hasattr(self.conn, "skip_verify") and self.conn.skip_verify:
            warnings.warn(
                "Transmitting credentials with TLS verification disabled. "
                "This is insecure and credentials may be intercepted.",
                SecurityWarning,
                stacklevel=2,
            )

        # Check rate limit before attempting login
        self._check_rate_limit()

        req = {
            "type": "AUTH_LOGIN",
            "username": username,
            "password": password,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            self._record_failed_attempt()
            message = resp.get("message", "Login failed")
            raise AuthError(f"Login failed: {message}")

        # Record successful login to clear failed attempts
        self._record_successful_login()

        result = resp.get("result", {})

        expires_at_str = result.get("expires_at", "")
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        except ValueError:
            expires_at = datetime.now()

        return SessionInfo(
            token=result.get("token", ""),
            user_id=int(result.get("user_id", 0)),
            username=result.get("username", ""),
            expires_at=expires_at,
            roles=result.get("roles", []),
        )

    async def logout(self, token: str) -> None:
        """
        Logout and invalidate the session.

        Args:
            token: Session token

        Raises:
            AuthError: If logout fails
        """
        req = {
            "type": "AUTH_LOGOUT",
            "token": token,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Logout failed")
            raise AuthError(f"Logout failed: {message}")

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> User:
        """
        Create a new user.

        Args:
            username: Username (must be a valid identifier)
            email: Email address (must be valid email format)
            password: Password
            roles: List of role names
            metadata: Additional metadata

        Returns:
            Created User object

        Raises:
            AuthError: If user creation fails
            ValidationError: If username or email format is invalid
        """
        # Validate inputs
        validated_username = validate.identifier(username)
        validated_email = validate.email(email)

        req = {
            "type": "AUTH_CREATE_USER",
            "username": validated_username,
            "email": validated_email,
            "password": password,
        }

        if roles:
            req["roles"] = roles
        if metadata:
            req["metadata"] = metadata

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Create user failed")
            raise AuthError(f"Create user failed: {message}")

        result = resp.get("result", {})
        return self._parse_user(result)

    async def delete_user(self, user_id: int) -> None:
        """
        Delete a user.

        Args:
            user_id: User ID

        Raises:
            AuthError: If deletion fails
        """
        req = {
            "type": "AUTH_DELETE_USER",
            "user_id": user_id,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Delete user failed")
            raise AuthError(f"Delete user failed: {message}")

    async def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
        roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> User:
        """
        Update a user's information.

        Args:
            user_id: User ID
            email: New email address (must be valid email format if provided)
            is_active: Active status
            roles: New roles list
            metadata: Updated metadata

        Returns:
            Updated User object

        Raises:
            AuthError: If update fails
            ValidationError: If email format is invalid
        """
        req = {
            "type": "AUTH_UPDATE_USER",
            "user_id": user_id,
        }

        if email is not None:
            validated_email = validate.email(email)
            req["email"] = validated_email
        if is_active is not None:
            req["is_active"] = is_active
        if roles is not None:
            req["roles"] = roles
        if metadata is not None:
            req["metadata"] = metadata

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Update user failed")
            raise AuthError(f"Update user failed: {message}")

        result = resp.get("result", {})
        return self._parse_user(result)

    async def get_user(self, user_id: int) -> User:
        """
        Get user information.

        Args:
            user_id: User ID

        Returns:
            User object

        Raises:
            AuthError: If user not found
        """
        req = {
            "type": "AUTH_GET_USER",
            "user_id": user_id,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Get user failed")
            raise AuthError(f"Get user failed: {message}")

        result = resp.get("result", {})
        return self._parse_user(result)

    async def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        List all users.

        Args:
            limit: Maximum number of users to return (1-10000)
            offset: Offset for pagination (non-negative)

        Returns:
            List of User objects

        Raises:
            AuthError: If operation fails
            ValidationError: If limit or offset is invalid
        """
        # Validate pagination parameters
        validated_limit = validate.pagination_limit(limit)
        validated_offset = validate.pagination_offset(offset)

        req = {
            "type": "AUTH_LIST_USERS",
            "limit": validated_limit,
            "offset": validated_offset,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "List users failed")
            raise AuthError(f"List users failed: {message}")

        result = resp.get("result", {})
        users_data = result.get("users", [])
        return [self._parse_user(user_data) for user_data in users_data]

    async def create_role(
        self,
        name: str,
        description: str,
        permissions: List[str],
        parent_role: Optional[int] = None,
        priority: int = 0,
    ) -> Role:
        """
        Create a new role.

        Args:
            name: Role name (must be a valid identifier)
            description: Role description
            permissions: List of permission names
            parent_role: Parent role ID for inheritance
            priority: Role priority

        Returns:
            Created Role object

        Raises:
            AuthError: If role creation fails
            ValidationError: If role name is not a valid identifier
        """
        # Validate role name
        validated_name = validate.identifier(name)

        req = {
            "type": "AUTH_CREATE_ROLE",
            "name": validated_name,
            "description": description,
            "permissions": permissions,
            "priority": priority,
        }

        if parent_role is not None:
            req["parent_role"] = parent_role

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Create role failed")
            raise AuthError(f"Create role failed: {message}")

        result = resp.get("result", {})
        return self._parse_role(result)

    async def delete_role(self, role_id: int) -> None:
        """
        Delete a role.

        Args:
            role_id: Role ID

        Raises:
            AuthError: If deletion fails
        """
        req = {
            "type": "AUTH_DELETE_ROLE",
            "role_id": role_id,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Delete role failed")
            raise AuthError(f"Delete role failed: {message}")

    async def grant_permission(self, role_id: int, permission_id: int) -> None:
        """
        Grant a permission to a role.

        Args:
            role_id: Role ID
            permission_id: Permission ID

        Raises:
            AuthError: If grant fails
        """
        req = {
            "type": "AUTH_GRANT_PERMISSION",
            "role_id": role_id,
            "permission_id": permission_id,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Grant permission failed")
            raise AuthError(f"Grant permission failed: {message}")

    async def revoke_permission(self, role_id: int, permission_id: int) -> None:
        """
        Revoke a permission from a role.

        Args:
            role_id: Role ID
            permission_id: Permission ID

        Raises:
            AuthError: If revoke fails
        """
        req = {
            "type": "AUTH_REVOKE_PERMISSION",
            "role_id": role_id,
            "permission_id": permission_id,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Revoke permission failed")
            raise AuthError(f"Revoke permission failed: {message}")

    async def create_rls_policy(self, policy: RLSPolicy) -> RLSPolicy:
        """
        Create a new Row-Level Security policy.

        Args:
            policy: RLS policy definition

        Returns:
            Created RLS policy with ID

        Raises:
            AuthError: If policy creation fails
        """
        req = {
            "type": "RLS_CREATE_POLICY",
            "name": policy.name,
            "table": policy.table,
            "graph": policy.graph,
            "operation": policy.operation,
            "permissive": policy.permissive,
            "roles": policy.roles,
            "enabled": policy.enabled,
        }

        if policy.using_expression:
            req["using_expr"] = policy.using_expression
        if policy.check_expression:
            req["check_expr"] = policy.check_expression
        if policy.data_classification:
            req["data_classification"] = policy.data_classification
        if policy.audit_level:
            req["audit_level"] = policy.audit_level

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Create policy failed")
            raise AuthError(f"Create policy failed: {message}")

        result = resp.get("result", {})
        policy.id = result.get("id", policy.id)
        return policy

    async def enable_rls_policy(self, policy_id: int, enable: bool = True) -> None:
        """
        Enable or disable an RLS policy.

        Args:
            policy_id: Policy ID
            enable: True to enable, False to disable

        Raises:
            AuthError: If operation fails
        """
        req = {
            "type": "RLS_ENABLE_POLICY",
            "policy_id": policy_id,
            "enabled": enable,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Enable policy failed")
            raise AuthError(f"Enable policy failed: {message}")

    async def delete_rls_policy(self, policy_id: int) -> None:
        """
        Delete an RLS policy.

        Args:
            policy_id: Policy ID

        Raises:
            AuthError: If deletion fails
        """
        req = {
            "type": "RLS_DELETE_POLICY",
            "policy_id": policy_id,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Delete policy failed")
            raise AuthError(f"Delete policy failed: {message}")

    async def check_permission(
        self,
        user_id: int,
        resource: str,
        action: str,
    ) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user_id: User ID
            resource: Resource name
            action: Action name

        Returns:
            True if user has permission, False otherwise

        Raises:
            AuthError: If check fails
        """
        req = {
            "type": "AUTH_CHECK_PERMISSION",
            "user_id": user_id,
            "resource": resource,
            "action": action,
        }

        async with self.conn._lock:
            await self.conn._write_json(req)
            resp = await self.conn._read_json()

        status = resp.get("status", "")
        if status != "00000":
            message = resp.get("message", "Check permission failed")
            raise AuthError(f"Check permission failed: {message}")

        result = resp.get("result", {})
        return bool(result.get("allowed", False))

    def _parse_user(self, data: Dict[str, Any]) -> User:
        """Parse user data from JSON response."""
        created_at_str = data.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except ValueError:
            created_at = datetime.now()

        return User(
            id=int(data.get("id", 0)),
            username=data.get("username", ""),
            email=data.get("email", ""),
            is_active=data.get("is_active", False),
            created_at=created_at,
            roles=data.get("roles", []),
            metadata=data.get("metadata", {}),
        )

    def _parse_role(self, data: Dict[str, Any]) -> Role:
        """Parse role data from JSON response."""
        return Role(
            id=int(data.get("id", 0)),
            name=data.get("name", ""),
            description=data.get("description", ""),
            permissions=data.get("permissions", []),
            parent_role=data.get("parent_role"),
            is_system=data.get("is_system", False),
            priority=int(data.get("priority", 0)),
        )
