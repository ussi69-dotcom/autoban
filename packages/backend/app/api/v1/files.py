"""File browsing endpoints."""

from pathlib import Path
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.config import get_settings
from app.models import User


router = APIRouter(prefix="/files", tags=["Files"])

settings = get_settings()

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
IGNORED_NAMES = {
    ".git",
    ".next",
    ".turbo",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}


def find_repo_root(start: Path) -> Path:
    """Locate the repository root by walking upwards for turbo.json."""
    for candidate in [start, *start.parents]:
        if (candidate / "turbo.json").exists():
            return candidate
    return start


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
WORKSPACE_ROOT = Path(settings.agent_workspace_path)
BASE_ROOT = WORKSPACE_ROOT if WORKSPACE_ROOT.exists() and WORKSPACE_ROOT.is_dir() else REPO_ROOT


def is_within_base(path: Path, base: Path) -> bool:
    """Check that a resolved path stays inside the base directory."""
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def normalize_relative_path(path: Optional[str]) -> str:
    """Normalize the request path to a safe relative path."""
    if not path:
        return ""
    if Path(path).is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path must be relative"
        )
    return path.strip().lstrip("/")


def resolve_path(path: Optional[str]) -> Path:
    """Resolve a request path into an absolute path within the base root."""
    relative = normalize_relative_path(path)
    resolved = (BASE_ROOT / relative).resolve()
    if not is_within_base(resolved, BASE_ROOT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path"
        )
    return resolved


def to_relative_string(path: Path) -> str:
    """Convert a resolved path to a workspace-relative string."""
    relative = path.relative_to(BASE_ROOT)
    return "" if relative == Path(".") else relative.as_posix()


def is_binary_file(path: Path) -> bool:
    """Heuristic binary detection to avoid loading non-text files."""
    try:
        with path.open("rb") as handle:
            sample = handle.read(4096)
    except OSError:
        return True
    return b"\x00" in sample


def iter_visible_entries(directory: Path):
    """Yield directory entries while filtering hidden/ignored names."""
    for entry in directory.iterdir():
        if entry.name.startswith(".") or entry.name in IGNORED_NAMES:
            continue
        yield entry


def has_visible_children(directory: Path) -> bool:
    """Check whether a directory has visible entries."""
    try:
        for _ in iter_visible_entries(directory):
            return True
    except OSError:
        return False
    return False


class FileEntry(BaseModel):
    """File tree entry."""

    name: str = Field(..., description="Entry name")
    path: str = Field(..., description="Relative path from workspace root")
    type: Literal["file", "directory"] = Field(..., description="Entry type")
    extension: Optional[str] = Field(None, description="File extension without dot")
    size: Optional[int] = Field(None, description="File size in bytes")
    has_children: Optional[bool] = Field(None, description="Directory has visible children")


class FileTreeResponse(BaseModel):
    """Response schema for file tree listing."""

    path: str = Field(..., description="Requested path")
    entries: list[FileEntry]


class FileTreeApiResponse(BaseModel):
    """Wrapped response schema for file tree listing."""

    data: FileTreeResponse


class FileContentResponse(BaseModel):
    """Response schema for file content."""

    path: str = Field(..., description="File path")
    content: str = Field(..., description="File contents")


class FileContentApiResponse(BaseModel):
    """Wrapped response schema for file content."""

    data: FileContentResponse

@router.get(
    "",
    response_model=FileTreeApiResponse,
    summary="List files in a directory",
    responses={
        200: {"description": "Directory listing"},
        400: {"description": "Invalid path"},
        401: {"description": "Not authenticated"},
        404: {"description": "Directory not found"},
    }
)
async def list_files(
    path: Optional[str] = Query(None, description="Relative path to list"),
    user: User = Depends(get_current_user),
) -> FileTreeApiResponse:
    """
    List files and folders at the given path.

    - **path**: Relative path from workspace root
    """
    _ = user
    directory = resolve_path(path)
    if not directory.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Path not found"
        )
    if not directory.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a directory"
        )

    entries: list[FileEntry] = []
    try:
        visible_entries = list(iter_visible_entries(directory))
    except OSError:
        visible_entries = []

    for entry in sorted(visible_entries, key=lambda item: (item.is_file(), item.name.lower())):
        relative_path = entry.relative_to(BASE_ROOT).as_posix()
        if entry.is_dir():
            entries.append(
                FileEntry(
                    name=entry.name,
                    path=relative_path,
                    type="directory",
                    has_children=has_visible_children(entry),
                )
            )
        else:
            entries.append(
                FileEntry(
                    name=entry.name,
                    path=relative_path,
                    type="file",
                    extension=entry.suffix.lstrip(".") or None,
                    size=entry.stat().st_size,
                )
            )

    return FileTreeApiResponse(
        data=FileTreeResponse(
            path=to_relative_string(directory),
            entries=entries,
        )
    )


@router.get(
    "/{path:path}",
    response_model=FileContentApiResponse,
    summary="Read a file",
    responses={
        200: {"description": "File content"},
        400: {"description": "Invalid path or directory"},
        401: {"description": "Not authenticated"},
        404: {"description": "File not found"},
        413: {"description": "File too large"},
        415: {"description": "Binary files are not supported"},
    }
)
async def read_file(
    path: str,
    user: User = Depends(get_current_user),
) -> FileContentApiResponse:
    """
    Read file content as UTF-8 text.

    - **path**: Relative file path from workspace root
    """
    _ = user
    file_path = resolve_path(path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    if file_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is a directory"
        )

    try:
        size = file_path.stat().st_size
    except OSError:
        size = MAX_FILE_SIZE_BYTES + 1
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large"
        )

    if is_binary_file(file_path):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Binary files are not supported"
        )

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file"
        )

    return FileContentApiResponse(
        data=FileContentResponse(
            path=to_relative_string(file_path),
            content=content,
        )
    )
