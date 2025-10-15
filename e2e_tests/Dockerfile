FROM python:3.11.3

# copy project dir
ENV PYTHONDONTWRITEBYTECODE=1       \
    PYTHONUNBUFFERED=1              \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1              \
    PYTHONPATH=/app

WORKDIR /app
COPY pages pages/
COPY tests tests/
COPY fixtures fixtures/
COPY config.yml requirements.txt e2e_test_entrypoint.sh ./

# install deps
RUN pip install -r requirements.txt

# create folder for test reports
RUN mkdir -p /data/reports

ENTRYPOINT [ "/app/e2e_test_entrypoint.sh" ]

CMD pytest --html=/data/reports/e2e_report.html --self-contained-html