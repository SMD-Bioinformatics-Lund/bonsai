### Base layer ###
FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

### Build javascript ###
FROM node:lts-alpine AS node-builder

WORKDIR /usr/src/app

COPY package.json package-lock.json webpack.config.cjs tsconfig.json ./
COPY web web

RUN npm install && npm run build

### Development layer ###
FROM base AS development

COPY frontend/  ./frontend

RUN pip install --editable ./frontend

EXPOSE 8000

CMD ["flask", "run", "--reload", "--debug", "--host", "0.0.0.0", "--port", "8000"]

### Build python deps ###
FROM base AS python-builder

COPY frontend/  ./frontend

RUN pip wheel --wheel-dir /wheels ./frontend

### Production layer ###
FROM base AS production

# Create non-root user
RUN addgroup --system --gid 1000 worker && \
    adduser --system --uid 1000 --ingroup worker --home /home/worker \
    --shell /usr/sbin/nologin worker

# Install pre-built python wheels
COPY --from=python-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy built JavaScript
COPY --from=node-builder /usr/src/app/build/*/bonsai.min.* bonsai_app/blueprints/public/static/

USER 1000:1000

EXPOSE 8000

CMD ["gunicorn", "--log-level", "WARNING", "--bind", "0.0.0.0:8000", "bonsai_app.wsgi:app"]