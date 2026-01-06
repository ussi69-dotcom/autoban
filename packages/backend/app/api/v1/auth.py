"""Authentication endpoints for OAuth and API key management."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4, UUID
import secrets
import httpx

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.config import get_settings
from app.models import User, Organization, OrgMember
from app.core.security import create_access_token, verify_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()
security = HTTPBearer(auto_error=False)


# ============================================================================
# Auth Dependencies
# ============================================================================

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    Supports both Authorization header and access_token cookie.
    """
    token = None

    # First try Authorization header
    if credentials:
        token = credentials.credentials

    # Fall back to cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional dependency to get the current user if authenticated.
    Returns None if no valid token provided.
    Supports both Authorization header and access_token cookie.
    """
    token = None

    # First try Authorization header
    if credentials:
        token = credentials.credentials

    # Fall back to cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        return None
    payload = verify_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return None

    result = await db.execute(select(User).where(User.id == user_uuid))
    return result.scalar_one_or_none()


async def get_or_create_user_and_org(
    db: AsyncSession,
    email: str,
    name: Optional[str],
    avatar_url: Optional[str],
    oauth_provider: str,
    oauth_id: str
) -> tuple[User, Organization]:
    """
    Get existing user by email or create a new user.
    For new users, also create a personal organization.
    Returns (user, organization).
    """
    # Check if user exists by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        # Update user info
        user.name = name or user.name
        user.avatar_url = avatar_url or user.avatar_url
        user.oauth_provider = oauth_provider
        user.oauth_id = oauth_id
        user.last_login_at = datetime.utcnow()
        await db.flush()

        # Get user's first organization
        org_result = await db.execute(
            select(Organization)
            .join(OrgMember, OrgMember.org_id == Organization.id)
            .where(OrgMember.user_id == user.id)
            .limit(1)
        )
        org = org_result.scalar_one_or_none()

        if not org:
            # Create personal org if none exists
            org = Organization(
                name=f"{name or email.split('@')[0]}'s Workspace",
                slug=f"user-{str(user.id).replace('-', '')[:12]}",
                plan="free",
            )
            db.add(org)
            await db.flush()

            member = OrgMember(
                org_id=org.id,
                user_id=user.id,
                role="owner",
            )
            db.add(member)
            await db.flush()

        return user, org

    # Create new user
    user = User(
        email=email,
        name=name,
        avatar_url=avatar_url,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()

    # Create personal organization
    org = Organization(
        name=f"{name or email.split('@')[0]}'s Workspace",
        slug=f"user-{str(user.id).replace('-', '')[:12]}",
        plan="free",
    )
    db.add(org)
    await db.flush()

    # Add user as owner of the org
    member = OrgMember(
        org_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db.add(member)
    await db.flush()

    return user, org


# ============================================================================
# Pydantic Schemas
# ============================================================================

class OAuthLoginResponse(BaseModel):
    """Response containing OAuth redirect URL."""
    authorization_url: str
    state: str


class TokenResponse(BaseModel):
    """Response containing access token after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class APIKeyCreate(BaseModel):
    """Request schema for creating an API key."""
    name: str = Field(..., min_length=1, max_length=100, description="Name for the API key")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Days until expiration")


class APIKeyResponse(BaseModel):
    """Response containing API key details."""
    id: str
    name: str
    key_prefix: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


class APIKeyCreatedResponse(APIKeyResponse):
    """Response after creating a new API key (includes full key, shown only once)."""
    key: str = Field(..., description="Full API key - save this, it won't be shown again")


class APIKeyListResponse(BaseModel):
    """Response containing list of API keys."""
    items: list[APIKeyResponse]
    total: int


class UserResponse(BaseModel):
    """Response containing current user information."""
    id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str
    created_at: datetime


class LogoutResponse(BaseModel):
    """Response after successful logout."""
    message: str = "Successfully logged out"


# ============================================================================
# OAuth Endpoints
# ============================================================================

@router.get(
    "/login/github",
    response_model=OAuthLoginResponse,
    summary="Initiate GitHub OAuth login",
    responses={
        200: {"description": "OAuth authorization URL generated"},
        503: {"description": "GitHub OAuth not configured"}
    }
)
async def login_github() -> OAuthLoginResponse:
    """
    Initiate GitHub OAuth login flow.

    Returns an authorization URL that the client should redirect to.
    The state parameter should be stored and verified during callback.
    """
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )

    state = secrets.token_urlsafe(32)
    authorization_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_redirect_uri}"
        f"&scope=user:email,read:org"
        f"&state={state}"
    )

    return OAuthLoginResponse(authorization_url=authorization_url, state=state)


@router.get(
    "/login/google",
    response_model=OAuthLoginResponse,
    summary="Initiate Google OAuth login",
    responses={
        200: {"description": "OAuth authorization URL generated"},
        503: {"description": "Google OAuth not configured"}
    }
)
async def login_google() -> OAuthLoginResponse:
    """
    Initiate Google OAuth login flow.

    Returns an authorization URL that the client should redirect to.
    The state parameter should be stored and verified during callback.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    state = secrets.token_urlsafe(32)
    authorization_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        f"&scope=openid email profile"
        f"&response_type=code"
        f"&state={state}"
        f"&access_type=offline"
    )

    return OAuthLoginResponse(authorization_url=authorization_url, state=state)


@router.get(
    "/callback/github",
    response_model=TokenResponse,
    summary="Handle GitHub OAuth callback",
    responses={
        200: {"description": "Authentication successful"},
        400: {"description": "Invalid or missing authorization code"},
        503: {"description": "GitHub OAuth not configured"}
    }
)
async def callback_github(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Handle GitHub OAuth callback.

    Exchanges the authorization code for an access token,
    fetches user information, and creates or updates the user record.

    - **code**: Authorization code from GitHub
    - **state**: State parameter for CSRF verification
    """
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri
            },
            headers={"Accept": "application/json"}
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )

        token_data = token_response.json()
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=token_data.get("error_description", "OAuth error")
            )

        github_access_token = token_data["access_token"]

        # Fetch user info
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_access_token}",
                "Accept": "application/vnd.github+json"
            }
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user information"
            )

        user_data = user_response.json()

        # Fetch user email if not public
        email = user_data.get("email")
        if not email:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {github_access_token}",
                    "Accept": "application/vnd.github+json"
                }
            )
            if emails_response.status_code == 200:
                emails = emails_response.json()
                primary_email = next(
                    (e for e in emails if e.get("primary") and e.get("verified")),
                    None
                )
                if primary_email:
                    email = primary_email["email"]

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve email from GitHub"
        )

    # Create or update user in database
    user, org = await get_or_create_user_and_org(
        db=db,
        email=email,
        name=user_data.get("name"),
        avatar_url=user_data.get("avatar_url"),
        oauth_provider="github",
        oauth_id=str(user_data.get("id")),
    )

    # Generate JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url
    )


@router.get(
    "/callback/google",
    response_model=TokenResponse,
    summary="Handle Google OAuth callback",
    responses={
        200: {"description": "Authentication successful"},
        400: {"description": "Invalid or missing authorization code"},
        503: {"description": "Google OAuth not configured"}
    }
)
async def callback_google(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Handle Google OAuth callback.

    Exchanges the authorization code for an access token,
    fetches user information, and creates or updates the user record.

    - **code**: Authorization code from Google
    - **state**: State parameter for CSRF verification
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code"
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )

        token_data = token_response.json()
        google_access_token = token_data["access_token"]

        # Fetch user info
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"}
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user information"
            )

        user_data = user_response.json()

    email = user_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve email from Google"
        )

    # Create or update user in database
    user, org = await get_or_create_user_and_org(
        db=db,
        email=email,
        name=user_data.get("name"),
        avatar_url=user_data.get("picture"),
        oauth_provider="google",
        oauth_id=str(user_data.get("id")),
    )

    # Generate JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url
    )


# ============================================================================
# API Key Endpoints
# ============================================================================

@router.post(
    "/api-keys",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new API key",
    responses={
        201: {"description": "API key created successfully"},
        401: {"description": "Not authenticated"}
    }
)
async def create_api_key(
    request: APIKeyCreate,
    db: AsyncSession = Depends(get_db)
) -> APIKeyCreatedResponse:
    """
    Generate a new API key for programmatic access.

    The full key is only returned once - store it securely.

    - **name**: A descriptive name for the API key
    - **expires_in_days**: Optional expiration period (1-365 days)
    """
    # TODO: Get current user from auth middleware

    key_id = str(uuid4())
    key = f"ab_{secrets.token_urlsafe(32)}"
    key_prefix = key[:12]

    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # TODO: Store API key hash in database

    return APIKeyCreatedResponse(
        id=key_id,
        name=request.name,
        key_prefix=key_prefix,
        key=key,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        last_used_at=None
    )


@router.get(
    "/api-keys",
    response_model=APIKeyListResponse,
    summary="List all API keys",
    responses={
        200: {"description": "List of API keys"},
        401: {"description": "Not authenticated"}
    }
)
async def list_api_keys(
    db: AsyncSession = Depends(get_db)
) -> APIKeyListResponse:
    """
    List all API keys for the current user.

    Note: Full keys are never returned, only prefixes.
    """
    # TODO: Get current user and fetch API keys from database

    return APIKeyListResponse(items=[], total=0)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
    responses={
        204: {"description": "API key revoked"},
        401: {"description": "Not authenticated"},
        404: {"description": "API key not found"}
    }
)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Revoke an API key.

    - **key_id**: The ID of the API key to revoke
    """
    # TODO: Delete API key from database
    pass


# ============================================================================
# User Endpoints
# ============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Not authenticated"}
    }
)
async def get_me(
    user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get information about the currently authenticated user.
    """
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        provider=user.oauth_provider or "unknown",
        created_at=user.created_at
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Log out the current user",
    responses={
        200: {"description": "Successfully logged out"},
        401: {"description": "Not authenticated"}
    }
)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> LogoutResponse:
    """
    Log out the current user.

    Invalidates the current session and clears authentication cookies.
    """
    # TODO: Invalidate session/token in database

    # Clear auth cookie if using cookies
    response.delete_cookie("access_token")

    return LogoutResponse()
