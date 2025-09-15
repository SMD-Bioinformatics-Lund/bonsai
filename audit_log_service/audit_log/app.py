"""Define API."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .db import close_mongo_client, get_mongo_client
from .core.config import Settings
from .core.logging import configure_logging
from .version import __version__

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Instanciate the template repository and add to state."""
    configure_logging(settings)
    get_mongo_client(settings)

    yield

    close_mongo_client()


def create_app() -> FastAPI:
    """Create API."""

    app = FastAPI(title="Audit Log Service", version=__version__, lifespan=lifespan)
    # define routers
    return app

app = create_app()
