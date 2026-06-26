"""Service layer helpers."""

from fastapi import Request

from bonsai_api.models.enums import FileSources


def normalize_roles(user_roles: list[str]) -> list[str]:
    """Normalize user roles to lowercase stripped strings."""
    if not user_roles:
        return []
    return [str(r).strip().lower() for r in user_roles if r is not None]


def is_admin(user_roles: list[str]) -> bool:
    """Check if user roles include admin."""
    return "admin" in normalize_roles(user_roles)


def resolve_resource_url(request: Request, source: FileSources, resource: str) -> str:
    """Resolve a resource URI to an accessible URL."""
    return str(request.url_for('file-resource', source=source, path=resource))

