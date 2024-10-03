"""Main entrypoint for API server."""

import logging
import logging.config as logging_config

from fastapi import FastAPI

from .config import settings
from .extensions.ldap_extension import ldap_connection
from .internal.middlewares import configure_cors
from .routers import (
    auth,
    cluster,
    export,
    groups,
    jobs,
    locations,
    resources,
    root,
    samples,
    users,
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

app = FastAPI(title="Bonsai")

# configure CORS
configure_cors(app)

# check if api authentication is disabled
if not settings.api_authentication:
    LOG.warning("API authentication disabled!")

# configure events
if settings.use_ldap_auth:
    app.add_event_handler("startup", ldap_connection.init_app)
    app.add_event_handler("shutdown", ldap_connection.teardown)


# add api routes
app.include_router(root.router)
app.include_router(users.router)
app.include_router(samples.router)
app.include_router(groups.router)
app.include_router(locations.router)
app.include_router(cluster.router)
app.include_router(export.router)
app.include_router(resources.router)
app.include_router(auth.router)
app.include_router(jobs.router)
