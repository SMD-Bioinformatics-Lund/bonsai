"""
Application entry point for the Bonsai API.

This module configures logging, initialises the FastAPI application, manages
startup and shutdown lifecycle concerns (database connections, indexes,
external services, and optional admin bootstrapping), and registers all API
routers, middleware, and exception handlers.
"""

import logging
import logging.config as logging_config
from contextlib import asynccontextmanager

from api_client.audit_log import AuditLogClient
from api_client.notification import NotificationClient
from bonsai_api.db.db import setup_db_connection
from bonsai_api.services.user_service import create_user_on_startup
from fastapi import FastAPI

from .config import Settings, settings
from .extensions.ldap_extension import ldap_connection
from .internal.middlewares import configure_cors
from .internal.error_handlers import register_exception_handlers
from .routers import (
    auth,
    analysis,
    cluster,
    export,
    files,
    groups,
    jobs,
    locations,
    memberships,
    root,
    samples,
    users,
    pipeline_run,
    reference_genomes,
)

logging_config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            }
        },
        "root": {"level": "DEBUG", "handlers": ["wsgi"]},
    }
)
LOG = logging.getLogger(__name__)


async def ensure_database_setup(db):
    """Ensure all database indexes are created and collections are available."""
    from bonsai_api.db.index import INDEXES

    LOG.info("Ensuring database indexes are created.")
    for col_name, indexes in INDEXES.items():
        if col_name == "curations":
            collection = db.curations_collection
        else:
            collection = getattr(db, f"{col_name}_collection")
        for idx in indexes:
            try:
                await collection.create_index(idx["definition"], **idx["options"])
                LOG.info(f"Created or ensured index {idx['options']['name']} on {col_name}")
            except Exception as e:
                LOG.warning(f"Failed to create index {idx['options']['name']} on {col_name}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and teardown events."""
    # setup database connection
    if not settings.mongodb_uri:
        raise RuntimeError("Database connection has not been configured")
    db = setup_db_connection(settings.mongodb_uri, db_name=settings.database_name)
    app.state.db = db
    # ensure database indexes and collections
    await ensure_database_setup(db)
    # setup ldap conneciton
    if settings.use_ldap_auth:
        ldap_connection.init_app()
    # setup connection to accessory services
    if settings.audit_log_service_api is not None:
        app.state.audit_log = AuditLogClient(
            base_url=str(settings.audit_log_service_api)
        )
    if settings.notification_service_api is not None:
        app.state.notification = NotificationClient(
            base_url=str(settings.notification_service_api)
        )

    if settings.bonsai_admin_user:

        if not settings.bonsai_admin_password:
            LOG.error(
                "Admin user configured without password, skipping admin user creation."
            )
        else:
            LOG.info(
                "Admin user configured, seeding database with admin user if no users exist."
            )
            if await db.user_collection.count_documents({}) == 0:
                admin_email = (
                    settings.bonsai_admin_mail
                    or f"{settings.bonsai_admin_user}@example.com"
                )
                await create_user_on_startup(
                    db,
                    username=settings.bonsai_admin_user,
                    password=settings.bonsai_admin_password,
                    email=admin_email,
                    audit=getattr(app.state, "audit_log", None),
                )
                LOG.info("Created admin user %s on startup.", settings.bonsai_admin_user)

    yield
    # teardown
    await db.close()
    app.state.db = None
    if settings.use_ldap_auth:
        ldap_connection.teardown()


def create_app(settings: Settings) -> FastAPI:
    """Create Bonsai API"""

    app = FastAPI(title="Bonsai", lifespan=lifespan)
    # configure CORS
    configure_cors(app)

    # check if api authentication is disabled
    if not settings.api_authentication:
        LOG.warning("API authentication disabled!")
    
    # admin user bootstrap is handled during lifespan startup
    
    # register routers
    app.include_router(analysis.router)
    app.include_router(auth.router)
    app.include_router(cluster.router)
    app.include_router(export.router)
    app.include_router(files.router)
    app.include_router(groups.router)
    app.include_router(jobs.router)
    app.include_router(locations.router)
    app.include_router(memberships.router)
    app.include_router(pipeline_run.router)
    app.include_router(reference_genomes.router)
    app.include_router(root.router)
    app.include_router(samples.router)
    app.include_router(users.router)

    # Register error handlers
    register_exception_handlers(app)

    return app


app = create_app(settings)
