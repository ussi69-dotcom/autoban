"""Organization management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ============================================================================
# Enums
# ============================================================================

class MemberRole(str, Enum):
    """Roles that can be assigned to organization members."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InviteStatus(str, Enum):
    """Status of organization invitations."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


# ============================================================================
# Pydantic Schemas
# ============================================================================

class OrganizationCreate(BaseModel):
    """Request schema for creating an organization."""
    name: str = Field(..., min_length=2, max_length=100, description="Organization name")
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$",
                      description="URL-friendly identifier")
    description: Optional[str] = Field(None, max_length=500, description="Organization description")


class OrganizationUpdate(BaseModel):
    """Request schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Response schema for organization details."""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    member_count: int
    project_count: int
    created_at: datetime
    updated_at: datetime


class OrganizationListResponse(BaseModel):
    """Response containing paginated list of organizations."""
    items: list[OrganizationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class MemberResponse(BaseModel):
    """Response schema for organization member details."""
    id: str
    user_id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: MemberRole
    joined_at: datetime


class MemberListResponse(BaseModel):
    """Response containing list of organization members."""
    items: list[MemberResponse]
    total: int


class MemberInvite(BaseModel):
    """Request schema for inviting a member."""
    email: EmailStr = Field(..., description="Email address of the user to invite")
    role: MemberRole = Field(MemberRole.MEMBER, description="Role to assign to the invited user")


class MemberRoleUpdate(BaseModel):
    """Request schema for updating a member's role."""
    role: MemberRole = Field(..., description="New role for the member")


class InvitationResponse(BaseModel):
    """Response schema for invitation details."""
    id: str
    email: str
    role: MemberRole
    status: InviteStatus
    invited_by: str
    created_at: datetime
    expires_at: datetime


class InvitationListResponse(BaseModel):
    """Response containing list of pending invitations."""
    items: list[InvitationResponse]
    total: int


# ============================================================================
# Organization CRUD Endpoints
# ============================================================================

@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
    responses={
        201: {"description": "Organization created successfully"},
        400: {"description": "Invalid input or slug already taken"},
        401: {"description": "Not authenticated"}
    }
)
async def create_organization(
    request: OrganizationCreate,
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """
    Create a new organization.

    The creating user becomes the owner of the organization.

    - **name**: Display name for the organization
    - **slug**: URL-friendly identifier (must be unique)
    - **description**: Optional description
    """
    # TODO: Check if slug is already taken
    # TODO: Create organization in database
    # TODO: Add current user as owner

    org_id = str(uuid4())
    now = datetime.utcnow()

    return OrganizationResponse(
        id=org_id,
        name=request.name,
        slug=request.slug,
        description=request.description,
        avatar_url=None,
        member_count=1,
        project_count=0,
        created_at=now,
        updated_at=now
    )


@router.get(
    "",
    response_model=OrganizationListResponse,
    summary="List organizations",
    responses={
        200: {"description": "List of organizations the user belongs to"},
        401: {"description": "Not authenticated"}
    }
)
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
) -> OrganizationListResponse:
    """
    List all organizations the current user belongs to.

    Returns paginated results sorted by name.
    """
    # TODO: Fetch organizations for current user from database

    return OrganizationListResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
        has_more=False
    )


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get organization details",
    responses={
        200: {"description": "Organization details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Organization not found"}
    }
)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """
    Get details of a specific organization.

    - **org_id**: Organization ID or slug
    """
    # TODO: Fetch organization from database
    # TODO: Check user has access

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Organization not found"
    )


@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Update organization",
    responses={
        200: {"description": "Organization updated successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only admins and owners can update organization"},
        404: {"description": "Organization not found"}
    }
)
async def update_organization(
    org_id: str,
    request: OrganizationUpdate,
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """
    Update an organization's details.

    Only organization admins and owners can perform this action.

    - **org_id**: Organization ID
    """
    # TODO: Fetch and update organization
    # TODO: Check user has admin/owner role

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Organization not found"
    )


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization",
    responses={
        204: {"description": "Organization deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only owners can delete organization"},
        404: {"description": "Organization not found"}
    }
)
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete an organization.

    This action is irreversible and removes all associated projects and data.
    Only organization owners can perform this action.

    - **org_id**: Organization ID
    """
    # TODO: Delete organization and all associated data
    # TODO: Check user is owner
    pass


# ============================================================================
# Member Management Endpoints
# ============================================================================

@router.get(
    "/{org_id}/members",
    response_model=MemberListResponse,
    summary="List organization members",
    responses={
        200: {"description": "List of organization members"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Organization not found"}
    }
)
async def list_members(
    org_id: str,
    role: Optional[MemberRole] = Query(None, description="Filter by role"),
    db: AsyncSession = Depends(get_db)
) -> MemberListResponse:
    """
    List all members of an organization.

    - **org_id**: Organization ID
    - **role**: Optional filter by member role
    """
    # TODO: Fetch members from database

    return MemberListResponse(items=[], total=0)


@router.post(
    "/{org_id}/members/invite",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a member",
    responses={
        201: {"description": "Invitation sent successfully"},
        400: {"description": "User already a member or invitation pending"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only admins and owners can invite members"},
        404: {"description": "Organization not found"}
    }
)
async def invite_member(
    org_id: str,
    request: MemberInvite,
    db: AsyncSession = Depends(get_db)
) -> InvitationResponse:
    """
    Invite a user to join the organization.

    An email will be sent to the invited user with a link to accept the invitation.

    - **org_id**: Organization ID
    - **email**: Email address of the user to invite
    - **role**: Role to assign (cannot invite as owner)
    """
    if request.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite users as owners"
        )

    # TODO: Check user doesn't already exist
    # TODO: Create invitation in database
    # TODO: Send invitation email

    invite_id = str(uuid4())
    now = datetime.utcnow()

    return InvitationResponse(
        id=invite_id,
        email=request.email,
        role=request.role,
        status=InviteStatus.PENDING,
        invited_by="current_user_id",  # TODO: Get from auth
        created_at=now,
        expires_at=datetime.utcnow()  # TODO: Add 7 days
    )


@router.get(
    "/{org_id}/invitations",
    response_model=InvitationListResponse,
    summary="List pending invitations",
    responses={
        200: {"description": "List of pending invitations"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Organization not found"}
    }
)
async def list_invitations(
    org_id: str,
    db: AsyncSession = Depends(get_db)
) -> InvitationListResponse:
    """
    List all pending invitations for an organization.

    - **org_id**: Organization ID
    """
    # TODO: Fetch pending invitations

    return InvitationListResponse(items=[], total=0)


@router.delete(
    "/{org_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel an invitation",
    responses={
        204: {"description": "Invitation cancelled"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only admins and owners can cancel invitations"},
        404: {"description": "Invitation not found"}
    }
)
async def cancel_invitation(
    org_id: str,
    invitation_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Cancel a pending invitation.

    - **org_id**: Organization ID
    - **invitation_id**: Invitation ID
    """
    # TODO: Delete invitation
    pass


@router.patch(
    "/{org_id}/members/{member_id}",
    response_model=MemberResponse,
    summary="Update member role",
    responses={
        200: {"description": "Member role updated"},
        400: {"description": "Invalid role change"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only owners can change roles"},
        404: {"description": "Member not found"}
    }
)
async def update_member_role(
    org_id: str,
    member_id: str,
    request: MemberRoleUpdate,
    db: AsyncSession = Depends(get_db)
) -> MemberResponse:
    """
    Update a member's role in the organization.

    Only organization owners can change member roles.
    Cannot demote the last owner.

    - **org_id**: Organization ID
    - **member_id**: Member ID
    - **role**: New role
    """
    # TODO: Update member role
    # TODO: Check cannot demote last owner

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Member not found"
    )


@router.delete(
    "/{org_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member",
    responses={
        204: {"description": "Member removed"},
        400: {"description": "Cannot remove last owner"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only admins and owners can remove members"},
        404: {"description": "Member not found"}
    }
)
async def remove_member(
    org_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Remove a member from the organization.

    Cannot remove the last owner.

    - **org_id**: Organization ID
    - **member_id**: Member ID
    """
    # TODO: Remove member
    # TODO: Check not removing last owner
    pass


@router.post(
    "/{org_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave organization",
    responses={
        204: {"description": "Successfully left organization"},
        400: {"description": "Cannot leave as last owner"},
        401: {"description": "Not authenticated"},
        404: {"description": "Not a member of this organization"}
    }
)
async def leave_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Leave an organization.

    Cannot leave if you are the last owner - transfer ownership first.

    - **org_id**: Organization ID
    """
    # TODO: Remove current user from organization
    pass
