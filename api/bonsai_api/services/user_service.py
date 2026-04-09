"""Service layer for creating and modifying user info."""

from api_client.audit_log import AuditLogClient
from api_client.audit_log.models import Actor, SourceType, Subject

from bonsai_api.auth import get_password_hash
from bonsai_api.crud.user import create_user as insert_user
from bonsai_api.crud.utils import audit_event_context
from bonsai_api.db import Database
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.user import UserInputCreate, UserInputDatabase, UserOutputDatabase


async def create_user_service(
    db_obj: Database,
    user: UserInputCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> UserOutputDatabase:
    """Create a new user in the database with business logic applied."""
    event_subject = Subject(id=user.username, type=SourceType.SYS)
    with audit_event_context(audit, "create_user", ctx, event_subject):
        hashed_password = get_password_hash(user.password)
        user_db_fmt: UserInputDatabase = UserInputDatabase(
            hashed_password=hashed_password, **user.model_dump(exclude="password")
        )
        return await insert_user(db_obj, user_db_fmt)


async def create_user_on_startup(
    db_obj: Database,
    username: str,
    password: str,
    email: str,
    audit: AuditLogClient | None = None,
) -> UserOutputDatabase:
    """Create an admin user on API startup."""
    ctx = ApiRequestContext(
        actor=Actor(id="system", type=SourceType.SYS),
        metadata={},
    )
    user = UserInputCreate(
        username=username,
        password=password,
        email=email,
        roles=["admin"],
    )
    return await create_user_service(db_obj, user, ctx=ctx, audit=audit)
