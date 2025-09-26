### Base layer ###
FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Minimal packages + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

### Development layer ###
FROM base AS development

WORKDIR /app

COPY audit_log_service/ ./audit_log_service

RUN pip install --editable ./audit_log_service

CMD ["uvicorn", "audit_log_service.app:app", "--reload", "--log-level", "debug", "--host", "0.0.0.0"]

### Build python deps ###
FROM base AS python-builder

COPY audit_log_service/ ./audit_log_service

RUN pip wheel --wheel-dir /wheels ./audit_log_service

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

# run app as non-root user
USER 1000:1000

CMD ["uvicorn", "audit_log_service.app:app", "--host", "0.0.0.0"]
