# Base image
FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build application wheels

FROM base AS python-builder

WORKDIR /src

COPY libs/api_client ./api_client
COPY minhash_service ./minhash_service

RUN pip wheel --wheel-dir /wheels \
    ./api_client \
    ./minhash_service


# Development layer

FROM continuumio/miniconda3 AS development

WORKDIR /app

RUN /opt/conda conda install -c conda-forge -y python=3.11.3 pip sourmash_plugin_branchwater

COPY libs/api_client ./api_client
COPY minhash_service ./minhash_service

RUN pip install -e ./api_client -e ./minhash_service

# Dev-only runtime convenience
RUN mkdir -p /data/signature_db

CMD ["bash"]

# Production layer

FROM continuumio/miniconda3 AS production

RUN opt/conda/bin/conda init \
    && /opt/conda/bin/conda install -c conda-forge -y python=3.11.3 pip sourmash_plugin_branchwater

# Create non-root user early
RUN addgroup --system --gid 1000 worker && \
    adduser --system --uid 1000 --ingroup worker \
    --home /home/worker --shell /usr/sbin/nologin worker

# Install wheels only
COPY --from=python-builder /wheels /wheels

RUN pip install --no-index \
        --find-links=/wheels \
        minhash_service \
    && rm -rf /wheels

# Runtime directories
RUN mkdir -p /data/signature_db && \
    chown -R worker:worker /data/signature_db

USER worker

CMD ["minhash-service", "--version"]