from fastapi.middleware.cors import CORSMiddleware
from ..config import allowed_origins


def configure_cors(app):
    """Configure cros site resource sharing for API.

    configuration is only applied if there are allowed origins specified in config
    """
    if len(allowed_origins) > 0:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
