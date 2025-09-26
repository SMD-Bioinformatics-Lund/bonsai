### Base layer ###
FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

### Development layer ###
FROM base AS development

COPY libs/api_client/ ./api_client
COPY minhash_service/ ./minhash_service

RUN pip install -e ./api_client -e ./minhash_service

# Dev-only: create default signature directory (owned by root in dev; bind mount in practice)
RUN mkdir -p /data/signature_db

### Build wheels ###
FROM base AS python-builder

COPY libs/api_client/ ./api_client
COPY minhash_service/ ./minhash_service

RUN pip wheel --wheel-dir /wheels ./api_client ./minhash_service

### Production layer ###
FROM base AS production

RUN addgroup --system --gid 1000 worker && \
    adduser --system --uid 1000 --ingroup worker --home /home/worker \
    --shell /usr/sbin/nologin worker

COPY --from=python-builder /wheels /wheels

RUN pip install --no-index --find-links=/wheels minhash_service && rm -rf /wheels

# create default signature directory
RUN mkdir -p /data/signature_db && chown -R 1000:1000 /data/signature_db

USER 1000:1000

CMD ["minhash-service", "--version"]