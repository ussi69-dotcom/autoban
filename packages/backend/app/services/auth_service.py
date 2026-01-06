"""
Authentication Service for AutoBan.

Handles OAuth flows, JWT tokens, API key management, and user operations.
"""

import hashlib
import hmac
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import jwt

logger = logging.getLogger(__name__)


class OAuthProvider(Enum):
    """Supported OAuth providers."""
    GITHUB = "github"
    GOOGLE = "google"


class TokenType(Enum):
    """Types of tokens."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class OAuthConfig:
    """OAuth provider configuration."""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str] = field(default_factory=list)
    redirect_uri: Optional[str] = None


@dataclass
class OAuthState:
    """Temporary state for OAuth flow."""
    state_id: str
    provider: OAuthProvider
    redirect_uri: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 600)  # 10 minutes
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the state has expired."""
        return time.time() > self.expires_at


@dataclass
class User:
    """User model."""
    user_id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: Optional[OAuthProvider] = None
    provider_user_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_login_at: Optional[float] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "provider": self.provider.value if self.provider else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login_at": self.last_login_at,
            "is_active": self.is_active,
        }


@dataclass
class APIKey:
    """API key model."""
    key_id: str
    user_id: str
    name: str
    key_hash: str  # We store the hash, not the actual key
    key_prefix: str  # First few characters for identification
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_used_at: Optional[float] = None
    is_active: bool = True
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without sensitive data)."""
        return {
            "key_id": self.key_id,
            "user_id": self.user_id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_used_at": self.last_used_at,
            "is_active": self.is_active,
            "scopes": self.scopes,
        }


@dataclass
class TokenPayload:
    """JWT token payload."""
    user_id: str
    token_type: TokenType
    issued_at: float
    expires_at: float
    jti: str  # JWT ID for revocation
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuthService:
    """
    Authentication service for AutoBan.

    Features:
    - OAuth flow for GitHub and Google
    - JWT token generation and validation
    - API key management
    - User creation and lookup
    """

    # Default OAuth configurations
    DEFAULT_OAUTH_CONFIGS = {
        OAuthProvider.GITHUB: {
            "authorize_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
            "scopes": ["read:user", "user:email"],
        },
        OAuthProvider.GOOGLE: {
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
            "scopes": ["openid", "email", "profile"],
        },
    }

    def __init__(
        self,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days: int = 30,
        api_key_prefix: str = "ab_",
    ):
        """
        Initialize the auth service.

        Args:
            jwt_secret: Secret key for JWT signing
            jwt_algorithm: Algorithm for JWT signing
            access_token_expire_minutes: Access token expiry in minutes
            refresh_token_expire_days: Refresh token expiry in days
            api_key_prefix: Prefix for API keys
        """
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days
        self._api_key_prefix = api_key_prefix

        # Storage (placeholder - in production, use database)
        self._users: Dict[str, User] = {}
        self._users_by_email: Dict[str, str] = {}  # email -> user_id
        self._users_by_provider: Dict[str, str] = {}  # provider:id -> user_id
        self._api_keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._api_keys_by_hash: Dict[str, str] = {}  # key_hash -> key_id
        self._oauth_states: Dict[str, OAuthState] = {}
        self._revoked_tokens: set = set()  # Set of revoked JTIs
        self._oauth_configs: Dict[OAuthProvider, OAuthConfig] = {}

    def configure_oauth(
        self,
        provider: OAuthProvider,
        client_id: str,
        client_secret: str,
        redirect_uri: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> None:
        """
        Configure an OAuth provider.

        Args:
            provider: The OAuth provider to configure
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: Redirect URI after authorization
            scopes: OAuth scopes to request
        """
        defaults = self.DEFAULT_OAUTH_CONFIGS.get(provider, {})

        config = OAuthConfig(
            provider=provider,
            client_id=client_id,
            client_secret=client_secret,
            authorize_url=defaults.get("authorize_url", ""),
            token_url=defaults.get("token_url", ""),
            userinfo_url=defaults.get("userinfo_url", ""),
            scopes=scopes or defaults.get("scopes", []),
            redirect_uri=redirect_uri,
        )

        self._oauth_configs[provider] = config
        logger.info(f"Configured OAuth provider: {provider.value}")

    async def get_oauth_authorization_url(
        self,
        provider: OAuthProvider,
        redirect_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Get the OAuth authorization URL.

        Args:
            provider: The OAuth provider
            redirect_uri: Override the configured redirect URI
            metadata: Additional metadata to store with the state

        Returns:
            Tuple of (authorization_url, state_id)
        """
        config = self._oauth_configs.get(provider)
        if not config:
            raise ValueError(f"OAuth provider {provider.value} not configured")

        # Generate state for CSRF protection
        state_id = secrets.token_urlsafe(32)
        oauth_state = OAuthState(
            state_id=state_id,
            provider=provider,
            redirect_uri=redirect_uri or config.redirect_uri or "",
            metadata=metadata or {},
        )
        self._oauth_states[state_id] = oauth_state

        # Build authorization URL
        params = {
            "client_id": config.client_id,
            "redirect_uri": oauth_state.redirect_uri,
            "scope": " ".join(config.scopes),
            "state": state_id,
            "response_type": "code",
        }

        if provider == OAuthProvider.GOOGLE:
            params["access_type"] = "offline"
            params["prompt"] = "consent"

        query = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{config.authorize_url}?{query}"

        logger.info(f"Generated OAuth authorization URL for {provider.value}")
        return auth_url, state_id

    async def handle_oauth_callback(
        self,
        provider: OAuthProvider,
        code: str,
        state: str,
    ) -> Tuple[User, str, str]:
        """
        Handle OAuth callback and create/update user.

        This is a placeholder implementation. In production, this would:
        1. Validate the state
        2. Exchange the code for tokens
        3. Fetch user info from the provider
        4. Create or update the user

        Args:
            provider: The OAuth provider
            code: Authorization code from the provider
            state: State parameter for CSRF validation

        Returns:
            Tuple of (user, access_token, refresh_token)
        """
        # Validate state
        oauth_state = self._oauth_states.get(state)
        if not oauth_state:
            raise ValueError("Invalid OAuth state")
        if oauth_state.is_expired():
            del self._oauth_states[state]
            raise ValueError("OAuth state expired")
        if oauth_state.provider != provider:
            raise ValueError("Provider mismatch")

        # Clean up state
        del self._oauth_states[state]

        # Placeholder: In production, exchange code for tokens and fetch user info
        # For now, create a mock user based on the provider
        provider_user_id = f"mock_{secrets.token_hex(8)}"
        email = f"user_{provider_user_id}@{provider.value}.example.com"

        # Check if user exists
        user = await self.get_user_by_provider(provider, provider_user_id)
        if not user:
            user = await self.create_user(
                email=email,
                name=f"User from {provider.value}",
                provider=provider,
                provider_user_id=provider_user_id,
            )
        else:
            user.last_login_at = time.time()
            user.updated_at = time.time()

        # Generate tokens
        access_token = await self.create_access_token(user.user_id)
        refresh_token = await self.create_refresh_token(user.user_id)

        logger.info(f"OAuth callback handled for user {user.user_id}")
        return user, access_token, refresh_token

    async def create_user(
        self,
        email: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        provider: Optional[OAuthProvider] = None,
        provider_user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> User:
        """
        Create a new user.

        Args:
            email: User's email address
            name: User's display name
            avatar_url: URL to user's avatar
            provider: OAuth provider used for signup
            provider_user_id: User ID from the OAuth provider
            metadata: Additional user metadata

        Returns:
            The created user
        """
        # Check if email already exists
        if email in self._users_by_email:
            raise ValueError(f"User with email {email} already exists")

        user_id = str(uuid.uuid4())
        user = User(
            user_id=user_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            provider=provider,
            provider_user_id=provider_user_id,
            last_login_at=time.time(),
            metadata=metadata or {},
        )

        self._users[user_id] = user
        self._users_by_email[email] = user_id

        if provider and provider_user_id:
            provider_key = f"{provider.value}:{provider_user_id}"
            self._users_by_provider[provider_key] = user_id

        logger.info(f"Created user {user_id} with email {email}")
        return user

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self._users.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        user_id = self._users_by_email.get(email)
        if user_id:
            return self._users.get(user_id)
        return None

    async def get_user_by_provider(
        self,
        provider: OAuthProvider,
        provider_user_id: str,
    ) -> Optional[User]:
        """Get a user by OAuth provider and provider user ID."""
        provider_key = f"{provider.value}:{provider_user_id}"
        user_id = self._users_by_provider.get(provider_key)
        if user_id:
            return self._users.get(user_id)
        return None

    async def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[User]:
        """Update a user's information."""
        user = self._users.get(user_id)
        if not user:
            return None

        if name is not None:
            user.name = name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if metadata is not None:
            user.metadata.update(metadata)
        user.updated_at = time.time()

        logger.info(f"Updated user {user_id}")
        return user

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user."""
        user = self._users.get(user_id)
        if not user:
            return False

        user.is_active = False
        user.updated_at = time.time()

        # Revoke all API keys
        for api_key in list(self._api_keys.values()):
            if api_key.user_id == user_id:
                api_key.is_active = False

        logger.info(f"Deactivated user {user_id}")
        return True

    async def create_access_token(
        self,
        user_id: str,
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: The user ID to create the token for
            scopes: Optional list of scopes for the token
            metadata: Optional additional claims

        Returns:
            The JWT access token
        """
        now = time.time()
        expires_at = now + (self._access_token_expire_minutes * 60)
        jti = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "type": TokenType.ACCESS.value,
            "iat": now,
            "exp": expires_at,
            "jti": jti,
            "scopes": scopes or [],
        }
        if metadata:
            payload["metadata"] = metadata

        token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
        return token

    async def create_refresh_token(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a JWT refresh token.

        Args:
            user_id: The user ID to create the token for
            metadata: Optional additional claims

        Returns:
            The JWT refresh token
        """
        now = time.time()
        expires_at = now + (self._refresh_token_expire_days * 24 * 60 * 60)
        jti = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "type": TokenType.REFRESH.value,
            "iat": now,
            "exp": expires_at,
            "jti": jti,
        }
        if metadata:
            payload["metadata"] = metadata

        token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
        return token

    async def validate_token(
        self,
        token: str,
        expected_type: Optional[TokenType] = None,
    ) -> Optional[TokenPayload]:
        """
        Validate a JWT token.

        Args:
            token: The JWT token to validate
            expected_type: Optional expected token type

        Returns:
            The token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
            )

            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self._revoked_tokens:
                logger.warning(f"Attempted to use revoked token {jti}")
                return None

            # Check token type if expected
            token_type = TokenType(payload.get("type"))
            if expected_type and token_type != expected_type:
                logger.warning(f"Token type mismatch: expected {expected_type}, got {token_type}")
                return None

            # Check if user is still active
            user = await self.get_user(payload.get("sub"))
            if not user or not user.is_active:
                logger.warning("Token for inactive or missing user")
                return None

            return TokenPayload(
                user_id=payload.get("sub"),
                token_type=token_type,
                issued_at=payload.get("iat"),
                expires_at=payload.get("exp"),
                jti=jti,
                scopes=payload.get("scopes", []),
                metadata=payload.get("metadata", {}),
            )

        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> Optional[Tuple[str, str]]:
        """
        Refresh access and refresh tokens.

        Args:
            refresh_token: The refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token) or None if invalid
        """
        payload = await self.validate_token(refresh_token, TokenType.REFRESH)
        if not payload:
            return None

        # Revoke old refresh token
        self._revoked_tokens.add(payload.jti)

        # Create new tokens
        access_token = await self.create_access_token(payload.user_id)
        new_refresh_token = await self.create_refresh_token(payload.user_id)

        return access_token, new_refresh_token

    async def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
                options={"verify_exp": False},  # Allow revoking expired tokens
            )
            jti = payload.get("jti")
            if jti:
                self._revoked_tokens.add(jti)
                logger.info(f"Revoked token {jti}")
                return True
        except jwt.InvalidTokenError:
            pass
        return False

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[APIKey, str]:
        """
        Create a new API key.

        Args:
            user_id: The user to create the key for
            name: A friendly name for the key
            scopes: Optional list of scopes
            expires_in_days: Optional expiry in days
            metadata: Optional additional metadata

        Returns:
            Tuple of (APIKey object, raw key string)
            Note: The raw key is only returned once and should be stored securely
        """
        # Generate the key
        raw_key = f"{self._api_key_prefix}{secrets.token_urlsafe(32)}"
        key_hash = self._hash_api_key(raw_key)
        key_prefix = raw_key[:12]  # Store prefix for identification

        key_id = str(uuid.uuid4())
        expires_at = None
        if expires_in_days:
            expires_at = time.time() + (expires_in_days * 24 * 60 * 60)

        api_key = APIKey(
            key_id=key_id,
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            expires_at=expires_at,
            scopes=scopes or [],
            metadata=metadata or {},
        )

        self._api_keys[key_id] = api_key
        self._api_keys_by_hash[key_hash] = key_id

        logger.info(f"Created API key {key_id} for user {user_id}")
        return api_key, raw_key

    async def validate_api_key(self, raw_key: str) -> Optional[Tuple[APIKey, User]]:
        """
        Validate an API key.

        Args:
            raw_key: The raw API key string

        Returns:
            Tuple of (APIKey, User) if valid, None otherwise
        """
        key_hash = self._hash_api_key(raw_key)
        key_id = self._api_keys_by_hash.get(key_hash)

        if not key_id:
            return None

        api_key = self._api_keys.get(key_id)
        if not api_key:
            return None

        if not api_key.is_active:
            logger.warning(f"Attempted to use inactive API key {key_id}")
            return None

        if api_key.is_expired():
            logger.warning(f"Attempted to use expired API key {key_id}")
            return None

        user = await self.get_user(api_key.user_id)
        if not user or not user.is_active:
            return None

        # Update last used timestamp
        api_key.last_used_at = time.time()

        return api_key, user

    async def list_api_keys(self, user_id: str) -> List[APIKey]:
        """List all API keys for a user."""
        return [
            key for key in self._api_keys.values()
            if key.user_id == user_id and key.is_active
        ]

    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: The key ID to revoke
            user_id: The user ID (for authorization)

        Returns:
            True if the key was revoked
        """
        api_key = self._api_keys.get(key_id)
        if not api_key:
            return False

        if api_key.user_id != user_id:
            logger.warning(f"User {user_id} attempted to revoke key owned by {api_key.user_id}")
            return False

        api_key.is_active = False
        logger.info(f"Revoked API key {key_id}")
        return True

    def _hash_api_key(self, raw_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    async def cleanup_expired_states(self) -> int:
        """Clean up expired OAuth states."""
        expired = [
            state_id for state_id, state in self._oauth_states.items()
            if state.is_expired()
        ]
        for state_id in expired:
            del self._oauth_states[state_id]
        return len(expired)

    async def cleanup_revoked_tokens(self, max_age_days: int = 30) -> None:
        """
        Clean up old revoked token entries.

        In production, this would query by timestamp. For the placeholder,
        we just clear old entries periodically.
        """
        # Placeholder: In production, track revocation timestamps
        # and remove entries older than max_age_days
        pass
