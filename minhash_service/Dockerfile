FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

FROM base AS dev

WORKDIR /app

COPY libs/api_client/ ./api_client
COPY minhash_service/ ./minhash_service

RUN pip install -e ./api_client -e ./minhash_service

# create default signature directory
RUN mkdir -p /data/signature_db

FROM base AS python-builder

WORKDIR /app
COPY libs/api_client/ ./api_client
COPY minhash_service/ ./minhash_service

RUN pip wheel --wheel-dir /wheels ./api_client ./minhash_service

FROM base AS prod

COPY --from=python-builder /wheels /wheels

RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# create default signature directory
RUN mkdir -p /data/signature_db

CMD ["minhash-service", "--version"]