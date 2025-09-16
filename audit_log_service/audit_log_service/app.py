"""Define API."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from pymongo import MongoClient

from .db import get_mongo_connection
from .core.config import Settings
from .core.logging import configure_logging
from .version import __version__
from .api import router


def lifespan_factory(settings: Settings, injected_client: MongoClient | None = None):
    """Create API setup and teardown functions."""

    @asynccontextmanager
    async def lifespan(api_app: FastAPI):
        """Instanciate the template repository and add to state."""
        configure_logging(settings)
        client = injected_client or get_mongo_connection(settings)
        api_app.state.database = client

        try:
            yield
        finally:
            if injected_client is None:
                client.close()
    return lifespan


def create_app(settings: Settings, injected_client: MongoClient | None = None) -> FastAPI:
    """Create API."""

    api_app = FastAPI(
        title="Audit Log Service", version=__version__, 
        lifespan=lifespan_factory(settings, injected_client))
    # define routers
    api_app.include_router(router)
    return api_app

config = Settings()
app = create_app(config)
