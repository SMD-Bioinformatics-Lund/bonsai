FROM python:3.11.3-slim as base

WORKDIR /app

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY pyproject.toml audit_log_service/ /app/
RUN pip install --upgrade pip && pip wheel --wheel-dir /wheels .

FROM base

COPY --from=builder /wheels /wheels

# Create non-root user to run commands
RUN groupadd --gid 1000 worker && useradd -g worker --uid 1000 --shell /user/sbin/nologin --create-home worker
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY /audit_log_service /app/src/
ENV PYTHONPATH=/app/src
EXPOSE 8080
CMD ["uvicorn", "audit_log_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
