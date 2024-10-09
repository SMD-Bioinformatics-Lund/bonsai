FROM python:3.11.3

LABEL base_image="python:3.8.1-slim"

# Create non-root user to run commands
RUN groupadd --gid 1000 worker && useradd -g worker --uid 1000 --shell /user/sbin/nologin --create-home worker

# copy project dir
WORKDIR /home/worker/app
COPY tests tests/
COPY config.yml requirements.txt ./
RUN mkdir reports

# Change ownership
RUN chown -R worker:worker .

RUN pip install --upgrade pip &&                   \
    pip install --no-cache -r requirements.txt

# run app as non-root user
USER worker