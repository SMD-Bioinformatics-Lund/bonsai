### Base layer ###
FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade pip

### Development layer ###
FROM base AS development

WORKDIR /app

COPY notification_service/ ./notification_service

RUN pip install --editable ./notification_service

# create directory for custom templates
RUN mkdir -p /data/templates

CMD ["uvicorn", "notification_service.main:create_api_app", "--reload", "--log-level", "debug", "--host", "0.0.0.0"]

### Build python deps ###
FROM base AS python-builder

COPY notification_service/ ./notification_service

RUN pip wheel --wheel-dir /wheels ./notification_service

### Production layer ###
FROM base AS production

# Create non-root user to run commands
RUN addgroup --system --gid 1000 worker && \
    adduser --system --uid 1000 --ingroup worker --home /home/worker \
    --shell /usr/sbin/nologin worker

# Set working directory
WORKDIR /app

# Install pre-built python wheels
COPY --from=python-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# create custom template directory
RUN mkdir -p /data/templates && chown 1000:1000 /data/templates

# run app as non-root user
USER 1000:1000

CMD ["uvicorn", "notification_service.main:create_api_app", "--host", "0.0.0.0"]