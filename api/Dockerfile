### Base layer ###
FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install healthcheck dependencies
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache --upgrade pip

### Development layer ###
FROM base AS development

WORKDIR /app

COPY libs/api_client/ ./api_client
COPY api/ ./bonsai_api

RUN pip install -e ./api_client -e ./bonsai_api

HEALTHCHECK --interval=10s --timeout=10s --start-period=30s --retries=3 \
  CMD curl --fail http://localhost:8000/

CMD ["uvicorn", "bonsai_api.main:app", "--reload", "--log-level", "info", "--host", "0.0.0.0"]

### Build python deps ###
FROM base AS python-builder

COPY libs/api_client/ ./api_client
COPY api/ ./api

RUN pip wheel --wheel-dir /wheels ./api_client ./bonsai_api

### Production layer ###
FROM base AS production

# Create non-root user
RUN addgroup --system --gid 1000 worker && \
    adduser --system --uid 1000 --ingroup worker --home /home/worker \
    --shell /usr/sbin/nologin worker

# Set working directory
WORKDIR /app

# Install pre-built python wheels
COPY --from=python-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

HEALTHCHECK --interval=10s --timeout=10s --start-period=30s --retries=3 \
  CMD curl --fail http://localhost:8000/

USER 1000:1000

# Default command
CMD ["uvicorn", "bonsai_api.main:app", "--log-level", "warning", "--host", "0.0.0.0"]
