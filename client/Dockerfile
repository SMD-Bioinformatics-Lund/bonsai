FROM python:3.10.2

# Set build variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app
COPY requirements.txt ./
COPY app app/
RUN pip install --no-cache-dir --upgrade pip &&                 \
	pip install --no-cache-dir --requirement requirements.txt
