FROM python:3.11.3

# install shared modules
WORKDIR /app
COPY bonsai_modules bonsai_modules/
COPY pyproject.toml ./

# install dependancies
RUN pip install pip --upgrade && pip install --no-cache-dir .