FROM python:3.11.3

LABEL base_image="python:3.11.3-slim"

# copy project dir
WORKDIR /app
COPY tests tests/
COPY fixtures fixtures/
COPY config.yml requirements.txt e2e_test_entrypoint.sh ./
RUN mkdir -p /app/reports

RUN pip install --upgrade pip &&                   \
    pip install --no-cache -r requirements.txt

ENTRYPOINT [ "/app/e2e_test_entrypoint.sh" ]
CMD pytest --html=/app/reports/e2e_report.html --self-contained-html