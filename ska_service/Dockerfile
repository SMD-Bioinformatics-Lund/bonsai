### Base layer ###
FROM python:3.11.3-slim AS base

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

### Build SKA2 ###
FROM rust:1.82-bullseye AS builder

ARG SKA2_VERSION=v0.3.11

WORKDIR /usr/src/ska2

# ska2
RUN \
    git clone https://github.com/bacpop/ska.rust.git \
    && cd ska.rust \
    && git reset --hard ${SKA2_VERSION} \
    && cargo install --path .


### Development layer ###
FROM base AS development

COPY ska_service/ ./ska_service

RUN pip install --editable ./ska_service

# copy ska2 binaries
COPY --from=builder /usr/local/cargo/bin/ska /usr/local/bin/ska

# create default data directory
RUN mkdir -p /data/index_files

CMD ["ska_service"]

### Build python deps ###
FROM base AS python-builder

COPY ska_service/ ./ska_service

RUN pip wheel --wheel-dir /wheels ./ska_service

### Production layer ###
FROM base AS production

# Create non-root user to run commands
RUN addgroup --system --gid 1000 worker && \
    adduser --system --uid 1000 --ingroup worker --home /home/worker \
    --shell /usr/sbin/nologin worker

# copy ska2 binaries
COPY --from=builder /usr/local/cargo/bin/ska /usr/local/bin/ska

# Install pre-built python wheels
COPY --from=python-builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels ska_service && rm -rf /wheels

# create default data directory
RUN mkdir -p /data/index_files && chown -R 1000:1000 /data/index_files

# run app as non-root user
USER 1000:1000

CMD ["ska_service"]