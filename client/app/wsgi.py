"""Client entrypoint for gunicorn"""

import logging
import os

from .app import create_app

app = create_app()

if __name__ != "__main__":
    # Hook up gunicorn logger to app logger
    if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
