################
# BUILDER NODE #
################

FROM node:lts-alpine AS node-builder
WORKDIR /usr/src/app
COPY package.json package-lock.json webpack.config.cjs tsconfig.json ./
COPY web web
RUN npm install && npm run build

#############
# BUILD APP #
#############

FROM python:3.11.3

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Create non-root user to run commands
RUN groupadd --gid 1000 worker && useradd -g worker --uid 1000 --shell /user/sbin/nologin --create-home worker

# copy project dir
WORKDIR /home/worker/app
COPY bonsai_app bonsai_app/
COPY pyproject.toml setup.py setup.cfg ./

# Copy compiled web assets
COPY --from=node-builder /usr/src/app/build/*/bonsai.min.* bonsai_app/blueprints/public/static/

# Change ownership
RUN chown -R worker:worker .

# install dependancies
RUN pip install --no-cache-dir .

# run app as non-root user
USER worker

CMD ["gunicorn", "--log-level", "WARNING", "--bind", "0.0.0.0:8000", "bonsai_app.wsgi:app"]