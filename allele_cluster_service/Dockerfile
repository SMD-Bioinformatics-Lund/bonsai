### Base layer ###
FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache --upgrade pip

### Development layer ###
FROM base AS development

WORKDIR /app

COPY allele_cluster_service/ ./allele_cluster_service

RUN pip install --editable ./allele_cluster_service

CMD ["cluster_service"]

### Build python deps ###
FROM base AS python-builder

COPY allele_cluster_service/ ./allele_cluster_service

RUN pip wheel --wheel-dir /wheels ./allele_cluster_service

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

# run app as non-root user
USER 1000:1000

CMD ["cluster_service"]