### Base layer ###
FROM python:3.11.13-bullseye AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# git and ca-certificates ship with the non-slim image. Avoid apt here:
# the legacy host requires Bullseye, whose archived repositories are unreliable.

# Keep base tooling up to date
RUN pip install --upgrade pip

WORKDIR /app


### Build javascript ###
FROM node:lts-alpine AS node-builder

WORKDIR /app

COPY frontend/ ./frontend

RUN cd frontend && npm install && npm run build


### Development layer ###
FROM base AS development

# Development convenience: local editable install
COPY frontend/ ./frontend

# Copy built JS to the python-builder context
COPY --from=node-builder /app/frontend/build/ ./frontend/bonsai_app/static/build/

RUN pip install --upgrade setuptools setuptools-scm wheel \
 && pip install --editable ./frontend

EXPOSE 8000
CMD ["flask", "run", "--reload", "--debug", "--host", "0.0.0.0", "--port", "8000"]


### Build python wheels (hermetic) ###
FROM base AS python-builder

# Copy source
COPY frontend/ ./frontend

# Copy built JS to the python-builder context
COPY --from=node-builder /app/frontend/build/ ./frontend/bonsai_app/static/build/

# Remove node artefacts
RUN rm -rf ./frontend/node_modules

# pip builds with PEP 517 isolation, so the build backend has to be in the
# wheelhouse too.
RUN pip wheel --wheel-dir /wheels \
    "setuptools>=61" \
    setuptools-scm>=8 \
    wheel

RUN pip wheel --wheel-dir /wheels ./frontend

### Production layer ###
FROM base AS production

# Create non-root user
RUN addgroup --system --gid 1000 worker && \
    adduser --system --uid 1000 --ingroup worker \
    --home /home/worker --shell /usr/sbin/nologin worker

# Install pre-built wheels only (offline)
COPY --from=python-builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels bonsai_app \
 && rm -rf /wheels

USER 1000:1000

EXPOSE 8000
CMD ["gunicorn", "--log-level", "WARNING", "--bind", "0.0.0.0:8000", "bonsai_app.wsgi:app"]
