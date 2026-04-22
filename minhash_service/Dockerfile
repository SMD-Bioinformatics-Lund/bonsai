# Base image
FROM python:3.14.4-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build requirements (only needed for compiling wheel

FROM base AS build-deps

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    pkg-config \
    rustc \
    cargo \
    curl \
    && rm -rf /var/lib/apt/lists

# Build sourmash / branchwater plugin wheels

FROM build-deps AS branchwater-builder

WORKDIR /src/branchwater

RUN curl -L https://github.com/sourmash-bio/sourmash_plugin_branchwater/archive/refs/tags/v0.9.14.tar.gz \
    | tar xz --strip-components=1

RUN pip wheel --wheel-dir /wheels .

# Build application wheels

FROM build-deps AS python-builder

WORKDIR /src

COPY libs/api_client ./api_client
COPY minhash_service ./minhash_service

RUN pip wheel --wheel-dir /wheels \
    ./api_client \
    ./minhash_service


# Development layer

FROM build-deps AS development

WORKDIR /app

COPY libs/api_client ./api_client
COPY minhash_service ./minhash_service
COPY --from=branchwater-builder /wheels /wheels

RUN pip install -e ./api_client -e ./minhash_service /wheels/*

# Dev-only runtime convenience
RUN mkdir -p /data/signature_db

CMD ["bash"]

# Production layer

FROM base AS production

# Create non-root user early
RUN addgroup --system --gid 1000 worker && \
    adduser --system --uid 1000 --ingroup worker \
    --home /home/worker --shell /usr/sbin/nologin worker

# Install wheels only
COPY --from=python-builder /wheels /wheels
COPY --from=branchwater-builder /wheels /branchwater-wheels

RUN pip install --no-index \
        --find-links=/wheels \
        --find-links=/branchwater-wheels \
        minhash_service \
        sourmash_plugin_branchwater \
    && rm -rf /wheels /branchwater-wheels

# Runtime directories
RUN mkdir -p /data/signature_db && \
    chown -R worker:worker /data/signature_db

USER worker

CMD ["minhash-service", "--version"]