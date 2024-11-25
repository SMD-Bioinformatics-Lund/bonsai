##############
# Build SKA2 #
##############
FROM rust:1.82-bullseye AS builder

ARG SKA2_VERSION=v0.3.11

WORKDIR /usr/src/ska2

# ska2
RUN \
    git clone https://github.com/bacpop/ska.rust.git \
    && cd ska.rust \
    && git reset --hard ${SKA2_VERSION} \
    && cargo install --path .


FROM python:3.11.3

# Create non-root user to run commands
RUN groupadd --gid 1000 worker && useradd -g worker --uid 1000 --shell /user/sbin/nologin --create-home worker

# ska2
COPY --from=builder /usr/local/cargo/bin/ska /usr/local/bin/ska

# create default data directory
RUN mkdir -p /data/index_files

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# copy project dir
WORKDIR /home/worker/app
COPY --chown=worker:worker ska_service ska_service/
COPY --chown=worker:worker README.md pyproject.toml setup.py setup.cfg ./

# install dependancies
RUN pip install --no-cache-dir --editable .

# run app as non-root user
USER worker

CMD ["ska_service"]