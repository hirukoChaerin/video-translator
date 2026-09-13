# syntax=docker/dockerfile:1
ARG PY_VERSION=3.14
FROM python:${PY_VERSION}-slim

# ffmpeg es la única dependencia de sistema del worker
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/worker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# PYTHONUNBUFFERED: logs en tiempo real en `docker logs`
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "app.main"]
