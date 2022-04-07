"""Main entrypoint for API server."""

from fastapi import FastAPI

from .db.utils import close_mongo_connection, connect_to_mongo
from .internal.middlewares import configure_cors
from .routers import groups, locations, samples, users

app = FastAPI(title="Mimer")

# configure CORS
configure_cors(app)

# configure events
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

# add api routes
app.include_router(groups.router)
app.include_router(samples.router)
app.include_router(users.router)
app.include_router(locations.router)
