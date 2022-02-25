"""Main entrypoint for API server."""

from fastapi import Depends, FastAPI
from .routers import collections, samples
from .db.utils import close_mongo_connection, connect_to_mongo

app = FastAPI(title="Mimer")

app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)
app.include_router(collections.router)
app.include_router(samples.router)
