FROM python:3.11.3-slim

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user to run commands
RUN groupadd --gid 1000 worker && useradd -g worker --uid 1000 --shell /user/sbin/nologin --create-home worker

# create custom template directory
RUN mkdir -p /data/templates && chown 1000:1000 /data/templates

# copy project dir
WORKDIR /home/worker/app
COPY --chown=worker:worker notification_service notification_service/
COPY --chown=worker:worker pyproject.toml ./

# install dependancies
RUN pip install --upgrade pip && pip install --no-cache-dir --editable .

# run app as non-root user
USER worker

CMD ["uvicorn", "audit_log_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
