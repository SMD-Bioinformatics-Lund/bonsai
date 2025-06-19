FROM python:3.11.3

# install shared models and modules
WORKDIR /app
COPY bonsai_models bonsai_models/
COPY pyproject.toml ./

# install dependancies
RUN pip install pip --upgrade && pip install --no-cache-dir .