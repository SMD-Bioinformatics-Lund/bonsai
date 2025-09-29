"""Contains applicaiton factory function."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import Redis
from rq import Queue, SimpleWorker

from .api import router
from .config import settings
from .services.templates import TemplateRepository
from .utils import configure_logging


def create_worker_app() -> SimpleWorker:
    """Create email notificatoin service worker."""
    configure_logging(settings)
    log = logging.getLogger(__name__)
    log.info("Setup redis connection: %s:%s", settings.redis.host, settings.redis.port)
    redis = Redis(host=settings.redis.host, port=settings.redis.port)
    queue = Queue(settings.redis.queue, connection=redis)
    worker = SimpleWorker([queue], connection=redis)

    return worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Instanciate the template repository and add to state."""
    app.state.template_repo = TemplateRepository(
        custom_template_dir=settings.template_dir,
        default_template="default.html",
    )
    yield


def create_api_app() -> FastAPI:
    """Create email notification rest api."""
    configure_logging(settings)
    log = logging.getLogger(__name__)
    log.info("Setup API")

    app = FastAPI(title="Notification service", lifespan=lifespan)
    app.include_router(router)

    return app
