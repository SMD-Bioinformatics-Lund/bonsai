FROM python:3.11.3

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Create non-root user to run commands
RUN groupadd --gid 1000 worker && useradd -g worker --uid 1000 --shell /user/sbin/nologin --create-home worker

# copy project dir
WORKDIR /home/worker/app
COPY --chown=worker:worker app app/
COPY --chown=worker:worker pyproject.toml setup.py setup.cfg ./

# install dependancies
RUN pip install --no-cache-dir --editable .

RUN mkdir -p /data/signature_db && chown worker:worker /data/signature_db

# run app as non-root user
USER worker
