"""Main entrypoint for API server."""

from fastapi import FastAPI

from .db.utils import close_mongo_connection, connect_to_mongo
from .internal.middlewares import configure_cors
from .routers import root, auth, groups, locations, samples, users, cluster

app = FastAPI(title="Bonsai")

# configure CORS
configure_cors(app)

# configure events
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

# add api routes
app.include_router(root.router)
app.include_router(users.router)
app.include_router(samples.router)
app.include_router(groups.router)
app.include_router(locations.router)
app.include_router(cluster.router)
app.include_router(auth.router)
