FROM python:3.11.3-slim

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user to run commands
RUN groupadd --gid 1000 worker && useradd -g worker --uid 1000 --shell /user/sbin/nologin --create-home worker

# create default data directory
RUN mkdir -p /data/signature_db && chown worker:worker /data/signature_db

# copy project dir
WORKDIR /home/worker/app
COPY --chown=worker:worker minhash_service minhash_service/
COPY --chown=worker:worker README.md pyproject.toml setup.py setup.cfg ./

# install dependancies
RUN pip install --no-cache-dir --editable .

# run app as non-root user
USER worker

CMD ["minhash-service", "--version"]