FROM python:3.11.3

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN groupadd --gid 1000 worker && useradd -g worker --uid 1000 --shell /usr/sbin/nologin --create-home worker

# Set working directory
WORKDIR /home/worker/app

# Copy your main app and bonsai-prp (which is symlinked and resolved)
COPY bonsai_api bonsai_api/
COPY setup.py setup.cfg pyproject.toml ./
COPY bonsai-prp bonsai-prp/

# Set ownership
RUN chown -R worker:worker .

# Install dependencies
RUN pip install --no-cache-dir . && pip install --no-cache-dir --force-reinstall ./bonsai-prp

# Create necessary runtime dirs
RUN mkdir -p /data/signature_db && chown worker:worker /data/signature_db

# Switch to non-root user
USER worker

# Default command
CMD ["uvicorn", "bonsai_api.main:app", "--log-level", "info", "--host", "0.0.0.0"]
