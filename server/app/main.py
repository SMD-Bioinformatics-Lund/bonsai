"""Main entrypoint for API server."""

from fastapi import Depends, FastAPI
from .routers import groups, samples, users, locations
from .db.utils import close_mongo_connection, connect_to_mongo
from .internal.middlewares import configure_cors


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
